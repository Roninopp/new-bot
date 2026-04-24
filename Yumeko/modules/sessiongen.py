import asyncio
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.errors import (
    PhoneCodeExpired, PhoneCodeInvalid, PasswordHashInvalid,
    SessionPasswordNeeded, PhoneNumberInvalid, FloodWait
)
from Yumeko import app
import config

# Optional Telethon support
try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession as TelethonStringSession
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

__module__ = "Session Generator"
__help__ = """
**🔐 Session Generator Module**

Generate Pyrogram / Telethon string sessions safely inside a private chat.

**Commands:**
• `/gensession` – Start the interactive session generator.

**How it works:**
1. Use the command **in private chat** with the bot.
2. Choose Pyrogram or Telethon.
3. Provide your API ID, API Hash, and phone number.
4. Enter the verification code (and 2FA password if enabled).
5. The bot will send you the session string **only once** via direct message.

⚠️ **Never share your session string!**
🗑️ Sensitive data is not stored; you should delete the chat after use.
"""

# -------------------- Core generation functions --------------------

async def generate_pyrogram_session(api_id: int, api_hash: str, phone: str,
                                    code_callback, password_callback) -> str:
    """Create a temporary in‑memory Pyrogram client and return the session string."""
    from pyrogram import Client
    client = Client(
        name=":memory:",
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone,
        in_memory=True,
    )
    await client.connect()
    try:
        sent_code = await client.send_code(phone)
        code = await code_callback(sent_code.phone_code_hash)
        await client.sign_in(phone, sent_code.phone_code_hash, code)
    except SessionPasswordNeeded:
        password = await password_callback()
        await client.check_password(password)
    except Exception:
        await client.disconnect()
        raise

    string = await client.export_session_string()
    await client.disconnect()
    return string

async def generate_telethon_session(api_id: int, api_hash: str, phone: str,
                                    code_callback, password_callback) -> str:
    """Create a temporary Telethon client and return the session string."""
    if not TELETHON_AVAILABLE:
        raise Exception("Telethon is not installed on the server.")
    client = TelegramClient(TelethonStringSession(), api_id, api_hash)
    await client.connect()
    try:
        sent_code = await client.send_code_request(phone)
        code = await code_callback(sent_code.phone_code_hash)
        await client.sign_in(phone, code, phone_code_hash=sent_code.phone_code_hash)
    except SessionPasswordNeeded:
        password = await password_callback()
        await client.sign_in(password=password)
    except Exception:
        await client.disconnect()
        raise

    string = client.session.save()
    await client.disconnect()
    return string


# -------------------- Main interactive handler --------------------

