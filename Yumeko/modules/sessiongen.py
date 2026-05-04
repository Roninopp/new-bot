import asyncio
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
    from telethon.errors import SessionPasswordNeededError as TelethonSessionPasswordNeeded
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False

__module__ = "Session Generator"
__help__ = """
**🔐 Session Generator Module**

Generate Pyrogram / Telethon string sessions safely inside a private chat.

**Commands:**
• `/gensession` – Start the interactive session generator.
"""

# Global state dictionary to manage async callback button interactions
GEN_STATE = {}

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
    except TelethonSessionPasswordNeeded: # Fixed: Using the Telethon-specific exception
        password = await password_callback()
        await client.sign_in(password=password)
    except Exception:
        await client.disconnect()
        raise

    string = client.session.save()
    await client.disconnect()
    return string


# -------------------- Interactive Handlers --------------------

@app.on_callback_query(filters.regex(r"^sg_"))
async def session_gen_callbacks(client: Client, query: CallbackQuery):
    """Handles the inline button presses for library choice and OTP entry."""
    user_id = query.from_user.id
    data = query.data

    if user_id not in GEN_STATE:
        await query.answer("This session process has expired. Please run /gensession again.", show_alert=True)
        return

    state = GEN_STATE[user_id]

    # Library Selection
    if state.get('step') == 'lib_choice':
        if data == "sg_lib_pyrogram":
            state['future'].set_result("pyrogram")
        elif data == "sg_lib_telethon":
            state['future'].set_result("telethon")
        await query.message.delete()

    # OTP Input Keypad
    elif state.get('step') == 'otp':
        action = data.split("_")[2]
        
        if action == "submit":
            if len(state['code']) < 1:
                await query.answer("Please enter the code first!", show_alert=True)
                return
            state['future'].set_result(state['code'])
            await query.message.delete()
            
        elif action == "clear":
            state['code'] = ""
            await query.message.edit_text(
                "📲 **Enter the verification code** sent to your Telegram app.\n\n"
                "Use the buttons below to safely enter the OTP:\n"
                f"**Code:** ` `",
                reply_markup=query.message.reply_markup
            )
            await query.answer("Cleared!")
            
        else:
            # Append number to code
            state['code'] += action
            display_code = "*" * len(state['code'])
            await query.message.edit_text(
                "📲 **Enter the verification code** sent to your Telegram app.\n\n"
                "Use the buttons below to safely enter the OTP:\n"
                f"**Code:** `{display_code}`",
                reply_markup=query.message.reply_markup
            )
            await query.answer()

