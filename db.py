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
_activity_collection = None
_ai_history_collection = None

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


async def get_activity_collection():
    """Use the collection only after MongoDB confirms its uniqueness constraint."""
    global _activity_collection
    if _activity_collection is None:
        collection = get_database()["user_game_activity"]
        await collection.create_index([("user_id", 1), ("appid", 1)], unique=True)
        _activity_collection = collection
    return _activity_collection


async def get_ai_history_collection():
    """Returns the user_ai_history collection with compound index on user_id and timestamp."""
    global _ai_history_collection
    if _ai_history_collection is None:
        database = get_database()
        if isinstance(database, dict):
            if "user_ai_history" not in database:
                return None
            collection = database["user_ai_history"]
        else:
            collection = database["user_ai_history"]
        await collection.create_index([("user_id", 1), ("timestamp", -1)])
        _ai_history_collection = collection
    return _ai_history_collection

async def init_db():
    """Initialize authentication and activity indexes."""
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
        await get_activity_collection()
        await get_ai_history_collection()
        print("[MongoDB] Authentication and activity indexes initialized.")
    except Exception as e:
        print(f"[MongoDB] Warning: Failed to initialize indexes: {e}")

async def close_db():
    """Closes the MongoDB connection."""
    global client, db, _activity_collection, _ai_history_collection
    if client:
        client.close()
        client = None
        db = None
        _activity_collection = None
        _ai_history_collection = None
