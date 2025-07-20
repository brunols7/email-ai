from sqlmodel import SQLModel, Field
from typing import Optional
import json

class LinkedAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_email: str = Field(index=True)
    linked_email: str = Field(unique=True, index=True)
    token_data: str 
