import io
import os
import json

from fastapi import FastAPI, UploadFile, File, HTTPException
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = FastAPI()

# ID du dossier Google Drive où l’agent doit travailler
FOLDER_ID = "1S7ULRbWlb3g-m2-FwuA-I_A6nfZ5onNq"


# ---------------------------------------------------------------------------
# Helper : connexion au Google Drive API via la clé JSON stockée en variable
# ---------------------------------------------------------------------------
def drive():
    """
    Retourne un client Drive authentifié à partir du JSON contenu
    dans la variable d’environnement GOOGLE_SERVICE_ACCOUNT_JSON.
    """
    try:
        creds_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    except KeyError:
        raise RuntimeError(
            "Variable d'environnement GOOGLE_SERVICE_ACCOUNT_JSON absente."
        )
    except json.JSONDecodeError:
        raise RuntimeError("Contenu JSON invalide dans GOOGLE_SERVICE_ACCOUNT_JSON.")

    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# Routes minimalistes
# ---------------------------------------------------------------------------

@app.get("/drive/list")
def list_files():
    """
    Liste les fichiers du dossier Drive partagé.
    """
    svc = drive()
    result = svc.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed = false",
        fields="files(id,name,mimeType,size)"
    ).execute()
    return result.get("files", [])


@app.post("/drive/upload")
async def upload_file(name: str, file: UploadFile = File(...)):
    """
    Charge un fichier (multipart/form-data) dans le dossier Drive.
    """
    data = await file.read()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=file.content_type)
    meta = {"name": name, "parents": [FOLDER_ID]}

    svc = drive()
    created = svc.files().create(
        body=meta, media_body=media, fields="id,name"
    ).execute()
    return created


@app.delete("/drive/file/{file_id}")
def delete_file(file_id: str):
    """
    Supprime un fichier du Drive par son ID.
    """
    svc = drive()
    try:
        svc.files().delete(fileId=file_id).execute()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "deleted", "id": file_id}
