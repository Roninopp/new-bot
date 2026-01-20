"""
Music Player Module - BULLETPROOF Edition (v9)
Features: Ghost state prevention, VC end detection, robust cleanup
"""

import asyncio
import os
import logging
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserAlreadyParticipant, ChatAdminRequired, UserNotParticipant, InviteRequestSent
from pytgcalls.types import MediaStream, AudioQuality
from pytgcalls import PyTgCalls

# Setup Logger
logger = logging.getLogger(__name__)

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
# 🧹 CLEANUP & STATE MANAGEMENT
# ==========================================
async def force_cleanup(chat_id: int):
    """Force cleanup of all states and leave VC"""
    try:
        # Clear queue
        clear_queue(chat_id)
        
        # Clear current playing
        if chat_id in current_playing:
            del current_playing[chat_id]
        
        # Try to leave call
        try:
            await pytgcalls.leave_call(chat_id)
        except Exception as e:
            # Ignore errors - might not be in call
            logger.debug(f"Leave call error (expected): {e}")
            pass
        
        logger.info(f"[CLEANUP] Chat {chat_id} cleaned up successfully")
        return True
    except Exception as e:
        logger.error(f"[CLEANUP] Error: {e}")
        return False

async def validate_vc_state(chat_id: int) -> bool:
    """Check if bot is actually in VC and playing - FIXED!"""
    try:
        # Method 1: Check our own tracking
        if chat_id in current_playing:
            # We think we're playing, that's good enough
            return True
        
        # Method 2: Try to get active calls (if available)
        if hasattr(pytgcalls, 'get_active_call'):
            try:
                call = await pytgcalls.get_active_call(chat_id)
                if call:
                    return True
            except:
                pass
        
        # Method 3: Check if calls is async
        if hasattr(pytgcalls, 'calls'):
            try:
                # If it's a coroutine, await it
                if asyncio.iscoroutinefunction(pytgcalls.calls):
                    active_calls = await pytgcalls.calls()
                    if chat_id in active_calls:
                        return True
                # If it's a property/dict
                elif hasattr(pytgcalls.calls, '__contains__'):
                    if chat_id in pytgcalls.calls:
                        return True
            except:
                pass
        
        return False
    except Exception as e:
        logger.debug(f"validate_vc_state error: {e}")
        # If we can't check, assume we're playing (fail open)
        if chat_id in current_playing:
            return True
        return False

# ==========================================
# 🤖 ENHANCED USERBOT JOIN HANDLER
# ==========================================
async def ensure_userbot_in_chat(chat_id: int, retries: int = 3):
    """
    Fixed userbot join with state validation.
    """
    try:
        # First, cleanup any ghost states
        if chat_id in current_playing:
            is_actually_playing = await validate_vc_state(chat_id)
            if not is_actually_playing:
                logger.warning(f"[JOIN] Ghost state detected for {chat_id}, cleaning up")
                await force_cleanup(chat_id)
        
        # Check if already in chat
        try:
            member = await userbot.get_chat_member(chat_id, "me")
            logger.info(f"[JOIN] Userbot already in chat {chat_id}")
            return True
        except UserNotParticipant:
            pass
        except:
            pass
        
        # Try to join
        for attempt in range(retries):
            try:
                chat = await app.get_chat(chat_id)
                
                if chat.username:
                    await userbot.join_chat(chat.username)
                    await asyncio.sleep(1)
                    logger.info(f"[JOIN] Joined public chat {chat_id}")
                    return True
                else:
                    try:
                        invite_link = await app.export_chat_invite_link(chat_id)
                        await asyncio.sleep(0.5)
                        await userbot.join_chat(invite_link)
                        await asyncio.sleep(1)
                        logger.info(f"[JOIN] Joined private chat {chat_id}")
                        return True
                    except ChatAdminRequired:
                        raise Exception("❌ Bot needs 'Invite Users' permission")
                    except InviteRequestSent:
                        raise Exception("⏳ Join request sent, please approve")
                        
            except UserAlreadyParticipant:
                return True
            except Exception as e:
                error_str = str(e)
                if "INVITE_HASH_EXPIRED" in error_str and attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
                if attempt == retries - 1:
                    if "FLOOD_WAIT" in error_str:
                        raise Exception("⏳ Too many requests, wait a moment")
                    else:
                        raise Exception(f"❌ Join failed: {error_str[:80]}")
                await asyncio.sleep(2)
        
        return False
    except Exception as e:
        raise e

