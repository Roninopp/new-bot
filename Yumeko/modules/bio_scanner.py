from pyrogram import Client, filters
from pyrogram.types import Message, ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus
from Yumeko import app
import config
import re
from Yumeko.decorator.errors import error
from Yumeko.database.bio_scanner_db import (
    add_bio_warn,
    get_bio_warns,
    reset_bio_warns,
    is_bio_approved,
    approve_bio,
    unapprove_bio,
    is_bio_scanner_enabled,
    enable_bio_scanner,
    disable_bio_scanner
)


# Regex patterns to detect Telegram links
TELEGRAM_LINK_PATTERNS = [
    r't\.me/[a-zA-Z0-9_]+',
    r'https?://t\.me/[a-zA-Z0-9_]+',
    r'telegram\.me/[a-zA-Z0-9_]+',
    r'https?://telegram\.me/[a-zA-Z0-9_]+'
]


async def check_user_bio(client: Client, user_id: int, chat_id: int):
    """
    Checks if a user's bio contains Telegram promotion links.
    Returns (has_link: bool, links_found: list)
    """
    try:
        # Get full user info including bio
        full_user = await client.get_chat(user_id)
        bio = full_user.bio or ""
        
        if not bio:
            return False, []
        
        # Check for Telegram links
        links_found = []
        for pattern in TELEGRAM_LINK_PATTERNS:
            matches = re.findall(pattern, bio, re.IGNORECASE)
            links_found.extend(matches)
        
        return len(links_found) > 0, links_found
    
    except Exception:
        return False, []


async def handle_bio_violation(client: Client, chat_id: int, user_id: int, user_mention: str, links_found: list):
    """
    Handles bio violations by warning and potentially banning users.
    """
    # Add warning
    warn_count = await add_bio_warn(chat_id, user_id)
    
    # Format links for display
    links_text = "\n".join([f"  • `{link}`" for link in links_found[:3]])  # Show max 3 links
    
    warning_text = (
        f"⚠️ **BIO PROMOTION ALERT**\n\n"
        f"👤 User: {user_mention}\n"
        f"🔗 **Promotion Link(s) Detected:**\n{links_text}\n\n"
        f"⚡ **Action Required:** Remove all promotional links from your bio to chat freely!\n"
        f"📊 **Warning Count:** `{warn_count}/5`\n\n"
    )
    
    if warn_count >= 5:
        # Ban the user
        try:
            await client.ban_chat_member(chat_id, user_id)
            warning_text += f"🚫 **User has been banned** for not removing bio links after 5 warnings!"
            await reset_bio_warns(chat_id, user_id)  # Reset warns after ban
        except Exception as e:
            warning_text += f"❌ Failed to ban user: {e}"
    else:
        warning_text += f"⏰ You have `{5 - warn_count}` warning(s) remaining before ban!"
    
    return warning_text


@app.on_chat_member_updated(filters.group)
@error
async def scan_bio_on_join(client: Client, update: ChatMemberUpdated):
    """
    Scans user bio when they join a group.
    """
    chat_id = update.chat.id
    
    # Check if bio scanner is enabled for this chat
    if not await is_bio_scanner_enabled(chat_id):
        return
    
    # Check if user is joining
    if update.new_chat_member and update.new_chat_member.status not in [
        ChatMemberStatus.LEFT, 
        ChatMemberStatus.BANNED
    ]:
        user = update.new_chat_member.user
        user_id = user.id
        
        # Skip bots
        if user.is_bot:
            return
        
        # Check if user is approved
        if await is_bio_approved(chat_id, user_id):
            return
        
        # Check bio
        has_link, links_found = await check_user_bio(client, user_id, chat_id)
        
        if has_link:
            warning_msg = await handle_bio_violation(
                client, chat_id, user_id, user.mention, links_found
            )
            await client.send_message(chat_id, warning_msg)


@app.on_message(filters.group & filters.text & ~filters.bot)
@error
async def scan_bio_on_message(client: Client, message: Message):
    """
    Periodically scans user bio when they send messages (to catch bio updates).
    """
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id
    
    # Check if bio scanner is enabled
    if not await is_bio_scanner_enabled(chat_id):
        return
    
    # Check if user is approved
    if await is_bio_approved(chat_id, user_id):
        return
    
    # Check bio (do this randomly to avoid excessive API calls)
    import random
    if random.randint(1, 20) == 1:  # 5% chance per message
        has_link, links_found = await check_user_bio(client, user_id, chat_id)
        
        if has_link:
            warning_msg = await handle_bio_violation(
                client, chat_id, user_id, user.mention, links_found
            )
            await message.reply_text(warning_msg)


