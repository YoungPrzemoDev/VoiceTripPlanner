from fastapi import APIRouter, HTTPException
from app.database import db
from app.models import Trip, VoiceCommand

router = APIRouter()


def get_trips(destination : str):
    trips_ref = db.collection("trips")
    docs = trips_ref.where("destination", "==", destination).stream()
    trips = [doc.to_dict() for doc in docs]
    return {"trips": trips}

    
@router.get("/")
async def get_all_trips():
    trips_ref = db.collection("trips")
    docs = trips_ref.stream()
    trips = [doc.to_dict() for doc in docs]
    return trips
    
@router.post("/voiceplace")
async def get_trip_place_by_voice(command: VoiceCommand):
    user_command = command.command.lower()
    
    found_destination = None
    for dest_key in VoiceCommand.known_destinations:
        if dest_key in user_command:
            found_destination = VoiceCommand.known_destinations[dest_key]
            break
        
    if found_destination:
        return get_trips(destination=found_destination)
    else:
        return {"message": "Nie rozpoznano miejsca docelowego. Proszę spróbować jeszcze raz."}