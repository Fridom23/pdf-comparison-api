import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
import tempfile
from typing import Dict, List, Optional
import uvicorn

app = FastAPI(title="PDF Comparison API", version="1.0.1")

# Configuration - adaptée pour le déploiement
MODELE_VIERGE_PATH = os.getenv("MODELE_VIERGE_PATH", "modele_vierge.pdf")
PAGES_A_COMPARER = [1, 3, 11, 12]  # pages 1, 3, 11, 12 (indexées à 0)

def nettoyer_lignes(texte: str) -> set:
    """Nettoie et filtre les lignes de texte."""
    return set(
        line.strip()
        for line in texte.strip().splitlines()
        if line.strip() and "docusign envelope id" not in line.lower()
    )

def extract_page_diffs(filled_pdf_path: str, empty_pdf_path: str, pages: List[int]) -> Dict[str, str]:
    """Extrait les différences entre deux PDF pour les pages spécifiées."""
    try:
        doc_filled = fitz.open(filled_pdf_path)
        doc_empty = fitz.open(empty_pdf_path)
        diffs_par_page = {}
        
        for page_index in pages:
            try:
                filled_text = doc_filled.load_page(page_index - 1).get_text()
                empty_text = doc_empty.load_page(page_index - 1).get_text()
            except IndexError:
                filled_text = ""
                empty_text = ""
            
            filled_lines = nettoyer_lignes(filled_text)
            empty_lines = nettoyer_lignes(empty_text)
            diff_lines = filled_lines - empty_lines
            diff_text = "\n".join(diff_lines).strip()
            
            # Format de clé demandé : "page11", "page12", etc.
            page_key = f"page{page_index}"
            diffs_par_page[page_key] = diff_text
        
        doc_filled.close()
        doc_empty.close()
        return diffs_par_page
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'extraction : {str(e)}")

