import io
import os
import json
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = FastAPI()

# Dossier racine partagé
FOLDER_ID = "1S7ULRbWlb3g-m2-FwuA-I_A6nfZ5onNq"


# ---------------------------------------------------------------------------
# Helper : connexion Google Drive
# ---------------------------------------------------------------------------
def drive():
    creds_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/drive/list")
def list_files():
    """Lister les fichiers du dossier partagé."""
    svc = drive()
    res = svc.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id,name,mimeType,size)",
    ).execute()
    return res.get("files", [])


@app.post("/drive/upload")
async def upload_file(name: str, file: UploadFile = File(...)):
    """Téléverser un fichier dans le dossier racine."""
    data = await file.read()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=file.content_type)
    meta = {"name": name, "parents": [FOLDER_ID]}
    svc = drive()
    created = svc.files().create(
        body=meta, media_body=media, fields="id,name,parents"
    ).execute()
    return created


@app.post("/drive/create-folder")
def create_folder(name: str):
    """Créer un sous‑dossier dans le dossier racine."""
    svc = drive()
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [FOLDER_ID],
    }
    folder = svc.files().create(body=meta, fields="id,name").execute()
    return folder


@app.patch("/drive/update/{file_id}")
async def update_file(
    file_id: str,
    new_name: Optional[str] = None,
    new_parent_id: Optional[str] = None,
):
    """Renommer et/ou déplacer un fichier."""
    svc = drive()
    body = {}
    if new_name:
        body["name"] = new_name

    if new_parent_id:
        current = svc.files().get(fileId=file_id, fields="parents").execute()
        prev = ",".join(current.get("parents", [])) or None
        updated = svc.files().update(
            fileId=file_id,
            body=body,
            addParents=new_parent_id,
            removeParents=prev,
            fields="id,name,parents",
        ).execute()
    else:
        updated = svc.files().update(
            fileId=file_id, body=body, fields="id,name,parents"
        ).execute()
    return updated


@app.delete("/drive/file/{file_id}")
def delete_file(file_id: str):
    """Supprimer un fichier par son ID."""
    drive().files().delete(fileId=file_id).execute()
    return {"status": "deleted", "id": file_id}