# ==========================================
# 🤖 ROBUST AUTO-PLAY ENGINE
# ==========================================
async def auto_end_handler(chat_id, duration):
    """Timer-based auto-skip with STRICT validation"""
    
    # CRITICAL: Validate duration first!
    if duration <= 0:
        logger.info(f"[AUTO-SKIP] Duration is 0 for {chat_id}, no timer")
        return
    
    # IMPORTANT: Songs under 60 seconds are often metadata errors!
    if duration < 60:
        logger.warning(f"[AUTO-SKIP] Short duration {duration}s for {chat_id} - might be wrong, setting longer buffer")
        wait_time = max(duration + 30, 90)  # At least 90 seconds for short songs
    elif duration < 120:
        # Songs under 2 minutes - add big buffer
        wait_time = duration + 20
    else:
        # Normal songs
        wait_time = duration + 15  # Increased from 10 to 15 seconds
    
    logger.info(f"[AUTO-SKIP] Chat {chat_id}: Timer {wait_time}s (song: {duration}s)")
    
    await asyncio.sleep(wait_time)

    # STRICT validation before auto-skip
    if chat_id not in current_playing:
        logger.info(f"[AUTO-SKIP] {chat_id}: Not playing anymore, cancelled")
        return
    
    # Verify we're still in VC
    is_in_vc = await validate_vc_state(chat_id)
    if not is_in_vc:
        logger.warning(f"[AUTO-SKIP] {chat_id}: Not in VC, cleaning up")
        await force_cleanup(chat_id)
        return
    
    # Check if there's a next song in queue
    queue = get_queue(chat_id)
    if not queue or len(queue) == 0:
        logger.info(f"[AUTO-SKIP] {chat_id}: No queue, will leave after this")
    
    logger.info(f"[AUTO-SKIP] {chat_id}: Triggering next song")
    await play_next_song(chat_id)

async def play_next_song(chat_id):
    """Play next song with robust validation"""
    next_song = get_next_song(chat_id)
    
    if next_song:
        try:
            # Validate we're in VC before playing
            is_in_vc = await validate_vc_state(chat_id)
            if not is_in_vc:
                logger.warning(f"[NEXT_SONG] Not in VC for {chat_id}, rejoining...")
                await ensure_userbot_in_chat(chat_id)
                await asyncio.sleep(1)
            
            await pytgcalls.play(
                chat_id,
                MediaStream(next_song['file_path'], audio_parameters=AudioQuality.HIGH)
            )
            current_playing[chat_id] = next_song
            
            # Start timer for next song with same smart logic
            if next_song['duration'] > 0:
                logger.info(f"[NEXT_SONG] Timer started: {next_song['duration']}s")
                asyncio.create_task(auto_end_handler(chat_id, next_song['duration']))
            else:
                logger.warning(f"[NEXT_SONG] No duration, skipping timer")
            
            await send_now_playing(chat_id, next_song)
            logger.info(f"[NEXT_SONG] Playing: {next_song['title']}")
            
        except Exception as e:
            error_str = str(e).lower()
            # Check for VC-related errors
            if any(x in error_str for x in ["group call", "not found", "no active", "invalid"]):
                logger.error(f"[NEXT_SONG] VC not active for {chat_id}")
                await force_cleanup(chat_id)
                try:
                    await app.send_message(
                        chat_id, 
                        "```\n⚠️ Voice chat ended\n```\n"
                        "Queue cleared. Start VC and use `/play` again."
                    )
                except:
                    pass
            else:
                logger.error(f"[NEXT_SONG] Error: {e}")
                await force_cleanup(chat_id)
    else:
        # Queue empty - leave VC
        logger.info(f"[NEXT_SONG] Queue empty for {chat_id}, leaving")
        await force_cleanup(chat_id)
        try:
            await app.send_message(chat_id, "```\n✅ Queue finished\n```")
        except:
            pass

