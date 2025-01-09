import os
from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
import re
# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
load_dotenv()

def clean_response(response: str) -> str:
    # Use regex to extract the JSON part from the response
    json_match = re.search(r"{.*}", response, re.DOTALL)
    if json_match:
        return json_match.group(0)
    raise ValueError("Response does not contain valid JSON.")


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
                    You are looking and extracting things like price, destination, 
                    departure date, and return from what they say.
                    User will text you in Polish.
                    Return the response in JSON format like:
                    {{
                        "destination": "<destination>",
                        "price": "<price>",
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
        
        # Clean the response to extract JSON
        cleaned_response = clean_response(raw_response)
        logger.debug("Cleaned OpenAI response: %s", cleaned_response)

        return cleaned_response
    except Exception as e:
        logger.error("Error during OpenAI API call: %s", str(e))
        raise ValueError("Error occurred while processing the OpenAI request.")
