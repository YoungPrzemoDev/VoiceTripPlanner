import firebase_admin
from firebase_admin import credentials, firestore, auth
from fastapi import HTTPException

# Konfiguracja Firebase
cred = credentials.Certificate("C:\\Users\\Przemo\\Documents\\9_sem\\SWP\\Projekt\\VoiceTripPlanner\\voicetripplanner-firebase-adminsdk-f60i8-35e8068ee3.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

async def verify_token(token: str):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")