# ==========================================
# 🎵 PLAY COMMAND (BULLETPROOF)
# ==========================================
@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply(
            "```\n╔════════════════════╗\n║   Music Player 🎵  ║\n╚════════════════════╝\n```\n"
            "**Usage:** `/play <song name>`"
        )
        return

    query = message.text.split(maxsplit=1)[1].strip()
    status = await message.reply("```\n🔍 Searching...\n```")

    try:
        # Search
        await status.edit("```\n╔════════════════════╗\n║  🔍 Searching...   ║\n╠════════════════════╣\n║ ██▱▱▱▱▱▱▱▱ 20%    ║\n╚════════════════════╝\n```")
        
        url = await search_youtube(query)
        if not url:
            await status.edit("```\n❌ Song not found\n```\nTry `/reboot` if stuck")
            return

        # Download
        await status.edit("```\n╔════════════════════╗\n║ 📥 Downloading...  ║\n╠════════════════════╣\n║ █████▱▱▱▱▱ 50%    ║\n╚════════════════════╝\n```")
        
        info = await download_audio(url)

        # Check if already playing - IMPROVED CHECK!
        chat_id = message.chat.id
        
        # Double-check: Are we actually playing?
        is_playing = False
        if chat_id in current_playing:
            # Verify we're still in VC
            is_in_vc = await validate_vc_state(chat_id)
            if is_in_vc:
                is_playing = True
                logger.info(f"[PLAY] Already playing, adding to queue for {chat_id}")
            else:
                # Ghost state! Clean it up
                logger.warning(f"[PLAY] Ghost state detected for {chat_id}, cleaning")
                await force_cleanup(chat_id)
                is_playing = False
        
        if is_playing:
            # Add to queue
            add_to_queue(chat_id, info)
            position = len(get_queue(chat_id))
            mins, secs = info['duration'] // 60, info['duration'] % 60
            
            await status.edit(
                f"```\n╔════════════════════╗\n║ ✅ Added to Queue  ║\n╚════════════════════╝\n```\n"
                f"**📍 Position:** `#{position}`\n"
                f"**🎵 Song:** `{info['title'][:40]}...`\n"
                f"**⏱ Duration:** `{mins}:{secs:02d}`"
            )
            return

        # Join VC
        await status.edit("```\n╔════════════════════╗\n║ 🤖 Joining VC...   ║\n╠════════════════════╣\n║ ████████▱▱ 80%    ║\n╚════════════════════╝\n```")
        
        await ensure_userbot_in_chat(message.chat.id)
        
        # Play
        await status.edit("```\n╔════════════════════╗\n║ ▶️ Starting...     ║\n╠════════════════════╣\n║ ██████████ 100%   ║\n╚════════════════════╝\n```")
        
        try:
            await pytgcalls.play(
                message.chat.id,
                MediaStream(info['file_path'], audio_parameters=AudioQuality.HIGH)
            )
        except Exception as e:
            error_str = str(e).lower()
            # Check if VC-related errors
            if any(x in error_str for x in ["groupcall", "group call", "not found", "invalid"]):
                logger.warning(f"[PLAY] VC error: {e}")
                # Explain to user
                raise Exception(
                    "❌ Voice chat is not active!\n\n"
                    "**Please:**\n"
                    "1️⃣ Start a voice chat first\n"
                    "2️⃣ Then use `/play` again\n\n"
                    "_The voice chat must be running before playing music._"
                )
            else:
                raise e
        
        current_playing[message.chat.id] = info
        
        # CRITICAL: Smart timer based on duration quality
        if info['duration'] > 0:
            # We have duration - use it with buffer
            logger.info(f"[PLAY] Starting timer for {info['title']} - Duration: {info['duration']}s")
            asyncio.create_task(auto_end_handler(message.chat.id, info['duration']))
        else:
            # No duration (live stream or error) - don't auto-skip
            logger.warning(f"[PLAY] No duration for {info['title']}, skipping auto-timer")
        
        await send_now_playing(message.chat.id, info)
        await status.delete()

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[PLAY] Error: {error_msg}")
        
        # User-friendly error messages
        if "Voice chat is not active" in error_msg:
            await status.edit(error_msg)
        elif "503" in error_msg or "Service unavailable" in error_msg:
            await status.edit(
                "```\n╔════════════════════╗\n║ ⚠️ API Overloaded  ║\n╚════════════════════╝\n```\n"
                "**The music API is currently overloaded.**\n\n"
                "**Please wait 2-3 minutes and try again.**\n"
                "The API server is receiving too many requests."
            )
        elif any(x in error_msg.lower() for x in ["groupcall", "invalid", "not found"]):
            await status.edit(
                "```\n╔════════════════════╗\n║ ⚠️ VC Not Active   ║\n╚════════════════════╝\n```\n"
                "**Voice chat is not running!**\n\n"
                "**Steps:**\n"
                "1️⃣ Start voice chat in group\n"
                "2️⃣ Use `/play <song>` again\n"
                "3️⃣ If still stuck, use `/reboot`"
            )
        elif any(x in error_msg for x in ["400", "500", "timeout", "failed"]):
            await status.edit(
                "```\n╔════════════════════╗\n║ ⚠️ Playback Failed ║\n╚════════════════════╝\n```\n"
                "**Try:** `/reboot` to reset\n"
                f"_Error: {error_msg[:50]}_"
            )
        else:
            await status.edit(f"```\n❌ Error\n```\n`{error_msg[:80]}`\n\n**Try:** `/reboot`")

