from pyrogram import Client, filters
from pyrogram.types import (
    InlineQueryResultArticle, InputTextMessageContent,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from Yumeko import app
from config import config
from Yumeko.decorator.errors import error

# --- MEMORY DATABASE ---
# Note: Whispers are stored in RAM. They will disappear if you restart the bot.
whisper_db = {}

# Button to switch to inline mode quickly
switch_btn = InlineKeyboardMarkup([[InlineKeyboardButton("💒 Start Whisper", switch_inline_query_current_chat="")]])

async def _whisper(client, inline_query):
    data = inline_query.query
    results = []
    
    # If the user hasn't typed enough arguments (needs username + text)
    if len(data.split()) < 2:
        mm = [
            InlineQueryResultArticle(
                title="💒 Whisper Mode",
                description=f"@{config.BOT_USERNAME} [USERNAME] [TEXT]",
                input_message_content=InputTextMessageContent(f"**💒 Whisper Usage:**\n\n@{config.BOT_USERNAME} (Target Username) (Message)"),
                thumb_url="https://telegra.ph/file/4287c313c71ab800e29d0.jpg",
                reply_markup=switch_btn
            )
        ]
    else:
        try:
            # Logic: Split the input into Target and Message
            first_arg = data.split()[0]
            msg = data.split(None, 1)[1]
            
            # Try to find the user they are tagging
            try:
                user = await client.get_users(first_arg)
                target_id = user.id
                target_name = user.first_name
            except Exception:
                return [
                    InlineQueryResultArticle(
                        title="❌ Invalid User",
                        description="I can't find that user! Make sure I know them.",
                        input_message_content=InputTextMessageContent("❌ Invalid username or ID!"),
                        reply_markup=switch_btn
                    )
                ]
            
            # Create a unique key for this whisper (FromUser_ToUser)
            whisper_key = f"{inline_query.from_user.id}_{target_id}"
            
            # Save the message to our memory
            whisper_db[whisper_key] = msg
            
            # Create Buttons
            whisper_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("💒 Read Whisper", callback_data=f"fdaywhisper_{inline_query.from_user.id}_{target_id}")]
            ])
            
            one_time_btn = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔥 One-Time Whisper", callback_data=f"fdaywhisper_{inline_query.from_user.id}_{target_id}_one")]
            ])
            
            mm = [
                # Option 1: Normal Whisper
                InlineQueryResultArticle(
                    title="💒 Send Whisper",
                    description=f"Secret message to {target_name}",
                    input_message_content=InputTextMessageContent(f"🔒 **A Whisper has been sent to {target_name}.**\n\nOnly they can open it!"),
                    thumb_url="https://telegra.ph/file/4287c313c71ab800e29d0.jpg",
                    reply_markup=whisper_btn
                ),
                # Option 2: One-Time Whisper (Deletes after reading)
                InlineQueryResultArticle(
                    title="🔥 One-Time Whisper",
                    description=f"Burn after reading message to {target_name}",
                    input_message_content=InputTextMessageContent(f"🔥 **One-Time Whisper sent to {target_name}.**\n\nIt will disappear after reading!"),
                    thumb_url="https://telegra.ph/file/ff4455f02730649f7a98f.jpg",
                    reply_markup=one_time_btn
                )
            ]
        except IndexError:
            pass
            
    if 'mm' in locals():
        results = mm
    
    return results

# --- CALLBACK HANDLER (When button is clicked) ---
@app.on_callback_query(filters.regex(pattern=r"fdaywhisper_(.*)"))
@error
async def whispes_cb(client, query):
    data = query.data.split("_")
    from_user = int(data[1])
    to_user = int(data[2])
    user_id = query.from_user.id
    
    # Permission Check: Only Sender, Receiver, or Owner can open
    if user_id not in [from_user, to_user, config.OWNER_ID]:
        await query.answer("🚧 This whisper is not for you!", show_alert=True)
        return
    
    search_msg = f"{from_user}_{to_user}"
    
    try:
        msg = whisper_db[search_msg]
    except KeyError:
        msg = "🚫 Error!\n\nThis whisper has expired or was deleted."
    
    SWITCH = InlineKeyboardMarkup([[InlineKeyboardButton("Send a Whisper 🤫", switch_inline_query_current_chat="")]])
    
    await query.answer(msg, show_alert=True)
    
    # If it is a "One-Time" whisper, delete it after showing
    if len(data) > 3 and data[3] == "one":
        if user_id == to_user:
            if search_msg in whisper_db:
                del whisper_db[search_msg]
            await query.edit_message_text("📬 Whisper has been read and destroyed!", reply_markup=SWITCH)

# --- INLINE QUERY HANDLER ---
@app.on_inline_query()
async def bot_inline(client, inline_query):
    string = inline_query.query.lower()
    
    if string.strip() == "":
        # Show Help Menu if nothing is typed
        answers = [
            InlineQueryResultArticle(
                title="💒 Whisper Help",
                description=f"@MariaModBot @username Message",
                input_message_content=InputTextMessageContent(
                    f"**📍 Whisper Usage:**\n\n`@{client.me.username} @username Your Message`\n\nExample:\n`@{client.me.username} @Dushmanxroninn Secret Message`"
                ),
                thumb_url="https://telegra.ph/file/4287c313c71ab800e29d0.jpg",
                reply_markup=switch_btn
            )
        ]
        await inline_query.answer(answers)
    else:
        # Process the whisper
        answers = await _whisper(client, inline_query)
        await inline_query.answer(answers, cache_time=0)

# --- MODULE INFO ---
__module__ = "Whisper"
__help__ = """
**🤫 Inline Whisper**

Securely send hidden messages in groups!

**How to use:**
1. Type `@MariaModBot @username Message` in the chat.
2. Wait for the popup menu.
3. Click the result to send.
4. Only the person you tagged can read it!
"""
