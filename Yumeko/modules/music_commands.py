"""
Music Player Module - Enhanced Commands & Events (Professional Edition)
Features: Professional UI, Fixed thumbnails, Fixed userbot joining for all group types
"""

import asyncio
import os
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserAlreadyParticipant, ChatAdminRequired, UserNotParticipant, InviteRequestSent
from pytgcalls.types import MediaStream, AudioQuality

# Import Core Logic
from Yumeko.modules.music import (
    download_audio,
    search_youtube,
    is_youtube_url,
    add_to_queue,
    get_queue,
    get_next_song,
    clear_queue,
    current_playing
)

# Import Clients
from Yumeko.modules.music_v2 import userbot, pytgcalls

from Yumeko import app
from config import config
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error

# ==========================================
# 🤖 ENHANCED USERBOT JOIN HANDLER
# ==========================================
async def ensure_userbot_in_chat(chat_id: int, retries: int = 3):
    """
    Enhanced userbot join logic that works with ALL group types.
    Handles: Public groups, Private groups, Supergroups, Channels
    """
    try:
        # Check if userbot is already in the chat
        try:
            await userbot.get_chat_member(chat_id, "me")
            return True  # Already in chat
        except UserNotParticipant:
            pass  # Not in chat, need to join
        except Exception as e:
            # Chat might not exist in userbot's session
            pass
        
        # Try to join the chat
        for attempt in range(retries):
            try:
                # Method 1: Get chat info from bot first
                chat = await app.get_chat(chat_id)
                
                if chat.username:
                    # Public group/channel - join via username
                    await userbot.join_chat(chat.username)
                    await asyncio.sleep(1)
                    return True
                else:
                    # Private group/supergroup - need invite link
                    try:
                        # Get invite link from bot
                        invite_link = await app.export_chat_invite_link(chat_id)
                        
                        # Join via invite link
                        await userbot.join_chat(invite_link)
                        await asyncio.sleep(1)
                        return True
                        
                    except ChatAdminRequired:
                        # Bot doesn't have permission to create invite link
                        # Ask an admin to add the userbot manually
                        raise Exception(
                            "❌ Bot needs 'Invite Users' permission to add the assistant.\n"
                            "Please give the bot admin rights or add the assistant manually."
                        )
                    except InviteRequestSent:
                        # Join request sent (approval needed)
                        raise Exception(
                            "⏳ Join request sent to group admins.\n"
                            "Please approve the assistant's request to join."
                        )
                        
            except UserAlreadyParticipant:
                return True  # Already joined
                
            except Exception as e:
                if attempt == retries - 1:
                    # Last attempt failed
                    error_msg = str(e)
                    if "FLOOD_WAIT" in error_msg:
                        raise Exception("⏳ Too many requests. Please try again in a few minutes.")
                    elif "INVITE_REQUEST_SENT" in error_msg:
                        raise Exception("⏳ Join request sent. Please approve the assistant.")
                    elif "CHANNELS_TOO_MUCH" in error_msg:
                        raise Exception("❌ Assistant has joined too many groups. Please try again later.")
                    else:
                        raise Exception(f"❌ Failed to add assistant: {error_msg}")
                
                await asyncio.sleep(2)  # Wait before retry
        
        return False
        
    except Exception as e:
        raise e

# ==========================================
# 🤖 AUTO-PLAY & TIMER ENGINE
# ==========================================
async def auto_end_handler(chat_id, duration):
    """
    Waits for the song duration + 2 seconds, then plays next.
    """
    if duration > 0:
        await asyncio.sleep(duration + 2)
    else:
        return

    if chat_id in current_playing:
        await play_next_song(chat_id)

async def play_next_song(chat_id):
    """Handles playing the next song or leaving"""
    next_song = get_next_song(chat_id)
    
    if next_song:
        try:
            await pytgcalls.play(
                chat_id,
                MediaStream(
                    next_song['file_path'],
                    audio_parameters=AudioQuality.HIGH
                )
            )
            current_playing[chat_id] = next_song
            await send_now_playing(chat_id, next_song)
            
            asyncio.create_task(auto_end_handler(chat_id, next_song['duration']))
            
        except Exception as e:
            print(f"Error playing next: {e}")
            await pytgcalls.leave_call(chat_id)
    else:
        if chat_id in current_playing:
            del current_playing[chat_id]
            
        await app.send_message(
            chat_id, 
            "```\n╔════════════════════╗\n"
            "║  Queue Finished ✨  ║\n"
            "╚════════════════════╝\n```\n"
            "**Leaving voice chat...**"
        )
        await asyncio.sleep(3)
        try:
            await pytgcalls.leave_call(chat_id)
        except:
            pass

