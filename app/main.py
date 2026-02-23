# app/main.py
import sys
from loguru import logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

logger.remove()
logger.add(sys.stdout, serialize=True, enqueue=True)

app = FastAPI(title=settings.PROJECT_NAME)

origins = [
    "http://localhost:3000",
    "https://404by.me",
    "https://booking.404by.me",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME}"}