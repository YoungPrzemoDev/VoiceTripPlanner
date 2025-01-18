from openai import OpenAI
import os
import logging
import re
import json
from dotenv import load_dotenv
import morfeusz2 

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Morfeusz for lemmatization
morf = morfeusz2.Morfeusz()

def clean_response(response: str) -> str:
    """
    Extracts the JSON content from the AI response.
    Removes any enclosing triple backticks and formats it properly.
    """
    try:
        # Remove any triple backticks or whitespace
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]  # Remove ```json
        elif response.startswith("```"):
            response = response[3:]  # Remove ```
        if response.endswith("```"):
            response = response[:-3]
        return response.strip()
    except Exception as e:
        logger.error("Failed to clean the response: %s", str(e))
        raise ValueError("Failed to clean the response.")


def normalize_text(text: str) -> str:
    analyses = morf.analyse(text)
    if analyses:
        # Extract the lemma and remove annotations (everything after the colon)
        return analyses[0][2][1].split(":")[0]
    return text  # If no analysis, return original text

def preprocess_json(json_data: dict) -> dict:
    """
    Processes the extracted JSON to normalize text fields like 'destination' and 'city'.
    """
    # Normalize the 'destination' field if it exists
    if "destination" in json_data:
        json_data["destination"] = normalize_text(json_data["destination"])
    
    # Normalize the 'city' field if it exists
    if "city" in json_data:
        json_data["city"] = normalize_text(json_data["city"])
    
    return json_data




def first_encounter(text: str):
    try:
        client = OpenAI(
            api_key=os.environ.get("OPEN_AI_API_KEY"),
        )

        chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"""
                Hello, you are a travel agency consultant, and you are searching in the provided text for key words.
                You are looking and extracting key information from the text provided by the user. Everything in polish language

                Extract the following:
                1. **Price**: Should only be a number, without any words or currency symbols. If not mentioned, return "null".
                2. **Country Destination**: Only real countries (e.g., Poland, France). If not mentioned, return "null".
                3. **City Destination**: The specific city mentioned in the destination. If not mentioned, return "null".
                4. **Departure Date**: The starting date for the trip, provided in the format DD/MM/YY. If any of it not mentioned, return for day - 01, for month - 01 and year 2025.
                5. **Return Date**: The ending date for the trip, provided in the format DD/MM/YY. If not mentioned, return for day - 01, for month - 12 and year 2025.
                6. **Departure City**: The city where the user wants to depart from. If not mentioned, return "null".
                7. **Baggage**: Whether the user is taking baggage. Format should be True/False. If not mentioned, return "null".
                8. **Number of Baggage**: The number of baggage items, given as a number (e.g., 1, 2, 3). If not mentioned, return "null".
                9. **Tags**: Keywords or phrases describing the trip type, such as "sightseeing", "ciepłe kraje" (warm countries), "może góry" (maybe mountains). If not mentioned, return "null".

                Return the response in a JSON format like this:
                {{
                    "destination_country": "<country>",
                    "destination_city": "<city>",
                    "price": "<price>",
                    "departure_city": "<departure_city>",
                    "baggage": "<baggage>",
                    "number_of_baggage": "<number>",
                    "tags": ["<tag1>", "<tag2>", ...],
                    "available_time": {{
                        "from": "<start_date>",
                        "to": "<end_date>"
                    }}
                }}


                HERE IS TEXT FROM USER:
                {text}
                """,
            }
        ],
        model="gpt-4o-mini",
    )

        raw_response = chat_completion.choices[0].message.content
        logger.debug("Raw OpenAI response: %s", raw_response)

        cleaned_response = clean_response(raw_response)
        logger.debug("Cleaned OpenAI response: %s", cleaned_response)

        extracted_data = json.loads(cleaned_response)

        normalized_data = preprocess_json(extracted_data)
        logger.debug("Normalized Data: %s", normalized_data)

        return normalized_data
    except Exception as e:
        logger.error("Error during OpenAI API call: %s", str(e))
        raise ValueError("Error occurred while processing the OpenAI request.")
    

