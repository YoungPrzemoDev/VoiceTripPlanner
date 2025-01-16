import os
import json
import pytz
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from app.routes.Chater import first_encounter,ask_user,second_encounter
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


def convert_to_firestore_date(date_str: str) -> datetime:
    try:
        # Parse the date string in the format DD/MM/YY
        return datetime.strptime(date_str, "%d/%m/%y")
    except ValueError:
        logger.error("Invalid date format: %s. Expected DD/MM/YY.", date_str)
        raise ValueError(f"Invalid date format: {date_str}. Expected DD/MM/YY.")


def validate_extracted_info(info):
    # Clean and validate price
    if "price" in info:
        price_str = info["price"]
        if price_str and price_str.strip().isdigit():  # Check if price is a valid number
            info["price"] = float(price_str.strip())
        else:
            info["price"] = None  # Set to None if invalid or missing

    # Validate available_time
    if "available_time" in info:
        available_time = info["available_time"]
        from_date = available_time.get("from", "").strip().lower()
        to_date = available_time.get("to", "").strip().lower()

        # Handle 'not specified' or similar invalid values
        if from_date in ["", "not specified", "unknown"]:
            available_time["from"] = None
        else:
            convert_to_firestore_date(from_date)


        if to_date in ["", "not specified", "unknown"]:
            available_time["to"] = None
        else:
            convert_to_firestore_date(to_date)



import google.api_core.exceptions

def filter_trips(db, extracted_info: dict):
    trips_ref = db.collection('Wycieczki')
    query = trips_ref

    try:

        if "destination_country" in extracted_info and extracted_info["destination_country"]:
            query = query.where("destination_country", "==", extracted_info["destination_country"])
            
        if "destination_city" in extracted_info and extracted_info["destination_city"]:
            query = query.where("destination_city", "==", extracted_info["destination_city"])

        if "price" in extracted_info and extracted_info["price"]:
            query = query.where("price", "<=", float(extracted_info["price"]))

        if "available_time" in extracted_info:
            available_time = extracted_info["available_time"]
            from_date = available_time.get("from")
            to_date = available_time.get("to")

            if from_date:
                query = query.where("departure_date", ">=", convert_to_firestore_date(from_date))
            if to_date:
                query = query.where("return_date", "<=", convert_to_firestore_date(to_date))

        if "tags" in extracted_info and extracted_info["tags"]:
            tags = extracted_info["tags"]
            for tag in tags:
                query = query.where("tags", "array_contains", tag)

        
        
        results = query.stream()
        Wycieczki = [doc.to_dict() for doc in results]
        logger.debug("Filtered Wycieczki: %s", Wycieczki)
        return Wycieczki

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
        # Step 1: Extract information from user input
        extracted_info = first_encounter(text)
        logger.debug("Extracted Info: %s", extracted_info)

        # Step 2: Validate and clean the extracted information
        validate_extracted_info(extracted_info)

        # Step 3: Filter trips in Firestore based on the extracted information
        filtered_trips = filter_trips(db, extracted_info)

        # Step 4: Return filtered trips or a message if none are found
        if not filtered_trips:
            return {"message": "No trips found matching your criteria."}

        return {"Wycieczki": filtered_trips}
    except ValueError as e:
        logger.error("Validation error: %s", str(e))
        return {"error": str(e)}
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return {"error": "An unexpected error occurred."}


@router.get("/ask_question")
async def search_trips(text: str):
    try:
        # Extract information from the user's text
        extracted_info = ask_user(text)


        return extracted_info
    except ValueError as e:
        logger.error("Validation error: %s", str(e))
        return {"error": str(e)}
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return {"error": "An unexpected error occurred."}
    

@router.post("/changer")
async def search_trips(text: str):
    try:
        # Extract information from the user's text
        extracted_info = second_encounter(text)

        return extracted_info
    except ValueError as e:
        logger.error("Validation error: %s", str(e))
        return {"error": str(e)}
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return {"error": "An unexpected error occurred."}
