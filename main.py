import io
import os
import json
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = FastAPI()

FOLDER_ID = "1S7ULRbWlb3g-m2-FwuA-I_A6nfZ5onNq"  # dossier Drive racine


# ------------------------------------------------------------------
# Helper Google Drive
# ------------------------------------------------------------------
def drive():
    creds_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        creds_info, scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------
@app.get("/drive/list", response_model=list)
def list_files():
    res = drive().files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id,name,mimeType,size)"
    ).execute()
    return res.get("files", [])


@app.post("/drive/create-folder", status_code=201)
def create_folder(payload: dict = Body(...)):
    """
    Crée un dossier. Payload attendu : { "name": "<nom>" }
    """
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name manquant")

    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [FOLDER_ID],
    }
    folder = drive().files().create(body=meta, fields="id,name").execute()
    return {"id": folder["id"], "name": folder["name"]}


@app.post("/drive/upload", status_code=201)
async def upload_file(name: str = Body(...), file: UploadFile = File(...)):
    """
    Téléverse un fichier dans le dossier racine.
    """
    data = await file.read()
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=file.content_type)
    meta = {"name": name, "parents": [FOLDER_ID]}
    created = drive().files().create(
        body=meta, media_body=media, fields="id,name"
    ).execute()
    return {"id": created["id"], "name": created["name"]}


@app.patch("/drive/update/{file_id}")
def update_file(
    file_id: str,
    new_name: Optional[str] = Body(default=None),
    new_parent_id: Optional[str] = Body(default=None),
):
    if not (new_name or new_parent_id):
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")

    svc = drive()
    body = {"name": new_name} if new_name else {}

    if new_parent_id:
        prev = ",".join(
            svc.files().get(fileId=file_id, fields="parents").execute()["parents"]
        )
        file = svc.files().update(
            fileId=file_id,
            body=body,
            addParents=new_parent_id,
            removeParents=prev,
            fields="id,name,parents",
        ).execute()
    else:
        file = svc.files().update(
            fileId=file_id, body=body, fields="id,name,parents"
        ).execute()
    return file


@app.delete("/drive/file/{file_id}")
def delete_file(file_id: str):
    drive().files().delete(fileId=file_id).execute()
    return {"status": "deleted", "id": file_id}
