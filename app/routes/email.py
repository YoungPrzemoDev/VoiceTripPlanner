import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import logging
import os
from fastapi import APIRouter, HTTPException, Depends, Query

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize FastAPI router
router = APIRouter()

# Function to send an email
def send_email(to_email: str, subject: str, body: str):
    # Email credentials
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")

    try:
        # Create the email
        message = MIMEMultipart()
        message["From"] = SMTP_USERNAME
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "html"))

        # Connect to the SMTP server and send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, to_email, message.as_string())

        return {"message": "Email sent successfully!"}
    except Exception as e:
        logger.error("Failed to send email: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to send email")

# Endpoint to send trip offers via email
@router.post("/send-trip-offer")
async def send_trip_offer(email: str, trip_data: dict):
    try:
        # Prepare the email content
        subject = "Ekskluzywna Oferta Wycieczki!"
        template = Template("""
        <h1>Szczegóły Oferty Wycieczki</h1>
        <p>Szanowny Kliencie,</p>
        <p>Z przyjemnością przedstawiamy ekskluzywną ofertę wycieczki specjalnie dla Ciebie:</p>
        <ul>
            <li><b>Kraj docelowy:</b> {{ destination_country }}</li>
            <li><b>Miasto docelowe:</b> {{ destination_city }}</li>
            <li><b>Cena:</b> {{ price }} PLN</li>
            <li><b>Data wyjazdu:</b> {{ departure_date }}</li>
            <li><b>Data powrotu:</b> {{ return_date }}</li>
            <li><b>Miasto wylotu:</b> {{ departure_city }}</li>
        </ul>
        <p>Mamy nadzieję, że ta oferta spełni Twoje oczekiwania. W razie jakichkolwiek pytań zapraszamy do kontaktu.</p>
        <p>Z poważaniem,<br>Zespół Biura Podróży</p>
        """)
        body = template.render(
            destination_country=trip_data.get("destination_country", "Brak danych"),
            destination_city=trip_data.get("destination_city", "Brak danych"),
            price=trip_data.get("price", "Brak danych"),
            departure_date=trip_data.get("departure_date", "Brak danych"),
            return_date=trip_data.get("return_date", "Brak danych"),
            departure_city=trip_data.get("departure_city", "Brak danych"),
            tags=trip_data.get("tags", [])
        )

        # Send the email
        response = send_email(email, subject, body)
        return {"Email": response}
    except HTTPException as e:
        logger.error("Failed to send trip offer email: %s", str(e.detail))
        return {"error": str(e.detail)}
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return {"error": "An unexpected error occurred."}
