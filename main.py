# main.py  —  colle ça

import io, os
from fastapi import FastAPI, UploadFile, File
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = FastAPI()
FOLDER_ID = "1S7ULRbWlb3g-m2-FwuA-I_A6nfZ5onNq"   # <- ton dossier Drive

def drive():
    creds = service_account.Credentials.from_service_account_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds)

@app.get("/drive/list")
def list_files():
    svc = drive()
    return svc.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed=false",
        fields="files(id,name)").execute()["files"]