# ==========================================
# 🎵 ENHANCED PLAY COMMAND
# ==========================================
@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply(
            "```\n╔═══════════════════╗\n"
            "║   Music Player 🎵  ║\n"
            "╚═══════════════════╝\n```\n"
            "**Usage:** `/play <song name or URL>`\n"
            "**Example:** `/play Believer Imagine Dragons`"
        )
        return

    query = message.text.split(maxsplit=1)[1].strip()
    
    # Professional searching message
    status = await message.reply(
        "```\n╔════════════════════╗\n"
        "║   🔍 Searching...   ║\n"
        "╚════════════════════╝\n```"
    )

    try:
        # 1. Search for the song
        url = await search_youtube(query)
        if not url:
            await status.edit(
                "```\n╔════════════════════╗\n"
                "║   ❌ Not Found      ║\n"
                "╚════════════════════╝\n```\n"
                "**Could not find the requested song.**"
            )
            return

        # 2. Update to downloading status
        await status.edit(
            "```\n╔════════════════════╗\n"
            "║  📥 Downloading...  ║\n"
            "╚════════════════════╝\n```"
        )

        # 3. Download audio
        info = await download_audio(url)

        # 4. Check if already playing
        if message.chat.id in current_playing:
            # Add to queue
            add_to_queue(message.chat.id, info)
            queue = get_queue(message.chat.id)
            position = len(queue)
            
            duration_str = f"{info['duration'] // 60}:{info['duration'] % 60:02d}" if info['duration'] > 0 else "Live"
            
            await status.edit(
                f"```\n╔════════════════════╗\n"
                f"║  ✅ Added to Queue  ║\n"
                f"╚════════════════════╝\n```\n"
                f"**🎵 Title:** `{info['title'][:50]}{'...' if len(info['title']) > 50 else ''}`\n"
                f"**📍 Position:** `#{position}`\n"
                f"**⏱️ Duration:** `{duration_str}`"
            )
            return

        # 5. Ensure userbot is in chat
        await status.edit(
            "```\n╔════════════════════╗\n"
            "║ 🤖 Joining VC...   ║\n"
            "╚════════════════════╝\n```"
        )
        
        await ensure_userbot_in_chat(message.chat.id)
        
        # 6. Play the song
        await pytgcalls.play(
            message.chat.id,
            MediaStream(
                info['file_path'],
                audio_parameters=AudioQuality.HIGH
            )
        )
        
        current_playing[message.chat.id] = info
        await send_now_playing(message.chat.id, info)
        
        # Start auto-play timer
        asyncio.create_task(auto_end_handler(message.chat.id, info['duration']))
        
        await status.delete()

    except Exception as e:
        error_msg = str(e)
        await status.edit(
            f"```\n╔════════════════════╗\n"
            f"║   ❌ Error Occurred ║\n"
            f"╚════════════════════╝\n```\n"
            f"**Details:** `{error_msg[:100]}`"
        )

# ==========================================
# 🎵 TEXT COMMANDS
# ==========================================

@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
async def stop_cmd(_, message):
    chat_id = message.chat.id
    if chat_id not in current_playing:
        await message.reply("```\n❌ Nothing is playing.\n```")
        return
    
    clear_queue(chat_id)
    if chat_id in current_playing:
        del current_playing[chat_id]
        
    await pytgcalls.leave_call(chat_id)
    await message.reply(
        "```\n╔════════════════════╗\n"
        "║   ⏹️ Stopped        ║\n"
        "╚════════════════════╝\n```"
    )

@app.on_message(filters.command("skip", config.COMMAND_PREFIXES) & filters.group)
async def skip_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("```\n❌ Nothing to skip.\n```")
        return
        
    await message.reply(
        "```\n╔════════════════════╗\n"
        "║   ⏭️ Skipping...    ║\n"
        "╚════════════════════╝\n```"
    )
    await play_next_song(message.chat.id)

@app.on_message(filters.command("pause", config.COMMAND_PREFIXES) & filters.group)
async def pause_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("```\n❌ Nothing playing.\n```")
        return
    try:
        await pytgcalls.pause_stream(message.chat.id)
        await message.reply("```\n⏸️ Paused.\n```")
    except:
        await message.reply("```\n❌ Failed to pause.\n```")

@app.on_message(filters.command("resume", config.COMMAND_PREFIXES) & filters.group)
async def resume_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("```\n❌ Nothing playing.\n```")
        return
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("```\n▶️ Resumed.\n```")
    except:
        await message.reply("```\n❌ Failed to resume.\n```")