@app.on_message(filters.command("free", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
@error
async def approve_user_bio(client: Client, message: Message):
    """
    Allows admins to approve users to keep links in bio.
    """
    # Check if user is admin
    user_member = await message.chat.get_member(message.from_user.id)
    if user_member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
        await message.reply_text("❌ Only admins can use this command!")
        return
    
    # Get target user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        target = message.command[1]
        try:
            if target.isdigit():
                target_user = await client.get_users(int(target))
            else:
                target_user = await client.get_users(target)
        except Exception:
            await message.reply_text("❌ User not found!")
            return
    else:
        await message.reply_text("❌ Reply to a user or provide username/ID!")
        return
    
    chat_id = message.chat.id
    user_id = target_user.id
    
    # Approve user and reset warnings
    await approve_bio(chat_id, user_id)
    await reset_bio_warns(chat_id, user_id)
    
    await message.reply_text(
        f"✅ {target_user.mention} is now **approved** to keep links in their bio!\n"
        f"📊 All warnings have been cleared."
    )


@app.on_message(filters.command("unfree", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
@error
async def unapprove_user_bio(client: Client, message: Message):
    """
    Removes bio approval from a user.
    """
    # Check if user is admin
    user_member = await message.chat.get_member(message.from_user.id)
    if user_member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
        await message.reply_text("❌ Only admins can use this command!")
        return
    
    # Get target user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        target = message.command[1]
        try:
            if target.isdigit():
                target_user = await client.get_users(int(target))
            else:
                target_user = await client.get_users(target)
        except Exception:
            await message.reply_text("❌ User not found!")
            return
    else:
        await message.reply_text("❌ Reply to a user or provide username/ID!")
        return
    
    await unapprove_bio(message.chat.id, target_user.id)
    await message.reply_text(f"❌ {target_user.mention} bio approval has been **removed**!")


@app.on_message(filters.command("bioscanner", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
@error
async def toggle_bio_scanner(client: Client, message: Message):
    """
    Enables or disables bio scanner for the group.
    """
    try:
        # Check if user is admin
        user_member = await message.chat.get_member(message.from_user.id)
        if user_member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            await message.reply_text("❌ Only admins can use this command!")
            return
    except Exception as e:
        await message.reply_text(f"❌ Error checking admin status: {e}")
        return
    
    chat_id = message.chat.id
    
    if len(message.command) > 1:
        action = message.command[1].lower()
        if action == "on":
            await enable_bio_scanner(chat_id)
            await message.reply_text("✅ Bio Scanner has been **enabled** for this group!")
        elif action == "off":
            await disable_bio_scanner(chat_id)
            await message.reply_text("❌ Bio Scanner has been **disabled** for this group!")
        else:
            await message.reply_text("❌ Use: `/bioscanner on` or `/bioscanner off`")
    else:
        is_enabled = await is_bio_scanner_enabled(chat_id)
        status = "**Enabled** ✅" if is_enabled else "**Disabled** ❌"
        await message.reply_text(
            f"📊 **Bio Scanner Status:** {status}\n\n"
            f"Use `/bioscanner on` or `/bioscanner off` to toggle."
        )


@app.on_message(filters.command("biowarns", prefixes=config.config.COMMAND_PREFIXES) & filters.group)
@error
async def check_bio_warns(client: Client, message: Message):
    """
    Check bio warning count for a user.
    """
    # Get target user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif len(message.command) > 1:
        target = message.command[1]
        try:
            if target.isdigit():
                target_user = await client.get_users(int(target))
            else:
                target_user = await client.get_users(target)
        except Exception:
            await message.reply_text("❌ User not found!")
            return
    else:
        target_user = message.from_user
    
    warn_count = await get_bio_warns(message.chat.id, target_user.id)
    
    await message.reply_text(
        f"📊 **Bio Warning Status**\n\n"
        f"👤 User: {target_user.mention}\n"
        f"⚠️ Warnings: `{warn_count}/5`"
    )


__module__ = "Bio Scanner"
__help__ = """
**Bio Scanner Module**

Automatically detects and warns users who have promotional Telegram links in their bio.

**Admin Commands:**
  ✧ `/bioscanner on/off`: Enable or disable bio scanning for the group.
  ✧ `/free [user/reply]`: Approve a user to keep links in their bio without warnings.
  ✧ `/unfree [user/reply]`: Remove bio approval from a user.

**User Commands:**
  ✧ `/biowarns [user/reply]`: Check bio warning count for yourself or another user.

**How it works:**
• When users join or send messages, bot checks their bio for t.me links
• Users get warned and their count increases (max 5 warnings)
• After 5 warnings, user gets automatically banned
• Admins can approve users with `/free` to exempt them from bio scanning

**Detected Link Patterns:**
• t.me/username
• https://t.me/username
• telegram.me/username
"""
