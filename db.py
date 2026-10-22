import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Load environment variables from .env
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "")
DB_NAME = os.getenv("MONGODB_DB_NAME", "rigcheck_db")

client = None
db = None

def get_database():
    """Returns the async MongoDB database instance."""
    global client, db
    if db is None:
        if not MONGODB_URI or MONGODB_URI == "your_connection_string_here":
            raise RuntimeError("MONGODB_URI is not configured in .env")
        try:
            client = AsyncIOMotorClient(MONGODB_URI, tlsCAFile=certifi.where())
        except Exception:
            client = AsyncIOMotorClient(MONGODB_URI)
        db = client[DB_NAME]
    return db

async def init_db():
    """Initializes collections and indexes (sparse unique indexes on email, google_id, steam_id)."""
    try:
        database = get_database()
        users_col = database["users"]
        # Use partialFilterExpression so documents with null/absent values are NEVER indexed or conflicted
        await users_col.create_index(
            "email",
            unique=True,
            partialFilterExpression={"email": {"$type": "string"}}
        )
        await users_col.create_index(
            "google_id",
            unique=True,
            partialFilterExpression={"google_id": {"$type": "string"}}
        )
        await users_col.create_index(
            "steam_id",
            unique=True,
            partialFilterExpression={"steam_id": {"$type": "string"}}
        )

        sessions_col = database["sessions"]
        await sessions_col.create_index("token", unique=True)
        print("[MongoDB] Database initialized with partial unique indexes on users and sessions.")
    except Exception as e:
        print(f"[MongoDB] Warning: Failed to initialize indexes: {e}")

async def close_db():
    """Closes the MongoDB connection."""
    global client, db
    if client:
        client.close()
        client = None
        db = None
