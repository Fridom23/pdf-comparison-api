# PDF Comparison API

API FastAPI pour comparer des fichiers PDF avec un modèle vierge et extraire les différences par page.

## 🚀 Fonctionnalités

- **Comparaison de PDF** : Compare un PDF rempli avec un modèle vierge
- **Pages personnalisables** : Spécifiez les pages à comparer (numéros réels : 1, 2, 3...)
- **Support multi-format** : Upload de fichiers ou Base64 (Power Automate)
- **Gestion robuste des erreurs** : Réponses JSON structurées
- **Nettoyage automatique** : Suppression des signatures DocuSign

## 📋 Endpoints disponibles

### 🔄 Comparaison de PDF

#### `POST /compare-pdf`
Compare un fichier PDF uploadé avec le modèle vierge.

**Paramètres :**
- `file` : Fichier PDF (multipart/form-data)
- `pages` : Pages à comparer, ex: "1,3,11,12" (optionnel, défaut: "1,3,11,12")

**Exemple d'utilisation avec curl :**
```bash
curl -X POST "https://votre-api.onrender.com/compare-pdf" \
     -F "file=@contrat_signe.pdf" \
     -F "pages=1,2,3"
```

#### `POST /compare-pdf-base64`
Version Base64 optimisée pour Power Automate.

**Body JSON :**
```json
{
    "file_content": "JVBERi0xLjQKMSAwIG9...",
    "pages": "1,3,11,12",
    "filename": "contrat.pdf"
}
```

**Réponse :**
```json
{
    "success": true,
    "filename": "contrat.pdf",
    "pages_compared": [1, 3, 11, 12],
    "file_size_kb": 1250,
    "differences": {
        "page1": "Texte différence page 1...",
        "page3": "Texte différence page 3...",
        "page11": "Texte différence page 11...",
        "page12": "Texte différence page 12..."
    }
}
```

### 📤 Upload du modèle vierge

#### `POST /upload-model`
Upload le fichier modèle vierge (multipart/form-data).

#### `POST /upload-model-base64`
Upload le modèle en Base64.

**Body JSON :**
```json
{
    "file_content": "JVBERi0xLjQKMSAwIG9...",
    "filename": "modele_vierge.pdf"
}
```

### ℹ️ Informations

#### `GET /`
Informations de base sur l'API.

#### `GET /health`
État de santé de l'API et vérification du modèle vierge.

#### `GET /config`
Configuration actuelle (pages par défaut, chemins des fichiers).

#### `GET /docs`
Documentation interactive Swagger UI.

## 🛠️ Installation locale

### Prérequis
- Python 3.8+
- pip

### Installation
```bash
# Cloner le repository
git clone https://github.com/votre-username/pdf-comparison-api.git
cd pdf-comparison-api

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'API
python main.py
```

L'API sera accessible sur `http://localhost:8000`

## ☁️ Déploiement

### Render (Recommandé)
1. Créez un compte sur [render.com](https://render.com)
2. Connectez votre repository GitHub
3. Créez un nouveau "Web Service"
4. Render détectera automatiquement la configuration

### Configuration automatique
Le fichier `render.yaml` est fourni pour un déploiement automatique.

## 🔧 Configuration Power Automate

### Workflow recommandé :
1. **Trigger** : "When a file is created" (SharePoint)
2. **Get file content** : Récupérer le contenu du fichier
3. **HTTP Action** :
   - Method : `POST`
   - URI : `https://votre-api.onrender.com/compare-pdf-base64`
   - Headers : `Content-Type: application/json`
   - Body :
   ```json
   {
       "file_content": "@{base64(outputs('Get_file_content')?['body'])}",
       "pages": "1,3,11,12",
       "filename": "@{triggerOutputs()?['body/Name']}"
   }
   ```
4. **Parse JSON** : Analyser la réponse
5. **Condition** : Traiter les résultats selon `success`

### Schéma Parse JSON :
```json
{
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "filename": {"type": "string"},
        "pages_compared": {"type": "array"},
        "file_size_kb": {"type": "integer"},
        "differences": {"type": "object"},
        "error": {"type": "string"}
    }
}
```

## ⚡ Utilisation

### 1. Upload du modèle vierge (une seule fois)
Utilisez `/upload-model` ou `/upload-model-base64` pour définir votre fichier de référence.

### 2. Comparaison des PDF
- **Via Postman/curl** : Utilisez `/compare-pdf`
- **Via Power Automate** : Utilisez `/compare-pdf-base64`

### 3. Analyse des résultats
L'API retourne les différences textuelles par page avec nettoyage automatique des signatures DocuSign.

## 📝 Notes importantes

- **Numéros de pages** : Utilisez les numéros réels (1, 2, 3...) et non les indices
- **Limite de taille** : ~10MB pour les endpoints Base64, plus pour l'upload direct
- **Format de sortie** : `{"page1": "texte", "page3": "texte"}` 
- **Nettoyage automatique** : Les signatures DocuSign sont filtrées

## 🐛 Résolution de problèmes

### Erreur "Modèle vierge non trouvé"
Uploadez d'abord votre fichier modèle via `/upload-model` ou `/upload-model-base64`.

### Erreur "Base64 invalide"
Vérifiez que vous utilisez `base64()` dans Power Automate et pas `base64ToString()`.

### Fichier trop volumineux
Pour les gros fichiers (>10MB), utilisez l'upload direct `/compare-pdf` plutôt que Base64.

## 📄 Licence

MIT License - voir le fichier LICENSE pour plus de détails.

## 🤝 Support

Pour toute question ou problème, ouvrez une issue sur GitHub ou contactez l'équipe de développement.