@app.on_message(
    filters.command("gensession", prefixes=config.config.COMMAND_PREFIXES)
    & filters.private
)
async def gensession_start(client: Client, message: Message):
    """Start the session generation wizard."""
    user = message.from_user
    loop = asyncio.get_event_loop()

    # --- Step 1: Choose Library (Using Inline Buttons) ---
    lib_future = loop.create_future()
    GEN_STATE[user.id] = {'step': 'lib_choice', 'future': lib_future}

    lib_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Pyrogram", callback_data="sg_lib_pyrogram"),
            InlineKeyboardButton("Telethon", callback_data="sg_lib_telethon")
        ]
    ])

    lib_msg = await message.reply(
        "**🔐 Session Generator**\n\n"
        "Which library do you want to generate a session for?\n"
        "Click a button below:\n\n"
        "⚠️ After the process, **delete this entire conversation manually** for security.",
        reply_markup=lib_keyboard,
        quote=True
    )

    try:
        lib_choice = await asyncio.wait_for(lib_future, timeout=120)
    except asyncio.TimeoutError:
        GEN_STATE.pop(user.id, None)
        await lib_msg.edit_text("⏰ Timeout. Start again with /gensession.")
        return

    # --- Step 2: API ID ---
    await message.reply("Please send your **API ID** (integer). Get it from my.telegram.org")
    try:
        api_msg = await client.ask(message.chat.id, text=">> Waiting for API ID...", filters=filters.text, timeout=120)
        api_id = int(api_msg.text.strip())
        await api_msg.delete()
    except (ValueError, asyncio.TimeoutError):
        await message.reply("❌ Invalid API ID or Timeout. Restart with /gensession.")
        return

    # --- Step 3: API Hash ---
    await message.reply("Now send your **API Hash** (string).")
    try:
        hash_msg = await client.ask(message.chat.id, text=">> Waiting for API Hash...", filters=filters.text, timeout=120)
        api_hash = hash_msg.text.strip()
        await hash_msg.delete()
    except asyncio.TimeoutError:
        await message.reply("⏰ Timeout. /gensession again.")
        return

    # --- Step 4: Phone number ---
    await message.reply("Send your **phone number** in international format (e.g., +1234567890)")
    try:
        phone_msg = await client.ask(message.chat.id, text=">> Waiting for phone number...", filters=filters.text, timeout=120)
        phone = phone_msg.text.strip()
        await phone_msg.delete()
    except asyncio.TimeoutError:
        await message.reply("⏰ Timeout. /gensession again.")
        return

    # --- Callbacks ---
    async def code_callback(phone_code_hash=None):
        """Pops up the interactive Inline Keyboard for OTP"""
        otp_future = loop.create_future()
        GEN_STATE[user.id] = {'step': 'otp', 'future': otp_future, 'code': ''}

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("1", callback_data="sg_otp_1"),
                InlineKeyboardButton("2", callback_data="sg_otp_2"),
                InlineKeyboardButton("3", callback_data="sg_otp_3")
            ],
            [
                InlineKeyboardButton("4", callback_data="sg_otp_4"),
                InlineKeyboardButton("5", callback_data="sg_otp_5"),
                InlineKeyboardButton("6", callback_data="sg_otp_6")
            ],
            [
                InlineKeyboardButton("7", callback_data="sg_otp_7"),
                InlineKeyboardButton("8", callback_data="sg_otp_8"),
                InlineKeyboardButton("9", callback_data="sg_otp_9")
            ],
            [
                InlineKeyboardButton("Clear", callback_data="sg_otp_clear"),
                InlineKeyboardButton("0", callback_data="sg_otp_0"),
                InlineKeyboardButton("Submit", callback_data="sg_otp_submit")
            ]
        ])

        await client.send_message(
            user.id,
            "📲 **Enter the verification code** sent to your Telegram app.\n\n"
            "Use the buttons below to safely enter the OTP:\n"
            "**Code:** ` `",
            reply_markup=keyboard
        )

        try:
            code = await asyncio.wait_for(otp_future, timeout=300)
            return code
        except asyncio.TimeoutError:
            GEN_STATE.pop(user.id, None)
            raise Exception("Timeout while waiting for OTP.")

    async def password_callback():
        pass_msg = await client.ask(
            message.chat.id,
            text="🔐 Enter your **two‑step verification password** (Cloud Password):",
            filters=filters.text,
            timeout=300
        )
        password = pass_msg.text.strip()
        await pass_msg.delete()
        return password

    # --- Step 5: Generate ---
    status = await message.reply("🔄 Generating your session string...")
    try:
        if lib_choice == "pyrogram":
            session_str = await generate_pyrogram_session(api_id, api_hash, phone, code_callback, password_callback)
        else:
            session_str = await generate_telethon_session(api_id, api_hash, phone, code_callback, password_callback)
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
        await status.edit_text(f"⏳ Flood wait: {e.value:.0f} seconds. Please wait before retrying.")
        return
    except Exception as e:
        await status.edit_text(f"❌ Unexpected error: {e}")
        return

    # --- Step 6: Send Output ---
    await status.delete()
    try:
        await client.send_message(
            user.id,
            f"✅ **{lib_choice.upper()} Session String**\n\n"
            f"`{session_str}`\n\n"
            "⚠️ **Do not share this with anyone!**\n"
            "Store it safely and immediately delete this chat for your security."
        )
        await message.reply(
            "✅ Session generated and sent to your **Saved Messages / private chat**.\n"
            "Please delete this conversation now for your safety."
        )
    except Exception:
        await message.reply(
            f"✅ Session generated, but I couldn't DM you.\n"
            f"**Save this immediately (it won't be shown again):**\n"
            f"`{session_str}`",
            quote=True
        )
