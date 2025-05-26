# database.py

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Define the database URL (using SQLite for simplicity)
DATABASE_URL = "sqlite+aiosqlite:///./posts.db"

# Create the async engine
engine = create_async_engine(DATABASE_URL, echo=False) # Set echo=True for SQL logging

# Create a configured "Session" class
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Dependency to get DB session
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Function to create tables (run once at startup)
async def create_tables():
    from models import Base # Import Base here to avoid circular imports
    async with engine.begin() as conn:
        # Drop tables if they exist (for easy reruns during development)
        # await conn.run_sync(Base.metadata.drop_all)
        # Create tables
        await conn.run_sync(Base.metadata.create_all)

# Function to delete the database file
async def delete_db_file():
    db_path = DATABASE_URL.split("///")[-1]
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Database file {db_path} deleted.")
    else:
        print(f"Database file {db_path} not found.")
