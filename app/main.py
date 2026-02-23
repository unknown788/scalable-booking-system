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

# Base origins always allowed
_base_origins = [
    "http://localhost:3000",
    "https://404by.me",
    "https://booking.404by.me",
]

# CORS_ORIGINS env var: comma-separated list of extra origins from Heroku config
_extra = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
origins = list(dict.fromkeys(_base_origins + _extra))  # deduplicate, preserve order

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",   # all Vercel preview deploys
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME}"}