#initialize FastAPI application and configure CORS middleware to allow requests from the frontend application running on http://localhost:3000
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import machines
from app.routers import auth
from app.routers import reservations
from app.routers import payments
from app.routers import admin

# Application events (reservations, payments) are logged at INFO. Tokens, card
# details and other personal data are never written to the log.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(
    title="Smart Laundromat API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth.router)
app.include_router(machines.router)
app.include_router(reservations.router)
app.include_router(payments.router)
app.include_router(admin.router)

@app.get("/health")
def health():
    return {"status": "ok"}
