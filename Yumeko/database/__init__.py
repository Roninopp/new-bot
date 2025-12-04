
from motor.motor_asyncio import AsyncIOMotorClient
from config import config
from pymongo import MongoClient
import asyncio
from cachetools import TTLCache, LRUCache
from Yumeko import log as logger

# Connection pooling settings
MAX_POOL_SIZE = 100
MIN_POOL_SIZE = 10
MAX_IDLE_TIME_MS = 30000  # 30 seconds

# Create connection with optimized settings
try:
    client = AsyncIOMotorClient(
        config.MONGODB_URI,
        maxPoolSize=MAX_POOL_SIZE,
        minPoolSize=MIN_POOL_SIZE,
        maxIdleTimeMS=MAX_IDLE_TIME_MS,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        serverSelectionTimeoutMS=5000,
        waitQueueTimeoutMS=5000,
        retryWrites=True,
        w="majority"  # Write concern for data durability
    )
    db = client[config.DATABASE_NAME]
    
    # Synchronous client for specific operations
    MCL = MongoClient(
        config.MONGODB_URI,
        maxPoolSize=MAX_POOL_SIZE // 2,  # Half the pool size for sync operations
        minPoolSize=MIN_POOL_SIZE // 2,
        maxIdleTimeMS=MAX_IDLE_TIME_MS,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        retryWrites=True
    )
    MDB = MCL[config.DATABASE_NAME]
    
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

# Collection definitions
user_collection = db.Users
afk_collection = db.AFK
rules_collection = db.Rules
announcement_collection = db.AnnouncementData
antichannel_collection = db.AntichannelData
antibanall_collection = db.AntiBanAllSettings
antiflood_collection = db.AntiFloodSettings
approved_collection = db.ApprovedUsers
blacklist_collection = db.BlacklistData
chatbot_collection = db.ChatBotData
filter_collection = db.FilterData
imposter_collection = db.ImposterUsersInfo
locks_collection = db.ChatLocks
warnings_collection = db.WarnData
log_channel_collection = db.LogChannel
nightmode_collection = db.NightMode
cleaner_collection = db.CleanerData
gmute_collection = db.GMutedUsers
gban_collection = db.GBannedUsers
user_chat_collection = db.CommonChatData
total_users = db.YumekoTotalUsers
total_chats = db.YumekoTotalChats
couple_collection = db.Couple
waifu_collection = db.Waifu
gamesdb = db.Games
karma_collection = db.Karma
info_collection = db.UserInfo
greetings_collection = db.WelcomeData
banned_chats = db.BannedChats

# Global caches for frequently accessed data
# Cache for database results with TTL (Time To Live)
DB_CACHE = TTLCache(maxsize=10000, ttl=60)  # 1 minute cache
# Cache for frequently accessed items that should persist longer
PERSISTENT_CACHE = LRUCache(maxsize=5000)
# Lock for cache operations
_cache_lock = asyncio.Lock()

async def setup_indexes():
    """Set up database indexes for optimized queries."""
    try:
        # User related indexes
        await user_collection.create_index("user_id", unique=True)
        await user_collection.create_index("username")
        await user_collection.create_index("first_name")
        await user_collection.create_index("last_name")
        
        # AFK related indexes
        await afk_collection.create_index("user_id", unique=True)
        await afk_collection.create_index("username", unique=False)
        
        # Chat configuration indexes
        await announcement_collection.create_index("chat_id", unique=True)
        await announcement_collection.create_index("announcements_enabled")
        await antichannel_collection.create_index("chat_id", unique=True)
        await antichannel_collection.create_index("antichannel_enabled")
        await antibanall_collection.create_index("chat_id", unique=True)
        await antibanall_collection.create_index("antibanall_enabled")
        await antiflood_collection.create_index("chat_id", unique=True)
        await approved_collection.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
        await blacklist_collection.create_index("chat_id", unique=True)
        await blacklist_collection.create_index("blacklisted_words")
        await blacklist_collection.create_index("blacklisted_stickers")
        await chatbot_collection.create_index("chat_id", unique=True)
        await chatbot_collection.create_index("chatbot_enabled")
        await filter_collection.create_index("chat_id", unique=True)
        await filter_collection.create_index("filters")
        
        # User tracking indexes
        await imposter_collection.create_index("user_id", unique=True)
        await imposter_collection.create_index("username")
        await imposter_collection.create_index("first_name")
        await imposter_collection.create_index("last_name")
        
        # Chat management indexes
        await locks_collection.create_index("chat_id", unique=True)
        await locks_collection.create_index("locks")
        await rules_collection.create_index("chat_id", unique=True)
        await rules_collection.create_index("rules")
        await cleaner_collection.create_index("chat_id", unique=True)
        await cleaner_collection.create_index("cleaner_enabled")
        
        # User-chat relationship indexes
        await user_chat_collection.create_index("user_id", unique=False)
        
        # Game related indexes
        await gamesdb.create_index("user_id", unique=True)
        await gamesdb.create_index("username", unique=False)
        await gamesdb.create_index("coins")
        await gamesdb.create_index("last_date")
        await gamesdb.create_index("last_collection_weekly")
        
        # Global action indexes
        await gmute_collection.create_index("id", unique=True)
        await gban_collection.create_index("id", unique=True)
        
        # Karma system indexes
        await karma_collection.create_index([("user_id", 1), ("chat_id", 1)], unique=True)
        await karma_collection.create_index([("chat_id", 1), ("karma", -1)])
        
        # Other chat settings indexes
        await log_channel_collection.create_index("chat_id", unique=True)
        await nightmode_collection.create_index("chat_id", unique=True)
        await nightmode_collection.create_index("nightmode_enabled")
        await info_collection.create_index("user_id", unique=True)
        await warnings_collection.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
        
        # Compound indexes for frequently accessed patterns
        await user_collection.create_index([("user_id", 1), ("username", 1)])
        await locks_collection.create_index([("chat_id", 1), ("locks", 1)])
        await greetings_collection.create_index([("chat_id", 1), ("welcome_enabled", 1)])
        
        logger.info("Database indexes setup completed")
    except Exception as e:
        logger.error(f"Error setting up indexes: {e}")
        raise