@app.post("/upload-model")
async def upload_model(file: UploadFile = File(...)):
    """
    Upload le fichier modèle vierge (à faire une seule fois).
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")
    
    try:
        content = await file.read()
        with open("modele_vierge.pdf", "wb") as f:
            f.write(content)
        return {"message": "Modèle vierge uploadé avec succès"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'upload : {str(e)}")

@app.post("/upload-model-base64")
async def upload_model_base64(request: dict):
    """
    Version sécurisée - Upload le fichier modèle vierge en Base64.
    
    Body JSON:
    {
        "file_content": "base64_string",
        "filename": "modele_vierge.pdf"
    }
    """
    import base64
    
    try:
        # Extraire les données du request
        file_content = request.get("file_content", "")
        filename = request.get("filename", "modele_vierge.pdf")
        
        if not file_content:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "file_content manquant"}
            )
        
        # Vérifier la taille
        if len(file_content) > 20000000:  # Limite plus élevée pour le modèle
            return JSONResponse(
                status_code=413,
                content={"success": False, "error": "Fichier modèle trop volumineux (max ~15MB)"}
            )
        
        # Décoder le Base64
        try:
            pdf_bytes = base64.b64decode(file_content)
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Base64 invalide: {str(e)}"}
            )
        
        # Vérifier que c'est un PDF valide
        if not pdf_bytes.startswith(b'%PDF'):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Le fichier ne semble pas être un PDF valide"}
            )
        
        # Sauvegarder le modèle vierge
        try:
            with open("modele_vierge.pdf", "wb") as f:
                f.write(pdf_bytes)
            
            return JSONResponse(content={
                "success": True,
                "message": f"Modèle vierge '{filename}' uploadé avec succès",
                "file_size_kb": len(pdf_bytes) // 1024
            })
            
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": f"Erreur lors de la sauvegarde: {str(e)}"}
            )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erreur serveur: {str(e)}"}
        )

@app.post("/compare-pdf")
async def compare_pdf(
    file: UploadFile = File(...),
    pages: str = "1,3,11,12"  # Pages sous forme de chaîne séparée par des virgules
):
    """
    Compare un fichier PDF uploadé avec le modèle vierge avec des pages personnalisées.
    
    - **file**: Fichier PDF à comparer
    - **pages**: Pages à comparer sous forme de chaîne séparée par des virgules (ex: "0,2,10,11")
    
    Retourne un JSON avec les différences par page au format {"page11": "texte", "page12": "texte"}
    """
    
    # Vérifier le type de fichier
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")
    
    # Vérifier que le modèle vierge existe
    if not os.path.exists(MODELE_VIERGE_PATH):
        raise HTTPException(status_code=500, detail="Le fichier modèle vierge n'a pas été trouvé")
    
    # Convertir la chaîne de pages en liste d'entiers
    try:
        pages_to_compare = [int(p.strip()) for p in pages.split(',')]
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de pages invalide. Utilisez des nombres séparés par des virgules (ex: '0,2,10,11')")
    
    # Créer un fichier temporaire pour le PDF uploadé
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        try:
            # Sauvegarder le fichier uploadé
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()
            
            # Extraire les différences
            differences = extract_page_diffs(temp_file.name, MODELE_VIERGE_PATH, pages_to_compare)
            
            return JSONResponse(content=differences)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {str(e)}")
        
        finally:
            # Nettoyer le fichier temporaire
            try:
                os.unlink(temp_file.name)
            except:
                pass

@app.post("/compare-pdf-base64")
async def compare_pdf_base64(request: dict):
    """
    Version sécurisée - Compare un fichier PDF en Base64 avec pages personnalisées.
    
    Body JSON:
    {
        "file_content": "base64_string",
        "pages": "0,2,10,11",
        "filename": "document.pdf"
    }
    """
    import base64
    
    try:
        # Extraire les données du request
        file_content = request.get("file_content", "")
        pages = request.get("pages", "1, 3, 11, 12")  # Pages par défaut
        filename = request.get("filename", "document.pdf")
        
        if not file_content:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "file_content manquant"}
            )
        
        # Vérifier que le modèle vierge existe
        if not os.path.exists(MODELE_VIERGE_PATH):
            return JSONResponse(
                status_code=500,
                content={"success": False, "error": "Modèle vierge non trouvé"}
            )
        
        # Convertir et valider les pages
        try:
            pages_to_compare = [int(p.strip()) for p in pages.split(',')]
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Format de pages invalide. Utilisez des nombres séparés par des virgules (ex: '0,2,10,11')"}
            )
        
        # Vérifier la taille
        if len(file_content) > 15000000:
            return JSONResponse(
                status_code=413,
                content={"success": False, "error": "Fichier trop volumineux (max ~10MB)"}
            )
        
        # Décoder le Base64
        try:
            pdf_bytes = base64.b64decode(file_content)
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": f"Base64 invalide: {str(e)}"}
            )
        
        # Vérifier que c'est un PDF
        if not pdf_bytes.startswith(b'%PDF'):
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Pas un fichier PDF valide"}
            )
        
        # Traitement du PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            try:
                temp_file.write(pdf_bytes)
                temp_file.flush()
                
                differences = extract_page_diffs(temp_file.name, MODELE_VIERGE_PATH, pages_to_compare)
                
                return JSONResponse(content={
                    "success": True,
                    "filename": filename,
                    "pages_compared": pages_to_compare,
                    "file_size_kb": len(pdf_bytes) // 1024,
                    "differences": differences
                })
                
            finally:
                try:
                    os.unlink(temp_file.name)
                except:
                    pass
                    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Erreur serveur: {str(e)}"}
        )

@app.get("/")
async def root():
    """Point d'entrée de l'API."""
    return {"message": "API de comparaison de PDF", "version": "1.0.1"}

@app.get("/health")
async def health_check():
    """Vérification de l'état de l'API."""
    return {"status": "healthy", "model_file_exists": os.path.exists(MODELE_VIERGE_PATH)}

@app.get("/config")
async def get_config():
    """Retourne la configuration actuelle."""
    return {
        "modele_vierge_path": MODELE_VIERGE_PATH,
        "pages_par_defaut": PAGES_A_COMPARER,
        "model_file_exists": os.path.exists(MODELE_VIERGE_PATH)
    }

if __name__ == "__main__":
    # Lancer le serveur de développement
    port = int(os.getenv("PORT", 8000))
    print(f"🚀 Serveur démarré sur http://localhost:{port}")
    print(f"📖 Documentation interactive : http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)

