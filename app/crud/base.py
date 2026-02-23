# app/crud/base.py
# Generic CRUD base class.
# Any model can extend this to get get/create/update/delete for free.
# Currently crud_event and crud_user use standalone functions instead,
# but this base is here for future use or refactoring.

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.base_class import Base

# ModelType = any SQLAlchemy model  e.g. User, Event, Venue
# CreateSchemaType = the Pydantic create schema  e.g. UserCreate
# UpdateSchemaType = the Pydantic update schema  e.g. UserUpdate
ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic CRUD base with default methods:
      get, get_multi, create, update, remove

    Usage:
      class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
          # get/create/update/remove all work automatically
          # add custom methods here e.g. get_by_email()
          ...

      crud_user = CRUDUser(User)
    """

    def __init__(self, model: Type[ModelType]):
        """
        Store the SQLAlchemy model class.
        e.g. CRUDBase(User) stores User as self.model
        """
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        """SELECT * FROM table WHERE id = :id LIMIT 1"""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """SELECT * FROM table OFFSET skip LIMIT limit"""
        return db.query(self.model).offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        INSERT INTO table (...) VALUES (...)
        Converts Pydantic schema → dict → SQLAlchemy model → DB row
        """
        obj_in_data = jsonable_encoder(obj_in)     # Pydantic → dict
        db_obj = self.model(**obj_in_data)          # dict → SQLAlchemy model
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        UPDATE table SET col=val WHERE id = :id
        Accepts either a Pydantic schema or a plain dict.
        Only updates fields that are explicitly provided.
        """
        obj_data = jsonable_encoder(db_obj)

        # Accept dict or Pydantic schema
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
            # exclude_unset=True → only fields the caller explicitly set
            # prevents overwriting fields with None accidentally

        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: int) -> ModelType:
        """DELETE FROM table WHERE id = :id"""
        obj = db.query(self.model).get(id)
        db.delete(obj)
        db.commit()
        return obj