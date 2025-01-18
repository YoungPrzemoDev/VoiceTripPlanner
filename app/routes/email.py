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
    SMTP_USERNAME = os.environ.get("username")
    SMTP_PASSWORD = os.environ.get("userpassy")

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
    """
    Send a trip offer to the user's email.

    Parameters:
        email (str): Recipient's email address.
        trip_data (dict): Details about the trip.

    Example trip_data:
    {
        "destination_country": "France",
        "destination_city": "Paris",
        "price": 1500,
        "departure_date": "10/05/2025",
        "return_date": "20/05/2025",
        "departure_city": "New York",
        "tags": ["sightseeing", "romantic"]
    }
    """
    try:
        # Prepare the email content
        subject = "Your Exclusive Trip Offer!"
        template = Template("""
        <h1>Trip Offer Details</h1>
        <p>Dear Customer,</p>
        <p>We are excited to share this exclusive trip offer with you:</p>
        <ul>
            <li><b>Destination Country:</b> {{ destination_country }}</li>
            <li><b>Destination City:</b> {{ destination_city }}</li>
            <li><b>Price:</b> ${{ price }}</li>
            <li><b>Departure Date:</b> {{ departure_date }}</li>
            <li><b>Return Date:</b> {{ return_date }}</li>
            <li><b>Departure City:</b> {{ departure_city }}</li>
            <li><b>Tags:</b> {{ tags | join(", ") }}</li>
        </ul>
        <p>We hope this offer meets your expectations. Feel free to contact us for any queries.</p>
        <p>Best regards,<br>Travel Agency Team</p>
        """)
        body = template.render(
            destination_country=trip_data.get("destination_country", "N/A"),
            destination_city=trip_data.get("destination_city", "N/A"),
            price=trip_data.get("price", "N/A"),
            departure_date=trip_data.get("departure_date", "N/A"),
            return_date=trip_data.get("return_date", "N/A"),
            departure_city=trip_data.get("departure_city", "N/A"),
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
