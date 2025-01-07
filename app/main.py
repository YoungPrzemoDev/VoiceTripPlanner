from fastapi import FastAPI
from app.routes import trips, users

app = FastAPI()

#tags dla swaggera sa
app.include_router(users.router, prefix="/users",tags=["Users"])
#app.include_router(bookings.router, prefix="/bookings",tags=["Bookings"])
app.include_router(trips.router, prefix="/trips",tags=["Trips"])

    