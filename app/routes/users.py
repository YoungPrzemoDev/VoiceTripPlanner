from fastapi import APIRouter, HTTPException
from app.database import db
from app.models import UserRegister
from firebase_admin import auth

router = APIRouter()

@router.post("/register")
async def register_user(user : UserRegister):
    try:
        user_record = auth.create_user(
            email = user.email,
            password = user.password
        )
        return {"message": "User created successfully", "uid": user_record.uid}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

