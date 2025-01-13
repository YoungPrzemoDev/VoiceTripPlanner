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
    """
    json_match = re.search(r"{.*}", response, re.DOTALL)
    if json_match:
        return json_match.group(0)
    logger.error("Response does not contain valid JSON.")
    raise ValueError("Response does not contain valid JSON.")

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




def extract_info(text: str):
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
                    You are looking and extracting things.
                    price - shoudl be just number without any words.
                    destiantion.
                    City in destination
                    departure date, and return from what they say - format DD/MM/RR. 
                    baggage - format True/False
                    If anything is not give, write None
                    User will text you in Polish.
                    Return the response in JSON format like:
                    {{
                        "destination": "<destination>",
                        "city":"<city>"
                        "price": "<price>",
                        "baggage": "<baggage>"
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
            model="gpt-4",
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
    
# Example usage
if __name__ == "__main__":
    try:
        user_text = "Chcę lecieć do Paryża w maju, najlepiej od 10 do 20. mj budzet to 3000 zlotych?"
        extracted_info =  (user_text)
        print("Extracted Information:", extracted_info)
    except Exception as e:
        print("An error occurred:", str(e))


