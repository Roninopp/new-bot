from Yumeko.database import aura_collection

async def increase_aura(user_id: int, user_name: str, chat_id: int, points: int = 1):
    """Increase the aura points for a user in a specific chat."""
    aura_collection.update_one(
        {"user_id": user_id, "chat_id": chat_id},
        {
            "$inc": {"aura": points},
            "$setOnInsert": {"user_id": user_id, "chat_id": chat_id, "user_name": user_name},
        },
        upsert=True,
    )

async def decrease_aura(user_id: int, user_name: str, chat_id: int, points: int = 1):
    """Decrease the aura points for a user in a specific chat."""
    aura_collection.update_one(
        {"user_id": user_id, "chat_id": chat_id},
        {
            "$inc": {"aura": -points},
            "$setOnInsert": {"user_id": user_id, "chat_id": chat_id, "user_name": user_name},
        },
        upsert=True,
    )


async def get_aura(user_id: int, chat_id: int) -> int:
    """Get the current aura points for a user in a specific chat."""
    user_aura = await aura_collection.find_one({"user_id": user_id, "chat_id": chat_id})
    return user_aura["aura"] if user_aura else 0


async def top_aura(chat_id: int, limit: int = 10) -> list:
    """Get the top users with the highest aura in a specific chat."""
    cursor = aura_collection.find({"chat_id": chat_id}).sort("aura", -1).limit(limit)
    top_users = []
    async for user in cursor:
        top_users.append({"user_id": user["user_id"], "aura": user["aura"], "user_name": user.get("user_name", "Unknown")})
    return top_users
