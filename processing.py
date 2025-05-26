# processing.py

import re
from collections import Counter
from typing import Optional, List, Dict, Any, Tuple

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Post

# Helper function to clean and count words
def calculate_word_frequency(text: str) -> Dict[str, int]:
    if not text:
        return {}
    # Simple cleaning: lowercase and remove non-alphanumeric characters
    words = re.findall(r'\b\w+\b', text.lower())
    return dict(Counter(words))

# Core function for filtering, processing, and paginating posts
async def get_processed_posts(
    session: AsyncSession,
    category: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    limit: int = 10, # Default page size
    offset: int = 0  # Default starting point
) -> Tuple[int, List[Dict[str, Any]]]:
    """Fetches posts based on filters, processes them, and returns a paginated list with total count."""

    # Base query for filtering
    base_stmt = select(Post)
    if category:
        base_stmt = base_stmt.where(Post.category == category)
    if keywords:
        for keyword in keywords:
            base_stmt = base_stmt.where(Post.content.ilike(f"%{keyword}%"))

    # --- Get Total Count ---    
    # Create a query to count the total matching rows *before* pagination
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_count_result = await session.execute(count_stmt)
    total_count = total_count_result.scalar_one_or_none() or 0

    # --- Get Paginated Results ---    
    # Apply pagination and ordering to the base query
    paginated_stmt = base_stmt.order_by(Post.id).offset(offset).limit(limit)
    
    # Execute the query to get posts for the current page
    result = await session.execute(paginated_stmt)
    posts_on_page = result.scalars().all()

    # --- Process Results ---    
    processed_results = []
    for post in posts_on_page:
        word_freq = calculate_word_frequency(post.content)
        processed_results.append({
            "id": post.id,
            "category": post.category,
            # "content": post.content, # Optionally omit content
            "word_frequency": word_freq
        })

    return total_count, processed_results

# --- Example Usage (can be removed later or moved to tests) ---
async def example_usage():
    from database import get_db, create_tables, delete_db_file, AsyncSessionLocal
    from sqlalchemy.ext.asyncio import AsyncSession

    # Setup DB (for testing)
    await delete_db_file() # Clean slate
    await create_tables()

    # Add some sample data
    async with AsyncSessionLocal() as session:
        async with session.begin():
            session.add_all([
                Post(category="tech", content="SQLAlchemy is great for Python ORM."),
                Post(category="news", content="FastAPI provides amazing speed."),
                Post(category="tech", content="Async Python with asyncio is powerful."),
                Post(category="tech", content="Another post about Python."),
                Post(category="life", content="Simple life hacks."),
                Post(category="tech", content="More Python content here.")
            ])

    print("--- Fetching page 1 (limit 2) with processing ---")
    async for db_session in get_db():
        total, posts = await get_processed_posts(db_session, limit=2, offset=0)
        print(f"Total posts found: {total}")
        print(f"Posts on page 1: {posts}")

    print("\n--- Fetching page 2 (limit 2) with processing ---")
    async for db_session in get_db():
        total, posts = await get_processed_posts(db_session, limit=2, offset=2)
        print(f"Total posts found: {total}") # Should be same total
        print(f"Posts on page 2: {posts}")

    print("\n--- Fetching 'tech' posts with 'python' keyword (page 1, limit 5) ---")
    async for db_session in get_db():
        total, posts = await get_processed_posts(db_session, category="tech", keywords=["python"], limit=5, offset=0)
        print(f"Total 'tech' posts with 'python': {total}")
        print(f"Posts on page 1: {posts}")

if __name__ == "__main__":
    import asyncio
    # asyncio.run(example_usage()) # Uncomment to run the example