def ask_user(text: str):
    try:
        client = OpenAI(
            api_key=os.environ.get("OPEN_AI_API_KEY"),
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {
                "role": "user",
                "content": f"""
                Hello! You are a travel agency consultant. Your task is to politely ask the user in Polish about missing information 
                that was not specified in the form below, i.e., any field with a value of null. If any information is already provided 
                (anything other than null), you should not ask about it:

                {text}

                If the user has not provided specific information, you can suggest that it can be "Specified later." 
                Remember to respond politely and respectfully. Here are the fields you can complete:

                1. **Price**: Do you have a specific budget? If so, what is the maximum price for your trip? 
                2. **Destination country**: Which country would you like to travel to?
                3. **Destination city**: Do you have a specific city in mind?
                4. **Departure date**: When would you like to depart? Format: DD/MM/YY.
                5. **Return date**: When do you plan to return? Format: DD/MM/YY.
                6. **Departure city**: From which city would you like to depart?
                7. **Baggage**: Do you plan to bring baggage? If so, how many pieces?
                8. **Tags**: What are your preferences for the trip (e.g., sightseeing, warm countries, mountains)?

                If the user does not have precise information, respond with: "Can be specified later." Do not mention **Price** or **Destination country** explicitly; just ask about it if the information is missing. 
                Always be helpful and polite!
                """,
            }
            ],
            model="gpt-4o-mini",
        )

        raw_response = chat_completion.choices[0].message.content
        logger.debug("Raw OpenAI response: %s", raw_response)

        return raw_response
    except Exception as e:
        logger.error("Error during OpenAI API call: %s", str(e))
        raise ValueError("Error occurred while processing the OpenAI request.")
    
def second_encounter(text: str, existing_preferences: dict):
    try:
        client = OpenAI(api_key=os.environ.get("OPEN_AI_API_KEY"))

        # Format available_time properly in the existing preferences
        available_time = existing_preferences.get("available_time", {})
        from_date = available_time.get("from", "null")
        to_date = available_time.get("to", "null")

        # Build the prompt with the correctly formatted `available_time`
        prompt = f"""
        Hello, you are a travel agency consultant. Your task is to extract key information from the user's input
        about their travel preferences. Some preferences might already exist, and your job is to identify if the user
        wants to change, add, or keep the existing values.

        Here are the existing values (if any):
        {json.dumps(existing_preferences)}
        
        Your task is to:
        1. Keep the existing values unless the user explicitly mentions a change or provides new preferences.
        2. Update or add information where the user specifies changes or new values.
        3. Do not replace valid existing values with "null" unless the user explicitly states that they should be removed.

        Extract the following details from the user's input:
        - **Price**: Should only be a number, without any words or currency symbols and.
        - **Country Destination**
        - **City Destination**
        - **Departure Date**:The starting date for the trip, provided in the format DD/MM/YY. If any of it not mentioned, return for day - 01, for month - 01 and year 2025.
        - **Return Date**:The ending date for the trip, provided in the format DD/MM/YY. If not mentioned, return for day - 01, for month - 12 and year 2025.
        - **Departure City**
        - **Baggage**: Whether the user is taking baggage. Format should be True/False. If specified that user dont take baggage return False and put 0 in Number of Baggage .If not mentioned, return "null".
        - **Number of Baggage**:The number of baggage items, given as a number (e.g., 1, 2, 3). If not mentioned, return "null".
        - **Tags**

        Return only the updated JSON object, e.g.:
        {{
            "destination_country": "example",
            "destination_city": "example",
            "price": "example",
            "departure_city": "example",
            "baggage": "example",
            "number_of_baggage": "example",
            "tags": ["example1", "example2"],
            "available_time": {{
                "from": "example",
                "to": "example"
            }}
        }}

        HERE IS TEXT FROM USER:
        {text}
        """

        # Send the prompt to OpenAI
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
        )
        raw_response = chat_completion.choices[0].message.content
        logger.debug("Raw OpenAI response: %s", raw_response)

        cleaned_response = clean_response(raw_response)
        logger.debug("Cleaned OpenAI response: %s", cleaned_response)

        extracted_data = json.loads(cleaned_response)

        normalized_data = preprocess_json(extracted_data)
        logger.debug("Normalized Data: %s", normalized_data)

        return normalized_data
    except Exception as e:
        logger.error("Error during OpenAI API call: %s", str(e))
        raise ValueError("Error occurred while processing the OpenAI request.")




