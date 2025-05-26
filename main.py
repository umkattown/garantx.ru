# main.py

import asyncio
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from database import get_db, create_tables, delete_db_file, engine # Import engine for lifespan
from processing import get_processed_posts
from models import Post # Import Post for potential future use or reference

# --- Pydantic Models --- 

class ProcessedPost(BaseModel):
    id: int
    category: str
    # content: Optional[str] = None # Decide if content should be in response
    word_frequency: Dict[str, int]

class PaginatedPostsResponse(BaseModel):
    total_count: int
    posts: List[ProcessedPost]

# --- Lifespan Management (for DB setup/teardown) --- 

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application startup: Creating database tables...")
    # await delete_db_file() # Optional: Clean DB on each startup for testing
    await create_tables() 
    # Optional: Add some initial data for testing
    # from database import AsyncSessionLocal
    # async with AsyncSessionLocal() as session:
    #     async with session.begin():
    #         if not (await session.execute(select(func.count(Post.id)))).scalar(): # Check if empty
    #             session.add_all([
    #                 Post(category="tech", content="SQLAlchemy is great for Python ORM."),
    #                 Post(category="news", content="FastAPI provides amazing speed."),
    #                 Post(category="tech", content="Async Python with asyncio is powerful."),
    #                 Post(category="tech", content="Another post about Python."),
    #                 Post(category="life", content="Simple life hacks."),
    #                 Post(category="tech", content="More Python content here.")
    #             ])
    #             print("Added initial sample data.")
    yield
    # Clean up resources (optional)
    print("Application shutdown.")
    # await engine.dispose() # Dispose of the engine connection pool

# --- FastAPI App --- 

app = FastAPI(lifespan=lifespan, title="Posts API", version="1.0.0")

# --- API Endpoint --- 

@app.get("/posts/", response_model=PaginatedPostsResponse)
async def read_posts(
    category: Optional[str] = Query(None, description="Filter by category"),
    keywords: Optional[List[str]] = Query(None, description="Filter by keywords in content (case-insensitive, AND logic)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(10, ge=1, le=100, description="Pagination limit"),
    session: AsyncSession = Depends(get_db)
):
    """
    Retrieve posts with filtering, processing (word frequency), and pagination.
    """
    total_count, processed_posts_data = await get_processed_posts(
        session=session,
        category=category,
        keywords=keywords,
        limit=limit,
        offset=offset
    )
    
    return PaginatedPostsResponse(total_count=total_count, posts=processed_posts_data)

# --- Root Endpoint (Optional) --- 

@app.get("/")
async def root():
    return {"message": "Welcome to the Posts API. Go to /docs for documentation."}

# --- Run with Uvicorn (for local testing) --- 
# Use: uvicorn main:app --reload

