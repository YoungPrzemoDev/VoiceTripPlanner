import os
import json
import pytz
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from app.routes.Chater import first_encounter,ask_user,second_encounter
from google.cloud.firestore_v1 import SERVER_TIMESTAMP
from openai import OpenAI
from app.database import db
import logging
import google.api_core.exceptions
from typing import Dict


# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI router
router = APIRouter()

# Global storage for the single user's preferences
user_preferences = {}


def convert_to_firestore_date(date_str: str) -> datetime:
    try:
        # Parse the date string in the format DD/MM/YY
        naive_datetime = datetime.strptime(date_str, "%d/%m/%y")
        # Make it offset-aware by assigning UTC timezone
        return pytz.utc.localize(naive_datetime)
    except ValueError:
        logger.error("Invalid date format: %s. Expected DD/MM/YY.", date_str)
        raise ValueError(f"Invalid date format: {date_str}. Expected DD/MM/YY.")



def validate_extracted_info(info):
    # Clean and validate price
    if "price" in info:
        price_value = info["price"]
        if isinstance(price_value, (float, int)):  # Already a valid number
            info["price"] = float(price_value)
        elif isinstance(price_value, str) and price_value.strip().isdigit():  # String containing digits
            info["price"] = float(price_value.strip())
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

    try:
        # Fetch all trips
        results = trips_ref.stream()
        all_trips = [doc.to_dict() for doc in results]
        logger.debug("Fetched all trips: %s", all_trips)

        # Apply local filtering
        def matches_filters(trip):
            # Filter by destination country
            if "destination_country" in extracted_info:
                destination_country = extracted_info["destination_country"]
                if destination_country and destination_country.lower() != "null":
                    if trip.get("destination_country", "").strip() != destination_country.strip():
                        return False

            # Filter by destination city
            if "destination_city" in extracted_info:
                destination_city = extracted_info["destination_city"]
                if destination_city and destination_city.lower() != "null":
                    if trip.get("destination_city", "").strip() != destination_city.strip():
                        return False

            # Filter by departure city
            if "departure_city" in extracted_info:
                departure_city = extracted_info["departure_city"]
                if departure_city and departure_city.lower() != "null":
                    if trip.get("departure_city", "").strip() != departure_city.strip():
                        return False

            # Filter by price
            if "price" in extracted_info:
                price = extracted_info["price"]
                if price and price != "null":
                    max_price = float(price)
                    if trip.get("price", float('inf')) > max_price:
                        return False

            # Filter by available time
            if "available_time" in extracted_info:
                available_time = extracted_info["available_time"]
                from_date = available_time.get("from")
                to_date = available_time.get("to")

                if from_date:
                    if trip.get("departure_date") < convert_to_firestore_date(from_date):
                        return False
                if to_date:
                    if trip.get("return_date") > convert_to_firestore_date(to_date):
                        return False

            # Filter by tags
            if "tags" in extracted_info:
                tags = extracted_info["tags"]
                valid_tags = [tag.strip() for tag in tags if tag.lower() != "null"]
                if valid_tags:
                    trip_tags = trip.get("tags", [])
                    if not set(valid_tags).intersection(trip_tags):
                        return False

            return True

        # Filter trips locally
        filtered_trips = [trip for trip in all_trips if matches_filters(trip)]
        logger.debug("Filtered trips: %s", filtered_trips)
        return filtered_trips

    except Exception as e:
        logger.error("Unexpected error during local filtering: %s", str(e))
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
        
        global user_preferences
        user_preferences = extracted_info
        logger.debug("Saved preferences: %s", user_preferences)

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
async def change_trip_filter(text: str):
    """
    Modify trip preferences and filter trips accordingly.
    """
    try:
        # Step 1: Retrieve the existing preferences
        global user_preferences
        if not user_preferences:
            return {"error": "No preferences found. Please search for trips first."}
        logger.debug("Existing preferences: %s", user_preferences)

        # Step 2: Extract changes to the filtering criteria from the user's text
        extracted_info = second_encounter(text, user_preferences)
        logger.debug("Extracted Info for changes: %s", extracted_info)

        # Step 3: Validate and clean the extracted information
        validate_extracted_info(extracted_info)

        # Step 4: Save the updated preferences
        user_preferences = extracted_info
        logger.debug("Updated preferences: %s", user_preferences)

        # Step 5: Apply the updated criteria to filter trips in Firestore
        filtered_trips = filter_trips(db, extracted_info)

        # Step 6: Return filtered trips or a message if none are found
        if not filtered_trips:
            return {"message": "No trips found matching the updated criteria."}

        return {"Wycieczki": filtered_trips}
    except ValueError as e:
        logger.error("Validation error: %s", str(e))
        return {"error": str(e)}
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return {"error": "An unexpected error occurred."}
