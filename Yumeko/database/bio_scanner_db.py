from Yumeko.database import bio_scanner_collection


async def add_bio_warn(chat_id: int, user_id: int):
    """
    Adds a bio warning to a user and returns the new warning count.
    """
    result = await bio_scanner_collection.find_one({
        "chat_id": chat_id,
        "user_id": user_id
    })
    
    if result:
        new_count = result.get("warn_count", 0) + 1
        await bio_scanner_collection.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"warn_count": new_count}}
        )
        return new_count
    else:
        await bio_scanner_collection.insert_one({
            "chat_id": chat_id,
            "user_id": user_id,
            "warn_count": 1,
            "approved": False
        })
        return 1


async def get_bio_warns(chat_id: int, user_id: int):
    """
    Gets the warning count for a user.
    """
    result = await bio_scanner_collection.find_one({
        "chat_id": chat_id,
        "user_id": user_id
    })
    
    if result:
        return result.get("warn_count", 0)
    return 0


async def reset_bio_warns(chat_id: int, user_id: int):
    """
    Resets the warning count for a user to 0.
    """
    await bio_scanner_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"warn_count": 0}},
        upsert=True
    )


async def approve_bio(chat_id: int, user_id: int):
    """
    Approves a user to keep links in their bio.
    """
    await bio_scanner_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"approved": True, "warn_count": 0}},
        upsert=True
    )


async def unapprove_bio(chat_id: int, user_id: int):
    """
    Removes bio approval from a user.
    """
    await bio_scanner_collection.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"approved": False}},
        upsert=True
    )


async def is_bio_approved(chat_id: int, user_id: int):
    """
    Checks if a user is approved to keep links in their bio.
    """
    result = await bio_scanner_collection.find_one({
        "chat_id": chat_id,
        "user_id": user_id
    })
    
    if result:
        return result.get("approved", False)
    return False


async def enable_bio_scanner(chat_id: int):
    """
    Enables bio scanner for a chat.
    """
    await bio_scanner_collection.update_one(
        {"chat_id": chat_id, "user_id": 0},  # user_id 0 for chat settings
        {"$set": {"enabled": True}},
        upsert=True
    )


async def disable_bio_scanner(chat_id: int):
    """
    Disables bio scanner for a chat.
    """
    await bio_scanner_collection.update_one(
        {"chat_id": chat_id, "user_id": 0},
        {"$set": {"enabled": False}},
        upsert=True
    )


async def is_bio_scanner_enabled(chat_id: int):
    """
    Checks if bio scanner is enabled for a chat.
    Default is True if not set.
    """
    result = await bio_scanner_collection.find_one({
        "chat_id": chat_id,
        "user_id": 0
    })
    
    if result:
        return result.get("enabled", True)
    return True  # Enabled by default


async def get_all_bio_warns_in_chat(chat_id: int):
    """
    Gets all users with bio warnings in a specific chat.
    """
    cursor = bio_scanner_collection.find({
        "chat_id": chat_id,
        "user_id": {"$ne": 0}  # Exclude settings document
    })
    return await cursor.to_list(None)


async def delete_bio_data(chat_id: int, user_id: int):
    """
    Deletes all bio scanner data for a user in a chat.
    """
    await bio_scanner_collection.delete_one({
        "chat_id": chat_id,
        "user_id": user_id
    })


async def delete_chat_bio_data(chat_id: int):
    """
    Deletes all bio scanner data for a chat.
    """
    await bio_scanner_collection.delete_many({"chat_id": chat_id})
