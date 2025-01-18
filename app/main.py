from fastapi import FastAPI
from app.routes import trips, email

app = FastAPI()

#tags dla swaggera sa
app.include_router(trips.router, prefix="/trips",tags=["Trips"])
app.include_router(email.router, prefix="/email",tags=["Email"])

    