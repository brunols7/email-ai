from sqlmodel import SQLModel, Field
from typing import Optional
from uuid import uuid4

class Category(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    description: Optional[str] = None
    user_email: str
