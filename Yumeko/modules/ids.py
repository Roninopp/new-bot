from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto
from Yumeko import app
import config
from pyrogram.enums import MessageEntityType
from Yumeko.decorator.errors import error
from Yumeko.database.common_chat_db import get_common_chat_count
from Yumeko.database.afk_db import is_user_afk
from Yumeko.database.global_actions_db import is_user_gbanned , is_user_gmuted
from Yumeko.database.user_info_db import get_user_infoo

@app.on_message(filters.command("id", prefixes=config.config.COMMAND_PREFIXES))
@error
async def get_id(client: Client, message: Message):
    """
    Handles the /id command, providing Chat ID and user IDs based on context.
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    reply = message.reply_to_message
    entities = message.entities
    command_args = message.command[1:] if len(message.command) > 1 else []

    # Base response
    response = [f"**Chat ID:** `{chat_id}`\n", f"**Your ID:** `{user_id}`\n"]

    # Handle replies
    if reply:
        if reply.forward_from_chat:  # Forwarded message
            response.append(
                f"**Forwarded Chat ID:** `{reply.forward_from_chat.id}`\n"
            )
        elif reply.from_user:  # Reply to a user
            response.append(
                f"**Replied User ID:** `{reply.from_user.id}` ({reply.from_user.mention()})\n"
            )

    # Handle text mentions
    if entities:
        for entity in entities:
            if entity.type == MessageEntityType.TEXT_MENTION:
                response.append(
                    f"**Mentioned User ID:** `{entity.user.id}` ({entity.user.mention()})\n"
                )
                break

    # Handle username arguments
    if command_args:
        username = command_args[0].strip("@")
        try:
            user_details = await client.get_users(username)
            response.append(
                f"**Username ID:** `{user_details.id}` ({user_details.mention()})\n"
            )
        except Exception:
            response.append("")

    # Final fallback: default response
    if len(response) == 2:  # No additional info added
        response.append("")

    await message.reply_text("".join(response))


@app.on_message(filters.command("info", prefixes=config.config.COMMAND_PREFIXES))
@error
async def get_user_info(client: Client, message: Message):
    # Determine target user
    if message.reply_to_message:
        user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        target = message.command[1]
        try:
            if target.isdigit():
                user = await client.get_users(int(target))
            else:
                user = await client.get_users(target)
        except Exception:
            await message.reply_text("❌ User not found!")
            return
    else:
        user = message.from_user

    x = await message.reply_text("Fetching User Info...")

    # Get user info
    user_id = user.id
    first_name = user.first_name or "N/A"
    last_name = user.last_name or "N/A"
    username = f"@{user.username}" if user.username else "N/A"
    mention = user.mention
    dc_id = user.dc_id or "N/A"

    # --- FIX: Define Photo Variables ---
    photo_count = 0
    user_photo = None
    
    try:
        # Get Photo Count
        photo_count = await client.get_chat_photos_count(user_id)
        # Get the first photo ID if count > 0
        if photo_count > 0:
            async for photo in client.get_chat_photos(user_id, limit=1):
                user_photo = photo.file_id
    except Exception:
        pass # Privacy settings might hide photos

    # Fetch full user info for bio
    try:
        full_user = await client.get_chat(user_id)
        bio = full_user.bio or "N/A"
    except Exception:
        bio = "N/A"

    # Fetch additional info from database
    user_info = await get_user_infoo(user_id)
    custom_bio = user_info.get("custom_bio", "N/A") if user_info else "N/A"
    custom_title = user_info.get("custom_title", "N/A") if user_info else "N/A"

    # Calculate health
    health = 100
    if username == "N/A":
        health -= 25
    if photo_count == 0:
        health -= 25
    if bio == "N/A":
        health -= 20

    # Generate health bar
    filled_blocks = health // 10
    empty_blocks = 10 - filled_blocks
    health_bar = f"{'▰' * filled_blocks}{'▱' * empty_blocks}"
   
    # Prepare caption
    caption = (
        f"     【 **User Information** 】\n"
        f"➢ **ID:** `{user_id}`\n"
        f"➢ **First Name:** `{first_name}`\n"
        f"➢ **Last Name:** `{last_name}`\n"
        f"➢ **Username:** {username}\n"
        f"➢ **Mention:** {mention}\n"
        f"➢ **DC ID:** `{dc_id}`\n"
        f"➢ **Bio:** `{bio}`\n\n"
        f"➢ **Custom Bio:** `{custom_bio}`\n"
        f"➢ **Custom Tag:** `{custom_title}`\n"
        f"➢ **Profile Photos:** `{photo_count} {'Photo' if photo_count == 1 else 'Photos'}`\n"
        f"➢ **Health:** `{health}%`\n"
        f"    {health_bar}\n\n"
    )

    # Additional statuses
    is_afk = await is_user_afk(user_id)
    caption += f"➢ **AFK Status:** `{'Currently Away From Keyboard !!' if is_afk else 'No'}`\n"
    
    try:
        common_groups = await get_common_chat_count(user_id)
    except:
        common_groups = 0
        
    caption += f"➢ **Common Groups:** `{common_groups}`\n"
    caption += f"➢ **Globally Banned:** `{'Yes' if await is_user_gbanned(user_id) else 'No'}`\n"
    caption += f"➢ **Globally Muted:** `{'Yes' if await is_user_gmuted(user_id) else 'No'}`\n"

    # Send response
    try:
        if user_photo:
            await x.edit_media(InputMediaPhoto(
                media=user_photo,
                caption=caption
            ))
        else:
            await x.edit_text(caption)
    except Exception as e:
        await x.edit_text(f"{caption}\n\n⚠️ Error showing photo: {e}")

__module__ = "ID"
__help__ = """
**User Commands:**
  ✧ `/id`: Displays your chat ID and user ID.
  ✧ `/id [username]`: Displays ID of specific user.
  ✧ `/info [username/reply]`: Fetches detailed info about a user.
"""