# ==========================================
# 🔄 REBOOT COMMAND (FIXED ADMIN CHECK!)
# ==========================================
@app.on_message(filters.command("reboot", config.COMMAND_PREFIXES) & filters.group)
async def reboot_cmd(_, message):
    """Reboot music system for this chat"""
    chat_id = message.chat.id
    
    # SIMPLIFIED ADMIN CHECK (same as /skip fix)
    try:
        member = await app.get_chat_member(chat_id, message.from_user.id)
        user_status = member.status
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        user_status = "unknown"
    
    # Only block regular members
    if user_status == "member" or user_status == "restricted" or user_status == "left":
        await message.reply("```\n❌ Only admins can reboot\n```")
        return
    
    status = await message.reply("```\n🔄 Rebooting music system...\n```")
    
    # Force cleanup
    success = await force_cleanup(chat_id)
    
    if success:
        await status.edit(
            "```\n╔════════════════════╗\n║ ✅ System Rebooted ║\n╚════════════════════╝\n```\n"
            "**All queues cleared**\n**Use `/play` to start fresh**"
        )
        logger.info(f"[REBOOT] Chat {chat_id} rebooted by {message.from_user.id}")
    else:
        await status.edit("```\n⚠️ Reboot attempted\n```\nTry `/play` again")

# ==========================================
# 🎵 OTHER COMMANDS
# ==========================================
@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
async def stop_cmd(_, message):
    chat_id = message.chat.id
    if chat_id not in current_playing:
        await message.reply("```\n❌ Nothing playing\n```")
        return
    
    try:
        member = await app.get_chat_member(chat_id, message.from_user.id)
        if member.status not in ["creator", "administrator"]:
            await message.reply("```\n❌ Only admins can stop\n```")
            return
    except:
        pass
    
    await force_cleanup(chat_id)
    await message.reply("```\n⏹️ Stopped & cleaned up\n```")

@app.on_message(filters.command("skip", config.COMMAND_PREFIXES) & filters.group)
async def skip_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("```\n❌ Nothing to skip\n```")
        return
    
    try:
        member = await app.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ["creator", "administrator"]:
            await message.reply("```\n❌ Only admins can skip\n```")
            return
    except:
        pass
    
    user_name = message.from_user.first_name
    await message.reply(f"```\n⏭️ Skipped by {user_name}\n```")
    await play_next_song(message.chat.id)

@app.on_message(filters.command("pause", config.COMMAND_PREFIXES) & filters.group)
async def pause_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("```\n❌ Nothing playing\n```")
        return
    try:
        member = await app.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ["creator", "administrator"]:
            await message.reply("```\n❌ Only admins\n```")
            return
    except:
        pass
    try:
        await pytgcalls.pause_stream(message.chat.id)
        await message.reply("```\n⏸️ Paused\n```")
    except:
        await message.reply("```\n❌ Failed\n```")

