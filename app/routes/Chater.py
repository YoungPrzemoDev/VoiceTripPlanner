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
                You are looking and extracting key information from the text provided by the user.

                Extract the following:
                1. **Price**: Should only be a number, without any words or currency symbols. If not mentioned, return "null".
                2. **Country Destination**: Only real countries (e.g., Poland, France). If not mentioned, return "null".
                3. **City Destination**: The specific city mentioned in the destination. If not mentioned, return "null".
                4. **Departure Date**: The starting date for the trip, provided in the format DD/MM/YY. If not mentioned, return "01/01/01".
                5. **Return Date**: The ending date for the trip, provided in the format DD/MM/YY. If not mentioned, return "01/01/01".
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
                    Witaj! Jesteś konsultantem biura podróży. Twoim zadaniem jest uprzejmie zapytać użytkownika w języku polskim o brakujące informacje, 
                    które nie zostały określone w poniższym formularzu oraz czy chcaiułby cos zmienic:

                    {text}

                    Jeśli użytkownik nie podał konkretnej informacji, możesz zasugerować, że można ją "Do sprecyzowania później". 
                    Pamiętaj, aby odpowiedzieć uprzejmie i z szacunkiem. Oto pola, które możesz uzupełnić:

                    1. **Cena**: Czy masz określony budżet? Jeśli tak, jaka jest maksymalna cena podróży? 
                    2. **Kraj docelowy**: Do jakiego kraju chciał(a)byś podróżować?
                    3. **Miasto docelowe**: Czy masz na myśli konkretne miasto?
                    4. **Data wyjazdu**: Kiedy chciał(a)byś wyjechać? Format: DD/MM/RR.
                    5. **Data powrotu**: Kiedy planujesz powrót? Format: DD/MM/RR.
                    6. **Miasto wylotu**: Z jakiego miasta chciał(a)byś wylecieć?
                    7. **Bagaż**: Czy planujesz zabrać bagaż? Jeśli tak, ile sztuk?
                    8. **Tagi**: Jakie są Twoje preferencje dotyczące wycieczki (np. zwiedzanie, ciepłe kraje, góry)?

                    Jeśli użytkownik nie ma precyzyjnych informacji, odpowiedz: "Do sprecyzowania później".
                    Zawsze bądź pomocny/a i uprzejmy/a!
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
    
def second_encounter(text: str):
    try:
        client = OpenAI(
            api_key=os.environ.get("OPEN_AI_API_KEY"),
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f"""
                Hello, you are a travel agency consultant, and your task is to extract key information that
                the user provides and identify any changes the user wants to make to their preferences or trip details.

                Extract the following:
                1. **Price**: Should only be a number, without any words or currency symbols. If not mentioned, return "null".
                2. **Country Destination**: Only real countries (e.g., Poland, France). If not mentioned, return "null".
                3. **City Destination**: The specific city mentioned in the destination. If not mentioned, return "null".
                4. **Departure Date**: The starting date for the trip, provided in the format DD/MM/YY. If not mentioned, return "01/01/01".
                5. **Return Date**: The ending date for the trip, provided in the format DD/MM/YY. If not mentioned, "01/01/01".
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

                If any value is not provided in the user's input, return "null" for that field.

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

# if __name__ == "__main__":
#     try:
#         user_text = "Chcę lecieć do ciepłych krajów w maju, najlepiej od 10 do 20. Mój budżet to 3000 złotych. Nie będę brał bagażu"
#         extracted_info = extract_info(user_text)  # Call the function with user_text
#         print("Extracted Information:", extracted_info)  # Print the extracted information
        
#         konsultatnt = extract_info_from_another_asks(extracted_info)
#         print(konsultatnt)
        
#         user_answer = "chce zmienić budzet do 5000 złotych i wezme 2 bagaże"
#         doprecyzowanie = extract_info_from_third_ask(user_answer)
#     except Exception as e:
#         print("An error occurred:", str(e))



