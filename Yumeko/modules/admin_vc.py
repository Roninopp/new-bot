from pyrogram import filters, Client
from pyrogram.types import Message

# ---------------------------------------------------------------------------------
# IMPORTANT: Adjust these imports to match your actual file structure
# You need to import:
# 1. 'app' -> Your Bot Client
# 2. 'call_py' -> Your PyTgCalls Client (the one running the music)
# 3. 'SUDOERS' -> Your list of admin IDs
# ---------------------------------------------------------------------------------
from MusicBot import app, call_py  # <--- CHANGE 'MusicBot' to your main file name
from config import SUDOERS         # <--- CHANGE to where your config is
# ---------------------------------------------------------------------------------

@app.on_message(filters.command("active_vc") & filters.user(SUDOERS))
async def active_vc_list(client: Client, message: Message):
    """
    Shows a list of all groups where the bot is currently playing music.
    """
    msg = await message.reply_text("🔄 **Scanning active voice chats...**")
    
    try:
        # Get the list of active calls from PyTgCalls
        active_calls = call_py.active_calls
        
        if not active_calls:
            await msg.edit_text("❌ **No active voice chats found.**\nThe bot is not playing anywhere.")
            return

        text = f"**🔊 Active Voice Chats ({len(active_calls)})**\n\n"
        
        count = 0
        for call in active_calls:
            try:
                # Get the Chat ID from the call object
                chat_id = call.chat_id
                
                # Attempt to get the Chat Title for better display
                try:
                    chat_info = await client.get_chat(chat_id)
                    chat_title = chat_info.title
                    username = f"@{chat_info.username}" if chat_info.username else "Private"
                except Exception:
                    chat_title = "Unknown Group"
                    username = "Private"

                count += 1
                text += f"**{count}. {chat_title}**\n   ID: `{chat_id}` | {username}\n"
                
            except Exception as e:
                # If a specific chat fails, skip it but continue the loop
                continue

        # Split text if it's too long (Telegram limit is 4096 chars)
        if len(text) > 4000:
            await msg.edit_text(
                f"**🔊 Active Voice Chats ({len(active_calls)})**\n\n"
                f"Total active chats: {len(active_calls)}\n"
                f"(List too long to display fully)"
            )
        else:
            await msg.edit_text(text)

    except Exception as e:
        await msg.edit_text(f"❌ **Error fetching active calls:**\n`{e}`")