class MongoDB:
    """Enhanced class for interacting with Bot database with caching."""

    def __init__(self, collection) -> None:
        self.collection = MDB[collection]
        self.collection_name = collection
        self.cache_prefix = f"mongo_{collection}_"

    def _get_cache_key(self, query):
        """Generate a cache key from a query."""
        if isinstance(query, dict):
            # Convert dict to a sorted string representation for consistent keys
            key_parts = []
            for k in sorted(query.keys()):
                key_parts.append(f"{k}:{query[k]}")
            return f"{self.cache_prefix}{'_'.join(key_parts)}"
        return f"{self.cache_prefix}{str(query)}"

    # Insert one entry into collection
    def insert_one(self, document):
        """Insert a document with cache invalidation."""
        result = self.collection.insert_one(document)
        # Clear any cache entries that might be affected
        self._invalidate_cache_for_document(document)
        return repr(result.inserted_id)

    # Find one entry from collection with caching
    def find_one(self, query):
        """Find one document with caching."""
        cache_key = self._get_cache_key(query)
        
        # Check cache first
        if cache_key in DB_CACHE:
            return DB_CACHE[cache_key]
        
        # If not in cache, query the database
        result = self.collection.find_one(query)
        
        # Cache the result (even if it's None)
        DB_CACHE[cache_key] = result
        
        return result if result else False

    # Find entries from collection with caching
    def find_all(self, query=None):
        """Find all documents matching query with caching."""
        if query is None:
            query = {}
            
        cache_key = self._get_cache_key(query)
        
        # Check cache first
        if cache_key in DB_CACHE:
            return DB_CACHE[cache_key]
        
        # If not in cache, query the database
        results = list(self.collection.find(query))
        
        # Cache the results
        DB_CACHE[cache_key] = results
        
        return results

    # Count entries from collection with caching
    def count(self, query=None):
        """Count documents with caching."""
        if query is None:
            query = {}
            
        cache_key = f"{self._get_cache_key(query)}_count"
        
        # Check cache first
        if cache_key in DB_CACHE:
            return DB_CACHE[cache_key]
        
        # If not in cache, query the database
        count = self.collection.count_documents(query)
        
        # Cache the count
        DB_CACHE[cache_key] = count
        
        return count

    # Delete entry/entries from collection
    def delete_one(self, query):
        """Delete documents with cache invalidation."""
        # Invalidate cache for this query
        self._invalidate_cache_for_query(query)
        
        # Delete from database
        self.collection.delete_many(query)
        
        # Return updated count
        return self.collection.count_documents({})

    # Replace one entry in collection
    def replace(self, query, new_data):
        """Replace a document with cache invalidation."""
        old = self.collection.find_one(query)
        if not old:
            return None, None
            
        _id = old["_id"]
        
        # Invalidate cache
        self._invalidate_cache_for_query(query)
        self._invalidate_cache_for_document(new_data)
        
        # Replace in database
        self.collection.replace_one({"_id": _id}, new_data)
        
        # Get updated document
        new = self.collection.find_one({"_id": _id})
        
        return old, new

    # Update one entry from collection
    def update(self, query, update):
        """Update a document with cache invalidation."""
        # Invalidate cache
        self._invalidate_cache_for_query(query)
        
        # Update in database
        result = self.collection.update_one(query, {"$set": update})
        
        # Get updated document
        new_document = self.collection.find_one(query)
        
        return result.modified_count, new_document

    def _invalidate_cache_for_query(self, query):
        """Invalidate cache entries related to a query."""
        # This is a simple implementation that clears cache entries with matching prefix
        # A more sophisticated implementation would track dependencies
        prefix = self.cache_prefix
        keys_to_remove = [k for k in DB_CACHE.keys() if k.startswith(prefix)]
        for k in keys_to_remove:
            DB_CACHE.pop(k, None)

    def _invalidate_cache_for_document(self, document):
        """Invalidate cache entries that might be affected by this document."""
        # Simple implementation that clears all cache for this collection
        self._invalidate_cache_for_query({})

    @staticmethod
    def clear_all_caches():
        """Clear all database caches."""
        DB_CACHE.clear()
        PERSISTENT_CACHE.clear()

    @staticmethod
    def close():
        """Close database connection."""
        return MCL.close()

# Async cache helper functions
async def get_cached_data(key, fetch_func, ttl=60):
    """
    Get data from cache or fetch it using the provided function.
    
    Args:
        key: Cache key
        fetch_func: Async function to fetch data if not in cache
        ttl: Time to live in seconds
        
    Returns:
        The cached or freshly fetched data
    """
    async with _cache_lock:
        # Check if in cache and not expired
        if key in PERSISTENT_CACHE:
            return PERSISTENT_CACHE[key]
    
    # If not in cache, fetch it
    data = await fetch_func()
    
    # Store in cache
    async with _cache_lock:
        PERSISTENT_CACHE[key] = data
    
    return data

# Initialize database connection and indexes
async def init_db():
    """Initialize database connection and set up indexes."""
    try:
        # Ping the database to verify connection
        await client.admin.command('ping')
        logger.info("Database connection verified")
        
        # Set up indexes
        await setup_indexes()
        
        return True
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False
