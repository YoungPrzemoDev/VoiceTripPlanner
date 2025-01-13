import firebase_admin
from firebase_admin import credentials, firestore, auth
from fastapi import HTTPException

# Konfiguracja Firebase
try:
    cred = credentials.Certificate("app/credentials/voicetripplanner-66dba-firebase-adminsdk-ads5q-2a03487b09.json")
except: 
    print("asd")
firebase_admin.initialize_app(cred)
db = firestore.client()

async def verify_token(token: str):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")