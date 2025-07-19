from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from uuid import uuid4

class Category(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str
    description: Optional[str] = None
    user_email: str = Field(index=True)

    emails: List["Email"] = Relationship(back_populates="category")