import io
import os
import json
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = FastAPI()

# ID du dossier Google Drive racine
FOLDER_ID = "1S7ULRbWlb3g-m2-FwuA-I_A6nfZ5onNq"

# ---------------------------------------------------------------------------
# Helper : connexion Drive
# ---------------------------------------------------------------------------
def drive():
    creds_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.get("/drive/list")
def list_files():
    svc = drive()
    res = svc.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed = false",
        fields="files(id,name,mimeType,size)",
    ).execute()
    return res.get("files", [])


@app.post("/drive/create-folder")
async def create_folder(request: Request, name: Optional[str] = None):
    """
    Crée un sous‑dossier.
    Accepte name                      en query (?name=Kaka)
            name=<valeur>             en x‑www‑form‑urlencoded
            { "name": "<valeur>" }    en JSON
    """
    if not name:                       # query ou form vide → lire éventuel JSON
        try:
            body = await request.json()
            name = body.get("name")
        except Exception:
            pass
    if not name:
        raise HTTPException(status_code=400, detail="name manquant")

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [FOLDER_ID],
    }
    return drive().files().create(body=meta, fields="id,name").execute()


@app.post("/drive/upload")
async def upload_file(name: str, file: UploadFile = File(...)):
    data = await file.read()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=file.content_type)
    meta = {"name": name, "parents": [FOLDER_ID]}
    return drive().files().create(body=meta, media_body=media, fields="id,name").execute()


@app.patch("/drive/update/{file_id}")
async def update_file(
    file_id: str,
    request: Request,
    new_name: Optional[str] = None,
    new_parent_id: Optional[str] = None,
):
    # récupérer JSON si paramètres absents
    if not (new_name or new_parent_id):
        try:
            body = await request.json()
            new_name = body.get("new_name")
            new_parent_id = body.get("new_parent_id")
        except Exception:
            pass

    if not (new_name or new_parent_id):
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    svc = drive()
    body = {"name": new_name} if new_name else {}

    if new_parent_id:
        prev_parents = ",".join(
            svc.files().get(fileId=file_id, fields="parents").execute()["parents"]
        )
        return svc.files().update(
            fileId=file_id,
            body=body,
            addParents=new_parent_id,
            removeParents=prev_parents,
            fields="id,name,parents",
        ).execute()

    return svc.files().update(
        fileId=file_id, body=body, fields="id,name,parents"
    ).execute()


@app.delete("/drive/file/{file_id}")
def delete_file(file_id: str):
    drive().files().delete(fileId=file_id).execute()
    return {"status": "deleted", "id": file_id}
