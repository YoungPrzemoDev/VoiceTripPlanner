import os
import json
import pytz
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from app.routes.Chater import extract_info
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from openai import OpenAI
from app.database import db
from app.models import Trip, VoiceCommand
import logging
import google.api_core.exceptions



# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI router
router = APIRouter()

# Utility functions
def convert_to_firestore_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
    except ValueError:
        logger.error("Invalid date format: %s", date_str)
        raise ValueError("Invalid date format. Expected 'YYYY-MM-DD'.")

def validate_extracted_info(info):
    # Clean and validate price
    if "price" in info and info["price"]:
        try:
            info["price"] = float(''.join(filter(str.isdigit, info["price"])))
        except ValueError:
            raise ValueError("Price must be a numeric value.")

    # Validate available_time
    if "available_time" in info:
        available_time = info["available_time"]
        from_date = available_time.get("from", "").strip().lower()
        to_date = available_time.get("to", "").strip().lower()

        # Handle 'not specified' or similar invalid values
        if from_date in ["", "not specified", "unknown"]:
            available_time["from"] = None
        else:
            try:
                convert_to_firestore_date(from_date)
            except ValueError:
                raise ValueError(f"Invalid 'from' date format: {from_date}. Expected 'YYYY-MM-DD'.")

        if to_date in ["", "not specified", "unknown"]:
            available_time["to"] = None
        else:
            try:
                convert_to_firestore_date(to_date)
            except ValueError:
                raise ValueError(f"Invalid 'to' date format: {to_date}. Expected 'YYYY-MM-DD'.")


import google.api_core.exceptions

def filter_trips(db, extracted_info: dict):
    trips_ref = db.collection('trips')
    query = trips_ref

    try:
        # Apply destination filter
        if "destination" in extracted_info and extracted_info["destination"]:
            query = query.where("destination", "==", extracted_info["destination"])

        # Apply price filter
        if "price" in extracted_info and extracted_info["price"]:
            query = query.where("price", "<=", float(extracted_info["price"]))

        # Apply date filters
        if "available_time" in extracted_info:
            available_time = extracted_info["available_time"]
            from_date = available_time.get("from")
            to_date = available_time.get("to")

            if from_date:
                query = query.where("departure_date", ">=", convert_to_firestore_date(from_date))
            if to_date:
                query = query.where("return_date", "<=", convert_to_firestore_date(to_date))

        # Execute the query
        results = query.stream()
        trips = [doc.to_dict() for doc in results]
        logger.debug("Filtered trips: %s", trips)
        return trips

    except google.api_core.exceptions.FailedPrecondition as e:
        # Handle Firestore index-related errors
        if "requires an index" in str(e):
            logger.error("The query requires a Firestore index. Please create it in the Firebase Console.")
            return {
                "error": "The query requires a Firestore index. Please check the Firebase Console for details.",
                "index_creation_link": str(e).split("https://")[1]  # Extract the link to create the index
            }
        raise  # Re-raise other exceptions
    except Exception as e:
        logger.error("Unexpected error during Firestore query: %s", str(e))
        raise




# API endpoints
@router.post("/search-trips")
async def search_trips(text: str):
    try:
        response = extract_info(text)
        extracted_info = json.loads(response)
        validate_extracted_info(extracted_info)

        filtered_trips = filter_trips(db, extracted_info)

        if not filtered_trips:
            return {"message": "No trips found matching your criteria."}

        return {"trips": filtered_trips}
    except json.JSONDecodeError:
        logger.error("Failed to parse OpenAI response.")
        return {"error": "Failed to parse OpenAI response."}
    except ValueError as e:
        logger.error("Validation error: %s", str(e))
        return {"error": str(e)}
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return {"error": "An unexpected error occurred."}


#============================================================================


@router.post("/test-openai")
async def test_openai(text: str):
    try:
        response = extract_info(text)
        extracted_info = json.loads(response)
        validate_extracted_info(extracted_info)
        return {"response": extracted_info}
    except json.JSONDecodeError:
        return {"error": "Failed to parse OpenAI response."}
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

@router.get("/")
async def get_all_trips(limit: int = 10, last_doc_id: str = None):
    trips_ref = db.collection("trips").limit(limit)
    if last_doc_id:
        last_doc = db.collection("trips").document(last_doc_id).get()
        trips_ref = trips_ref.start_after(last_doc)

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
    
def get_trips(destination: str):
    trips_ref = db.collection("trips")
    docs = trips_ref.where("destination", "==", destination).stream()
    trips = [doc.to_dict() for doc in docs]
    return {"trips": trips}

@router.get("/filter-trips")
async def filter_trips(
    kierunek_kraj: str = Query(None, description="Destination country"),
    kierunek_miasto: str = Query(None, description="Destination city (optional)"),
    odlot_data_from: str = Query(None, description="Departure date from (YYYY-MM-DD)"),
    odlot_data_to: str = Query(None, description="Departure date to (YYYY-MM-DD)"),
    cena_max: int = Query(None, description="Maximum price"),
):
    """
    Endpoint to filter trips from Firestore database. 
    The city (kierunek_miasto) is optional.
    """
    trips_ref = db.collection("Wycieczki")
    query = trips_ref

    try:
        # Apply filters dynamically
        if kierunek_kraj:
            query = query.where("Kierunek_Kraj", "==", kierunek_kraj)
        if kierunek_miasto:
            logger.debug("Applying city filter: %s", kierunek_miasto)
            query = query.where("Kierunek_Miasto", "==", kierunek_miasto)

        if odlot_data_from:
            from_date = convert_to_firestore_date(odlot_data_from)
            query = query.where("Odlot_Data", ">=", from_date)
        if odlot_data_to:
            to_date = convert_to_firestore_date(odlot_data_to)
            query = query.where("Odlot_Data", "<=", to_date)
        if cena_max:
            query = query.where("Cena", "<=", cena_max)

        # Debug log for query filters
        logger.debug("Filters applied: country=%s, city=%s, from_date=%s, to_date=%s, max_price=%s",
                     kierunek_kraj, kierunek_miasto, odlot_data_from, odlot_data_to, cena_max)

        # Execute query and fetch results
        results = query.stream()
        trips = [doc.to_dict() for doc in results]

        if not trips:
            return {"message": "No trips match your criteria."}

        return {"trips": trips}

    except Exception as e:
        logger.error("Error in filter-trips endpoint: %s", str(e))
        raise HTTPException(status_code=500, detail="An error occurred while filtering trips.")
