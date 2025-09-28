# app/api/v1/endpoints/resources.py
from fastapi import APIRouter, HTTPException
from typing import List
from app import schemas

router = APIRouter()

# In-memory "database" for now
fake_db = {
    1: {"id": 1, "name": "Conference Room A", "description": "Large room with projector", "url": "conference-a"},
    2: {"id": 2, "name": "Focus Booth 1", "description": "Small booth for one person", "url": "booth-1"},
}

@router.post("/", response_model=schemas.Resource, status_code=201)
def create_resource(resource: schemas.ResourceCreate):
    """
    Create a new resource.
    (This is a placeholder and doesn't save to a real DB yet).
    """
    new_id = max(fake_db.keys()) + 1
    new_resource = schemas.Resource(id=new_id, **resource.model_dump())
    fake_db[new_id] = new_resource.model_dump()
    return new_resource


@router.get("/", response_model=List[schemas.Resource])
def read_resources():
    """
    Retrieve all resources.
    """
    return list(fake_db.values())
