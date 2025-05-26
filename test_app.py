# test_app.py

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Adjust imports to match project structure
from main import app
from models import Base, Post # Import Base and Post from models
from database import get_db, DATABASE_URL # Keep other imports from database
from models import Post

# Use a separate test database
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_posts.db"

# Create a new engine and session for testing
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Override the get_db dependency for testing
async def override_get_db() -> AsyncSession:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

# Fixture to set up and tear down the test database
@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    # Create tables before tests run
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Ensure clean state
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Optional: Clean up after tests if needed, though usually a fresh DB is created each run
    # async with test_engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

# Fixture to add sample data for each test function
@pytest_asyncio.fixture(scope="function")
async def add_sample_data():
    async with TestingSessionLocal() as session:
        async with session.begin():
            # Clear existing data first
            await session.execute(Post.__table__.delete())
            # Add new data
            session.add_all([
                Post(id=1, category="tech", content="SQLAlchemy is great for Python ORM."),
                Post(id=2, category="news", content="FastAPI provides amazing speed."),
                Post(id=3, category="tech", content="Async Python with asyncio is powerful."),
                Post(id=4, category="tech", content="Another post about Python."),
                Post(id=5, category="life", content="Simple life hacks."),
                Post(id=6, category="tech", content="More Python content here.")
            ])

# ... (keep other imports)

# Fixture for the async HTTP client
@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncClient:
    # Use ASGITransport to test the FastAPI app with httpx.AsyncClient
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
# --- Test Cases --- 

@pytest.mark.asyncio
async def test_read_posts_no_filters(client: AsyncClient, add_sample_data):
    response = await client.get("/posts/?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 6
    assert len(data["posts"]) == 6
    assert data["posts"][0]["id"] == 1
    assert data["posts"][0]["category"] == "tech"
    assert "word_frequency" in data["posts"][0]
    assert data["posts"][0]["word_frequency"]["python"] == 1

@pytest.mark.asyncio
async def test_read_posts_pagination(client: AsyncClient, add_sample_data):
    # Page 1
    response = await client.get("/posts/?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 6
    assert len(data["posts"]) == 2
    assert data["posts"][0]["id"] == 1
    assert data["posts"][1]["id"] == 2

    # Page 2
    response = await client.get("/posts/?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 6
    assert len(data["posts"]) == 2
    assert data["posts"][0]["id"] == 3
    assert data["posts"][1]["id"] == 4

@pytest.mark.asyncio
async def test_read_posts_filter_category(client: AsyncClient, add_sample_data):
    response = await client.get("/posts/?category=tech&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 4
    assert len(data["posts"]) == 4
    assert all(p["category"] == "tech" for p in data["posts"])
    assert data["posts"][0]["id"] == 1
    assert data["posts"][1]["id"] == 3

@pytest.mark.asyncio
async def test_read_posts_filter_keywords(client: AsyncClient, add_sample_data):
    response = await client.get("/posts/?keywords=python&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 4 # Posts 1, 3, 4, 6 contain Python (case-insensitive)   # Correction: Post 6 also contains Python. Let's recheck data. ID 1, 3, 4, 6. Total 4.   # Let's re-run the mental check: 1: Python, 3: Python, 4: Python, 6: Python. Yes, 4 posts.    # The test data has 4 posts with 'Python'. Let's adjust the assertion.
    # Rerun mental check: 1: SQLAlchemy is great for Python ORM. (Yes) 3: Async Python with asyncio is powerful. (Yes) 4: Another post about Python. (Yes) 6: More Python content here. (Yes)
    # Okay, the total count should be 4.
    assert data["total_count"] == 4
    assert len(data["posts"]) == 4
    assert data["posts"][0]["id"] == 1
    assert data["posts"][1]["id"] == 3
    assert data["posts"][2]["id"] == 4
    assert data["posts"][3]["id"] == 6
    assert "python" in data["posts"][0]["word_frequency"]

@pytest.mark.asyncio
async def test_read_posts_filter_category_and_keywords(client: AsyncClient, add_sample_data):
    response = await client.get("/posts/?category=tech&keywords=python&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    # All 4 posts containing 'python' are also category 'tech'.
    assert data["total_count"] == 4
    assert len(data["posts"]) == 4
    assert all(p["category"] == "tech" for p in data["posts"])
    assert all("python" in p["word_frequency"] for p in data["posts"])
    assert data["posts"][0]["id"] == 1
    assert data["posts"][3]["id"] == 6

@pytest.mark.asyncio
async def test_read_posts_filter_multiple_keywords(client: AsyncClient, add_sample_data):
    # Test AND logic: posts containing BOTH 'python' AND 'async'
    response = await client.get("/posts/?keywords=python&keywords=async&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    # Only post 3 contains both 'Python' and 'Async'
    assert data["total_count"] == 1
    assert len(data["posts"]) == 1
    assert data["posts"][0]["id"] == 3
    assert "python" in data["posts"][0]["word_frequency"]
    assert "async" in data["posts"][0]["word_frequency"]

@pytest.mark.asyncio
async def test_word_frequency_calculation(client: AsyncClient, add_sample_data):
    response = await client.get("/posts/?limit=1&offset=0") # Get post 1
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 6
    assert len(data["posts"]) == 1
    word_freq = data["posts"][0]["word_frequency"]
    assert word_freq == {"sqlalchemy": 1, "is": 1, "great": 1, "for": 1, "python": 1, "orm": 1}

@pytest.mark.asyncio
async def test_empty_results(client: AsyncClient, add_sample_data):
    response = await client.get("/posts/?category=nonexistent&limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert len(data["posts"]) == 0

