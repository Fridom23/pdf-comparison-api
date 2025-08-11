import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
import tempfile
from typing import Dict, List, Optional
import uvicorn

app = FastAPI(title="PDF Comparison API", version="1.0.0")

# Configuration - adaptée pour le déploiement
MODELE_VIERGE_PATH = os.getenv("MODELE_VIERGE_PATH", "modele_vierge.pdf")
PAGES_A_COMPARER = [0, 2, 10, 11]  # pages 1, 3, 11, 12 (indexées à 0)

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
                filled_text = doc_filled.load_page(page_index).get_text()
                empty_text = doc_empty.load_page(page_index).get_text()
            except IndexError:
                filled_text = ""
                empty_text = ""
            
            filled_lines = nettoyer_lignes(filled_text)
            empty_lines = nettoyer_lignes(empty_text)
            diff_lines = filled_lines - empty_lines
            diff_text = "\n".join(diff_lines).strip()
            
            # Format de clé demandé : "page11", "page12", etc.
            page_key = f"page{page_index + 1}"
            diffs_par_page[page_key] = diff_text
        
        doc_filled.close()
        doc_empty.close()
        return diffs_par_page
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'extraction : {str(e)}")

@app.post("/compare-pdf-base64")
async def compare_pdf_base64(
    file_content: str,
    filename: str = "document.pdf"
):
    """
    Compare un fichier PDF en Base64 avec le modèle vierge.
    Parfait pour Power Automate !
    
    - **file_content**: Contenu du PDF en Base64
    - **filename**: Nom du fichier (optionnel)
    
    Body JSON exemple:
    {
        "file_content": "JVBERi0xLjQKMSAwIG9...",
        "filename": "contrat.pdf"
    }
    """
    import base64
    
    # Vérifier que le modèle vierge existe
    if not os.path.exists(MODELE_VIERGE_PATH):
        raise HTTPException(status_code=500, detail="Le fichier modèle vierge n'a pas été trouvé")
    
    try:
        # Décoder le Base64
        pdf_bytes = base64.b64decode(file_content)
    except Exception:
        raise HTTPException(status_code=400, detail="Contenu Base64 invalide")
    
    # Créer un fichier temporaire pour le PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        try:
            # Écrire les bytes décodés
            temp_file.write(pdf_bytes)
            temp_file.flush()
            
            # Extraire les différences
            differences = extract_page_diffs(temp_file.name, MODELE_VIERGE_PATH, PAGES_A_COMPARER)
            
            return JSONResponse(content=differences)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors du traitement : {str(e)}")
        
        finally:
            # Nettoyer le fichier temporaire
            try:
                os.unlink(temp_file.name)
            except:
                pass

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

@app.post("/compare-pdf-custom")
async def compare_pdf_custom(
    file: UploadFile = File(...),
    pages: str = "0,2,10,11"  # Pages sous forme de chaîne séparée par des virgules
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

@app.post("/compare-pdf")
async def compare_pdf(
    file: UploadFile = File(...)
):
    """
    Compare un fichier PDF uploadé avec le modèle vierge.
    
    - **file**: Fichier PDF à comparer
    
    Retourne un JSON avec les différences par page au format {"page11": "texte", "page12": "texte"}
    Les pages comparées sont définies dans la configuration (pages 1, 3, 11, 12 par défaut).
    """
    
    # Vérifier le type de fichier
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")
    
    # Vérifier que le modèle vierge existe
    if not os.path.exists(MODELE_VIERGE_PATH):
        raise HTTPException(status_code=500, detail="Le fichier modèle vierge n'a pas été trouvé")
    
    # Utiliser les pages par défaut
    pages_to_compare = PAGES_A_COMPARER
    
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

@app.get("/")
async def root():
    """Point d'entrée de l'API."""
    return {"message": "API de comparaison de PDF", "version": "1.0.0"}

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
