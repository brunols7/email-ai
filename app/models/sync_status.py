from sqlmodel import SQLModel, Field

class SyncStatus(SQLModel, table=True):
    owner_email: str = Field(primary_key=True)
    status: str