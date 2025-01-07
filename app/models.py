from pydantic import BaseModel
from typing import  Optional
from datetime import datetime
from typing import ClassVar
from pydantic import BaseModel

class VoiceCommand(BaseModel):
    command: str
    known_destinations: ClassVar[dict] = {
    "hiszpania": "Spain",
    "francja": "France",
    "niemcy": "Germany",
    "włochy": "Italy"
    }
    
    

class Trip(BaseModel):
    id: str
    destination: str
    description: str
    price: float
    departure_date: datetime
    return_date: datetime 
    spots_left: int
    
class UserRegister(BaseModel):
    email: str
    password: str
    
known_destinations = {
    "hiszpania": "Spain",
    "francja": "France",
    "niemcy": "Germany",
    "włochy": "Italy"
}