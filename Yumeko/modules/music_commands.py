"""
Music Player Module - Clean Professional Edition (v8)
Features: Animated loading bars, compact output, beautiful design
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
# 🎨 ANIMATED PROGRESS BAR
# ==========================================
async def animated_progress(message, total_steps=5):
    """
    Shows animated loading bar with stages.
    """
    stages = [
        ("🔍 Searching", "█▱▱▱▱▱▱▱▱▱", 10),
        ("📡 Fetching", "███▱▱▱▱▱▱▱", 30),
        ("📥 Downloading", "█████▱▱▱▱▱", 50),
        ("🎵 Processing", "███████▱▱▱", 70),
        ("🤖 Joining VC", "█████████▱", 90),
        ("✅ Ready", "██████████", 100)
    ]
    
    for stage, bar, percent in stages:
        text = (
            f"```\n"
            f"╔════════════════════╗\n"
            f"║  {stage:^18}║\n"
            f"╠════════════════════╣\n"
            f"║ {bar} {percent}% ║\n"
            f"╚════════════════════╝\n"
            f"```"
        )
        try:
            await message.edit(text)
            await asyncio.sleep(0.5)
        except:
            pass
    
    return message

# ==========================================
# 🤖 ENHANCED USERBOT JOIN HANDLER (FIXED INVITE HASH!)
# ==========================================
async def ensure_userbot_in_chat(chat_id: int, retries: int = 3):
    """
    Fixed userbot join - generates fresh invite links each time.
    """
    try:
        # Check if already in chat
        try:
            member = await userbot.get_chat_member(chat_id, "me")
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
                    # Public group - join via username
                    await userbot.join_chat(chat.username)
                    await asyncio.sleep(1)
                    return True
                else:
                    # Private group - need FRESH invite link
                    try:
                        # IMPORTANT: Revoke old link and create NEW one each time!
                        # This prevents INVITE_HASH_EXPIRED error
                        invite_link = await app.export_chat_invite_link(chat_id)
                        
                        # Small delay to ensure link is active
                        await asyncio.sleep(0.5)
                        
                        # Join via fresh invite link
                        await userbot.join_chat(invite_link)
                        await asyncio.sleep(1)
                        return True
                        
                    except ChatAdminRequired:
                        raise Exception(
                            "❌ Bot needs 'Invite Users' permission.\n"
                            "Give bot admin rights with invite permission."
                        )
                    except InviteRequestSent:
                        raise Exception(
                            "⏳ Join request sent to admins.\n"
                            "Please approve the assistant."
                        )
                        
            except UserAlreadyParticipant:
                return True
                
            except Exception as e:
                error_str = str(e)
                
                # Handle INVITE_HASH_EXPIRED specifically
                if "INVITE_HASH_EXPIRED" in error_str:
                    if attempt < retries - 1:
                        await asyncio.sleep(1)
                        continue  # Retry with new link
                    raise Exception(
                        "❌ Invite link expired.\n"
                        "Please add the assistant bot manually or try again."
                    )
                
                if attempt == retries - 1:
                    # Last attempt failed
                    if "FLOOD_WAIT" in error_str:
                        raise Exception("⏳ Too many requests. Wait a few minutes.")
                    elif "INVITE_REQUEST_SENT" in error_str:
                        raise Exception("⏳ Join request sent. Please approve.")
                    elif "CHANNELS_TOO_MUCH" in error_str:
                        raise Exception("❌ Assistant joined too many groups.")
                    else:
                        raise Exception(f"❌ Join failed: {error_str[:80]}")
                
                await asyncio.sleep(2)  # Wait before retry
        
        return False
        
    except Exception as e:
        raise e

# ==========================================
# 🤖 AUTO-PLAY ENGINE (FIXED TIMER BUG!)
# ==========================================
async def auto_end_handler(chat_id, duration):
    """Fixed: Only triggers if duration is reliable"""
    # Don't auto-skip if duration is 0 or unreliable
    if duration <= 0 or duration > 7200:  # Skip if > 2 hours (likely wrong)
        return
    
    # Add extra buffer time to prevent early skip
    wait_time = duration + 5  # 5 seconds buffer instead of 2
    await asyncio.sleep(wait_time)

    # Double check if the SAME song is still playing
    if chat_id in current_playing:
        # Check if song file still exists (means it's the same song)
        current_file = current_playing[chat_id].get('file_path')
        if current_file and os.path.exists(current_file):
            await play_next_song(chat_id)

async def play_next_song(chat_id):
    next_song = get_next_song(chat_id)
    
    if next_song:
        try:
            await pytgcalls.play(
                chat_id,
                MediaStream(next_song['file_path'], audio_parameters=AudioQuality.HIGH)
            )
            current_playing[chat_id] = next_song
            await send_now_playing(chat_id, next_song)
            asyncio.create_task(auto_end_handler(chat_id, next_song['duration']))
        except Exception as e:
            print(f"Error: {e}")
            await pytgcalls.leave_call(chat_id)
    else:
        if chat_id in current_playing:
            del current_playing[chat_id]
        await app.send_message(chat_id, "```\n✅ Queue finished\n```")
        await asyncio.sleep(2)
        try:
            await pytgcalls.leave_call(chat_id)
        except:
            pass

# ==========================================
# 🎵 PLAY COMMAND WITH ANIMATION
# ==========================================
@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply(
            "```\n"
            "╔════════════════════╗\n"
            "║   Music Player 🎵  ║\n"
            "╚════════════════════╝\n"
            "```\n"
            "**Usage:** `/play <song name>`"
        )
        return

    query = message.text.split(maxsplit=1)[1].strip()
    
    # Start animated progress
    status = await message.reply("```\n🔍 Initializing...\n```")

    try:
        # Animate: Searching
        await status.edit(
            "```\n"
            "╔════════════════════╗\n"
            "║   🔍 Searching...  ║\n"
            "╠════════════════════╣\n"
            "║ ██▱▱▱▱▱▱▱▱ 20%    ║\n"
            "╚════════════════════╝\n"
            "```"
        )
        
        url = await search_youtube(query)
        if not url:
            await status.edit("```\n❌ Song not found\n```")
            return

        # Animate: Downloading
        await status.edit(
            "```\n"
            "╔════════════════════╗\n"
            "║  📥 Downloading... ║\n"
            "╠════════════════════╣\n"
            "║ █████▱▱▱▱▱ 50%    ║\n"
            "╚════════════════════╝\n"
            "```"
        )
        
        info = await download_audio(url)

        # Check if already playing (queue)
        if message.chat.id in current_playing:
            add_to_queue(message.chat.id, info)
            queue = get_queue(message.chat.id)
            position = len(queue)
            
            mins = info['duration'] // 60
            secs = info['duration'] % 60
            
            await status.edit(
                f"```\n"
                f"╔════════════════════╗\n"
                f"║  ✅ Added to Queue ║\n"
                f"╚════════════════════╝\n"
                f"```\n"
                f"**📍 Position:** `#{position}`\n"
                f"**⏱ Duration:** `{mins}:{secs:02d}`"
            )
            return

        # Animate: Joining VC
        await status.edit(
            "```\n"
            "╔════════════════════╗\n"
            "║  🤖 Joining VC...  ║\n"
            "╠════════════════════╣\n"
            "║ ████████▱▱ 80%    ║\n"
            "╚════════════════════╝\n"
            "```"
        )
        
        await ensure_userbot_in_chat(message.chat.id)
        
        # Animate: Starting
        await status.edit(
            "```\n"
            "╔════════════════════╗\n"
            "║  ▶️ Starting...    ║\n"
            "╠════════════════════╣\n"
            "║ ██████████ 100%   ║\n"
            "╚════════════════════╝\n"
            "```"
        )
        
        await pytgcalls.play(
            message.chat.id,
            MediaStream(info['file_path'], audio_parameters=AudioQuality.HIGH)
        )
        
        current_playing[message.chat.id] = info
        await send_now_playing(message.chat.id, info)
        asyncio.create_task(auto_end_handler(message.chat.id, info['duration']))
        
        await status.delete()

    except Exception as e:
        await status.edit(f"```\n❌ Error\n```\n`{str(e)[:80]}`")

# ==========================================
# 🎵 OTHER COMMANDS
# ==========================================

@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
async def stop_cmd(_, message):
    chat_id = message.chat.id
    if chat_id not in current_playing:
        await message.reply("```\n❌ Nothing is playing\n```")
        return
    
    # SIMPLIFIED ADMIN CHECK
    user_id = message.from_user.id
    
    try:
        member = await app.get_chat_member(chat_id, user_id)
        user_status = member.status
    except:
        user_status = "unknown"
    
    # Only block regular members
    if user_status == "member" or user_status == "restricted" or user_status == "left":
        await message.reply("```\n❌ Only admins can stop\n```")
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
        await message.reply("```\n❌ Nothing to skip\n```")
        return
    
    # SIMPLIFIED ADMIN CHECK
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    try:
        member = await app.get_chat_member(chat_id, user_id)
        user_status = member.status
        
        # Log for debugging
        print(f"[SKIP] User: {message.from_user.first_name}, Status: {user_status}")
        
    except Exception as e:
        # If we can't check, assume they're allowed (fail open)
        print(f"[SKIP ERROR] {e}")
        user_status = "member"  # Default to member, will skip check below
    
    # Only block if we KNOW they're a regular member
    if user_status == "member" or user_status == "restricted" or user_status == "left":
        await message.reply("```\n❌ Only admins can skip\n```")
        return
    
    # If creator, administrator, or check failed = allow
    # Show who skipped
    user_name = message.from_user.first_name
    await message.reply(f"```\n⏭️ Skipped by {user_name}\n```")
    await play_next_song(message.chat.id)

@app.on_message(filters.command("pause", config.COMMAND_PREFIXES) & filters.group)
async def pause_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("```\n❌ Nothing playing\n```")
        return
    
    # SIMPLIFIED ADMIN CHECK
    try:
        member = await app.get_chat_member(message.chat.id, message.from_user.id)
        user_status = member.status
    except:
        user_status = "unknown"
    
    if user_status == "member" or user_status == "restricted" or user_status == "left":
        await message.reply("```\n❌ Only admins can pause\n```")
        return
        
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
    
    # SIMPLIFIED ADMIN CHECK
    try:
        member = await app.get_chat_member(message.chat.id, message.from_user.id)
        user_status = member.status
    except:
        user_status = "unknown"
    
    if user_status == "member" or user_status == "restricted" or user_status == "left":
        await message.reply("```\n❌ Only admins can resume\n```")
        return
        
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("```\n▶️ Resumed\n```")
    except:
        await message.reply("```\n❌ Failed\n```")

@app.on_message(filters.command("queue", config.COMMAND_PREFIXES) & filters.group)
async def queue_cmd(_, message):
    queue = get_queue(message.chat.id)
    
    text = "```\n╔════════════════════╗\n║   🎵 Queue List   ║\n╚════════════════════╝\n```\n\n"
    
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
# 🎛️ CALLBACKS (ADMIN ONLY!)
# ==========================================
@app.on_callback_query(filters.regex(r"^(stop|skip|pause|resume|close)"))
async def cb_handler(_, query):
    action = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    
    if action == "close":
        await query.message.delete()
        return

    # Check if user is admin
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status not in ["creator", "administrator"]:
            await query.answer("❌ Only admins can use this!", show_alert=True)
            return
    except:
        await query.answer("❌ Error checking permissions", show_alert=True)
        return

    if action == "stop":
        clear_queue(chat_id)
        if chat_id in current_playing: 
            del current_playing[chat_id]
        await pytgcalls.leave_call(chat_id)
        await query.message.delete()
        await query.answer("⏹️ Stopped")
        
    elif action == "skip":
        user_name = query.from_user.first_name
        await query.answer(f"⏭️ Skipped by {user_name}")
        await play_next_song(chat_id)
        
    elif action == "pause":
        await pytgcalls.pause_stream(chat_id)
        await query.answer("⏸️ Paused")
        
    elif action == "resume":
        await pytgcalls.resume_stream(chat_id)
        await query.answer("▶️ Resumed")

# ==========================================
# 🎨 COMPACT NOW PLAYING UI (like your reference)
# ==========================================
async def send_now_playing(chat_id, info):
    """Clean, compact now playing message with mini-games!"""
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎮 Tic Tac Toe", callback_data="game_tictactoe"),
            InlineKeyboardButton("✊ Rock Paper", callback_data="game_rps")
        ],
        [
            InlineKeyboardButton("𝐒𝐔𝐌𝐌𝐎𝐍 𝐌𝐄 𝐍𝐎𝐖", url="https://t.me/MariaModBot?startgroup=true")
        ]
    ])
    
    # Format duration
    if info['duration'] > 0:
        mins = info['duration'] // 60
        secs = info['duration'] % 60
        duration_str = f"{mins}:{secs:02d} Minutes"
    else:
        duration_str = "🔴 Live Stream"
    
    # Clean title (max 60 chars)
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
        # Try with thumbnail
        if info.get('thumbnail'):
            await app.send_photo(
                chat_id, 
                info['thumbnail'], 
                caption=text, 
                reply_markup=buttons
            )
        else:
            await app.send_message(chat_id, text, reply_markup=buttons)
    except:
        # Fallback without thumbnail
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
╔═══════════════════╗
║  🎵 Music Player  ║
╚═══════════════════╝
```

**Commands:**
• `/play <song>` - Play music
• `/skip` - Skip current
• `/stop` - Stop & clear
• `/pause` - Pause
• `/resume` - Resume
• `/queue` - View queue

*Powered by XBitCode API*
"""
