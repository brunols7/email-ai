from sqlmodel import SQLModel, Field, Relationship
from typing import Optional

class Email(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_email: str = Field(index=True)
    summary: str
    snippet: str
    sent_date: str
    from_address: str

    category_id: Optional[str] = Field(default=None, foreign_key="category.id")

    category: Optional["Category"] = Relationship(back_populates="emails")