@app.on_message(
    filters.command("gensession", prefixes=config.config.COMMAND_PREFIXES)
    & filters.private      # 🛡️ Only private chats – keeps sensitive data safe
)
async def gensession_start(client, message: Message):
    """Start the session generation wizard."""
    user = message.from_user

    # Step 1: choose library
    await message.reply(
        "**🔐 Session Generator**\n\n"
        "Which library do you want to generate a session for?\n"
        "Reply with: `pyrogram` or `telethon`\n\n"
        "⚠️ After the process, **delete this entire conversation manually** for security.",
        quote=True
    )

    try:
        lib_msg = await client.ask(
            message.chat.id,
            text=">> Waiting for your choice...",
            filters=filters.text,
            timeout=120
        )
        lib_choice = lib_msg.text.lower().strip()
        if lib_choice not in ("pyrogram", "telethon"):
            await lib_msg.reply("❌ Invalid choice. Use /gensession to restart.")
            return
        # Bot's own message – can be deleted
        await lib_msg.delete()
    except asyncio.TimeoutError:
        await message.reply("⏰ Timeout. Start again with /gensession.")
        return

    # Step 2: API ID
    await message.reply("Please send your **API ID** (integer). Get it from my.telegram.org", quote=True)
    try:
        api_msg = await client.ask(
            message.chat.id,
            text=">> Waiting for API ID...",
            filters=filters.text,
            timeout=120
        )
        api_id = int(api_msg.text.strip())
        await api_msg.delete()
    except (ValueError, asyncio.TimeoutError):
        await message.reply("❌ Invalid API ID. Restart with /gensession.")
        return

    # Step 3: API Hash
    await message.reply("Now send your **API Hash** (string).", quote=True)
    try:
        hash_msg = await client.ask(
            message.chat.id,
            text=">> Waiting for API Hash...",
            filters=filters.text,
            timeout=120
        )
        api_hash = hash_msg.text.strip()
        await hash_msg.delete()
    except asyncio.TimeoutError:
        await message.reply("⏰ Timeout. /gensession again.")
        return

    # Step 4: Phone number
    await message.reply(
        "Send your **phone number** in international format (e.g., +1234567890)",
        quote=True
    )
    try:
        phone_msg = await client.ask(
            message.chat.id,
            text=">> Waiting for phone number...",
            filters=filters.text,
            timeout=120
        )
        phone = phone_msg.text.strip()
        await phone_msg.delete()
    except asyncio.TimeoutError:
        await message.reply("⏰ Timeout. /gensession again.")
        return

    # Helper callbacks for code and password
    async def code_callback(phone_code_hash=None):
        await message.reply(
            "Enter the **verification code** sent to your Telegram app.",
            quote=True
        )
        code_msg = await client.ask(
            message.chat.id,
            text=">> Waiting for code...",
            filters=filters.text,
            timeout=300
        )
        code = code_msg.text.strip()
        await code_msg.delete()
        return code

    async def password_callback():
        await message.reply(
            "Enter your **two‑step verification password** (Cloud Password):",
            quote=True
        )
        pass_msg = await client.ask(
            message.chat.id,
            text=">> Waiting for password...",
            filters=filters.text,
            timeout=300
        )
        password = pass_msg.text.strip()
        await pass_msg.delete()
        return password

    # Step 5: Generate
    status = await message.reply("🔄 Generating your session string...")
    try:
        if lib_choice == "pyrogram":
            session_str = await generate_pyrogram_session(
                api_id, api_hash, phone, code_callback, password_callback
            )
        else:
            session_str = await generate_telethon_session(
                api_id, api_hash, phone, code_callback, password_callback
            )
    except PhoneCodeExpired:
        await status.edit_text("❌ Verification code expired. Run /gensession again.")
        return
    except PhoneCodeInvalid:
        await status.edit_text("❌ Invalid verification code. Run /gensession again.")
        return
    except PasswordHashInvalid:
        await status.edit_text("❌ Wrong 2FA password. Run /gensession again.")
        return
    except PhoneNumberInvalid:
        await status.edit_text("❌ Invalid phone number. Run /gensession again.")
        return
    except FloodWait as e:
        await status.edit_text(f"⏳ Flood wait: {e.x:.0f} seconds. Please wait before retrying.")
        return
    except Exception as e:
        await status.edit_text(f"❌ Unexpected error: {e}")
        return

    # Step 6: Send the session string – only to the user, and delete the status message
    await status.delete()
    try:
        await client.send_message(
            user.id,
            f"✅ **{lib_choice.upper()} Session String**\n\n"
            f"`{session_str}`\n\n"
            "⚠️ **Do not share this with anyone!**\n"
            "Store it safely and immediately delete this chat for your security."
        )
        # Acknowledge in the original chat
        await message.reply(
            "✅ Session generated and sent to your **Saved Messages / private chat**.\n"
            "Please delete this conversation now for your safety."
        )
    except Exception:
        # Fallback if DM fails (should not happen in private, but just in case)
        await message.reply(
            f"✅ Session generated, but I couldn't DM you.\n"
            f"**Save this immediately (it won't be shown again):**\n"
            f"`{session_str}`",
            quote=True
        )
