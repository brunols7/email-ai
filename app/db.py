import os
from sqlmodel import create_engine, SQLModel
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:mysecretpassword@db:5432/email_ai_db")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL was not set in the environment variables")

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    print("Creating database tables...")
    SQLModel.metadata.create_all(engine)
    print("Database tables created successfully.")