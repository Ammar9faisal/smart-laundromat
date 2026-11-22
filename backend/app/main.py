#initialize FastAPI application and configure CORS middleware to allow requests from the frontend application running on http://localhost:3000
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import machines
from app.routers import auth



app = FastAPI(
    title="Smart Laundromat API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth.router)
app.include_router(machines.router)

@app.get("/health")
def health():
    return {"status": "ok"}