@app.on_message(filters.command("resume", config.COMMAND_PREFIXES) & filters.group)
async def resume_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("```\n❌ Nothing playing\n```")
        return
    try:
        member = await app.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ["creator", "administrator"]:
            await message.reply("```\n❌ Only admins\n```")
            return
    except:
        pass
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("```\n▶️ Resumed\n```")
    except:
        await message.reply("```\n❌ Failed\n```")

@app.on_message(filters.command("queue", config.COMMAND_PREFIXES) & filters.group)
async def queue_cmd(_, message):
    queue = get_queue(message.chat.id)
    text = "```\n╔════════════════════╗\n║  🎵 Queue List     ║\n╚════════════════════╝\n```\n\n"
    
    if message.chat.id in current_playing:
        curr = current_playing[message.chat.id]
        text += f"**▶️ Now:** `{curr['title'][:40]}{'...' if len(curr['title']) > 40 else ''}`\n\n"
    
    if not queue:
        text += "**📭 Queue is empty**"
    else:
        for i, song in enumerate(queue[:10], 1):
            text += f"`{i}.` {song['title'][:35]}{'...' if len(song['title']) > 35 else ''}\n"
        if len(queue) > 10:
            text += f"\n*+{len(queue)-10} more*"
    
    await message.reply(text)

# ==========================================
# 🎛️ CALLBACKS
# ==========================================
@app.on_callback_query(filters.regex(r"^(stop|skip|pause|resume|close)"))
async def cb_handler(_, query):
    action = query.data
    chat_id = query.message.chat.id
    
    if action == "close":
        await query.message.delete()
        return

    try:
        member = await app.get_chat_member(chat_id, query.from_user.id)
        if member.status not in ["creator", "administrator"]:
            await query.answer("❌ Only admins!", show_alert=True)
            return
    except:
        pass

    if action == "stop":
        await force_cleanup(chat_id)
        await query.message.delete()
        await query.answer("⏹️ Stopped")
    elif action == "skip":
        await query.answer(f"⏭️ Skipped")
        await play_next_song(chat_id)
    elif action == "pause":
        await pytgcalls.pause_stream(chat_id)
        await query.answer("⏸️ Paused")
    elif action == "resume":
        await pytgcalls.resume_stream(chat_id)
        await query.answer("▶️ Resumed")

# ==========================================
# 🎨 NOW PLAYING UI
# ==========================================
async def send_now_playing(chat_id, info):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Tic Tac Toe", callback_data="game_tictactoe"),
            InlineKeyboardButton("✊ Rock Paper", callback_data="game_rps")
        ],
        [
            InlineKeyboardButton("𝐒𝐔𝐌𝐌𝐎𝐍 𝐌𝐄 𝐍𝐎𝐖", url="https://t.me/MariaModBot?startgroup=true")
        ]
    ])
    
    if info['duration'] > 0:
        mins, secs = info['duration'] // 60, info['duration'] % 60
        duration_str = f"{mins}:{secs:02d} Minutes"
    else:
        duration_str = "🔴 Live Stream"
    
    title = info['title'][:60] + ('...' if len(info['title']) > 60 else '')
    
    text = (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎵 **NOW PLAYING**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎧 `{title}`\n"
        f"⏱ `{duration_str}` | 👤 You\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    try:
        if info.get('thumbnail'):
            await app.send_photo(chat_id, info['thumbnail'], caption=text, reply_markup=buttons)
        else:
            await app.send_message(chat_id, text, reply_markup=buttons)
    except:
        try:
            await app.send_message(chat_id, text, reply_markup=buttons)
        except:
            pass

__module__ = "Music"
__help__ = """
```
╔════════════════════╗
║  🎵 Music Player   ║
╚════════════════════╝
```

**Commands:**
• `/play <song>` - Play music
• `/skip` - Skip current
• `/stop` - Stop & clear
• `/pause` - Pause
• `/resume` - Resume
• `/queue` - View queue
• `/reboot` - Reset system (if stuck)

*Powered by XBitCode API*
"""