@app.on_message(filters.command("queue", config.COMMAND_PREFIXES) & filters.group)
async def queue_cmd(_, message):
    queue = get_queue(message.chat.id)
    
    text = "```\n╔════════════════════╗\n"
    text += "║   🎵 Music Queue   ║\n"
    text += "╚════════════════════╝\n```\n\n"
    
    if message.chat.id in current_playing:
        curr = current_playing[message.chat.id]
        text += f"**▶️ Now Playing:**\n`{curr['title'][:45]}{'...' if len(curr['title']) > 45 else ''}`\n\n"
    
    if not queue:
        text += "**📭 Queue is empty!**"
    else:
        text += "**📝 Up Next:**\n"
        for i, song in enumerate(queue[:10], 1):
            text += f"`{i}.` {song['title'][:40]}{'...' if len(song['title']) > 40 else ''}\n"
        
        if len(queue) > 10:
            text += f"\n*...and {len(queue)-10} more songs*"
        
    await message.reply(text)

# ==========================================
# 🎛️ BUTTON CALLBACKS
# ==========================================
@app.on_callback_query(filters.regex(r"^(stop|skip|pause|resume|close)"))
async def cb_handler(_, query):
    action = query.data.split("_")[0]
    chat_id = query.message.chat.id
    
    if action == "close":
        await query.message.delete()
        return

    if action == "stop":
        clear_queue(chat_id)
        if chat_id in current_playing: 
            del current_playing[chat_id]
        await pytgcalls.leave_call(chat_id)
        await query.message.delete()
        await query.answer("⏹️ Stopped", show_alert=False)
        
    elif action == "skip":
        await query.answer("⏭️ Skipped", show_alert=False)
        await play_next_song(chat_id)
        
    elif action == "pause":
        await pytgcalls.pause_stream(chat_id)
        await query.answer("⏸️ Paused", show_alert=False)
        
    elif action == "resume":
        await pytgcalls.resume_stream(chat_id)
        await query.answer("▶️ Resumed", show_alert=False)

# ==========================================
# 🎨 ENHANCED NOW PLAYING UI
# ==========================================
async def send_now_playing(chat_id, info):
    """Enhanced now playing message with better formatting and thumbnail."""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸", callback_data="pause"),
            InlineKeyboardButton("▶️", callback_data="resume"),
            InlineKeyboardButton("⏭", callback_data="skip"),
            InlineKeyboardButton("⏹", callback_data="stop")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])
    
    duration_str = f"{info['duration'] // 60}:{info['duration'] % 60:02d}" if info['duration'] > 0 else "🔴 Live Stream"
    
    # Format views count
    views = info.get('views', 0)
    if views >= 1_000_000:
        views_str = f"{views / 1_000_000:.1f}M"
    elif views >= 1_000:
        views_str = f"{views / 1_000:.1f}K"
    else:
        views_str = str(views)
    
    text = (
        f"```\n╔════════════════════════════╗\n"
        f"║      🎵 NOW PLAYING 🎵      ║\n"
        f"╚════════════════════════════╝\n```\n\n"
        f"**🎼 Title:**\n`{info['title']}`\n\n"
        f"**👤 Uploader:** `{info.get('uploader', 'Unknown')}`\n"
        f"**⏱️ Duration:** `{duration_str}`\n"
        f"**👁️ Views:** `{views_str}`\n\n"
        f"**🎧 Powered by:** `Samurai Network`"
    )
    
    try:
        # Try to send with thumbnail
        if info.get('thumbnail'):
            await app.send_photo(
                chat_id, 
                info['thumbnail'], 
                caption=text, 
                reply_markup=buttons
            )
        else:
            # Fallback to text only
            await app.send_message(chat_id, text, reply_markup=buttons)
    except Exception as e:
        # If thumbnail fails, send text only
        try:
            await app.send_message(chat_id, text, reply_markup=buttons)
        except:
            pass

# ==========================================
# ℹ️ MODULE INFO
# ==========================================
__module__ = "Music"
__help__ = """
```
╔═══════════════════════╗
║   🎵 Music Player 🎵   ║
╚═══════════════════════╝
```

**Commands:**
• `/play <song>` - Play or queue a song
• `/skip` - Skip current song
• `/stop` - Stop & clear queue
• `/pause` - Pause playback
• `/resume` - Resume playback
• `/queue` - View current queue

**Features:**
✨ High-quality audio streaming
🎨 Professional UI design
🤖 Auto-queue management
📱 Interactive controls

*Powered by XBitCode API*
"""
