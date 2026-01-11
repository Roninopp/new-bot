"""
Music Player Module - Commands & Events (FINAL STABLE VERSION)
Fixes: 'on_stream_end' Crash & restores Auto-Leave
"""

import asyncio
import os
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pytgcalls.types import MediaStream, AudioQuality

# Import Core Logic (New API System)
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
from Yumeko.modules.music_v2 import userbot, pytgcalls, ensure_userbot_in_chat

from Yumeko import app
from config import config
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error

# ==========================================
# 🤖 AUTO-PLAY & TIMER ENGINE
# ==========================================
async def auto_end_handler(chat_id, duration):
    """
    Waits for the song duration + 2 seconds, then plays next.
    Replaces the broken @on_stream_end event.
    """
    if duration > 0:
        await asyncio.sleep(duration + 2)  # Wait for song to finish
    else:
        return # Live stream or unknown duration, don't auto-skip

    # Double check if we are still playing the SAME song
    # (In case user stopped/skipped manually)
    if chat_id in current_playing:
        # Trigger next song
        await play_next_song(chat_id)

async def play_next_song(chat_id):
    """Handles playing the next song or leaving"""
    next_song = get_next_song(chat_id)
    
    if next_song:
        try:
            # Play next
            await pytgcalls.play(
                chat_id,
                MediaStream(
                    next_song['file_path'],
                    audio_parameters=AudioQuality.HIGH
                )
            )
            current_playing[chat_id] = next_song
            await send_now_playing(chat_id, next_song)
            
            # 🕒 Start the Timer for the new song
            asyncio.create_task(auto_end_handler(chat_id, next_song['duration']))
            
        except Exception as e:
            print(f"Error playing next: {e}")
            await pytgcalls.leave_call(chat_id)
    else:
        # Empty Queue -> Leave
        if chat_id in current_playing:
            del current_playing[chat_id]
            
        await app.send_message(chat_id, "✅ **Queue finished. Leaving voice chat.**")
        await asyncio.sleep(3)
        try:
            await pytgcalls.leave_call(chat_id)
        except:
            pass

# ==========================================
# 🎵 PLAY COMMAND
# ==========================================
@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply("Usage: `/play <song>`\nExample: `/play Believer`")
        return

    query = message.text.split(maxsplit=1)[1].strip()
    status = await message.reply("🔍 **Searching...**")

    try:
        # 1. Get URL
        url = await search_youtube(query)
        if not url:
            await status.edit("❌ Song not found.")
            return

        # 2. Check Queue
        if message.chat.id in current_playing:
            await status.edit("📥 **Downloading for queue...**")
            # Get metadata first using API/yt-dlp
            info = await download_audio(url) 
            add_to_queue(message.chat.id, info)
            
            # Show Queue Position
            queue = get_queue(message.chat.id)
            position = len(queue)
            await status.edit(
                f"✅ **Added to Queue #{position}**\n"
                f"🎵 **Title:** `{info['title']}`\n"
                f"⏱️ **Duration:** `{info['duration'] // 60}:{info['duration'] % 60:02d}`"
            )
            return

        # 3. Play Now
        await status.edit("📥 **Downloading...**")
        info = await download_audio(url)
        
        # Ensure userbot is ready
        await ensure_userbot_in_chat(message.chat.id)
        
        # Stream!
        await pytgcalls.play(
            message.chat.id,
            MediaStream(
                info['file_path'],
                audio_parameters=AudioQuality.HIGH
            )
        )
        
        current_playing[message.chat.id] = info
        await send_now_playing(message.chat.id, info)
        
        # 🕒 START THE TIMER (This fixes the "Stuck in VC" issue)
        asyncio.create_task(auto_end_handler(message.chat.id, info['duration']))
        
        await status.delete()

    except Exception as e:
        await status.edit(f"❌ Error: {e}")

# ==========================================
# 🎵 TEXT COMMANDS
# ==========================================

@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
async def stop_cmd(_, message):
    chat_id = message.chat.id
    if chat_id not in current_playing:
        await message.reply("❌ Nothing is playing.")
        return
    
    clear_queue(chat_id)
    if chat_id in current_playing:
        del current_playing[chat_id]
        
    await pytgcalls.leave_call(chat_id)
    await message.reply("⏹️ **Stopped and cleared queue.**")

@app.on_message(filters.command("skip", config.COMMAND_PREFIXES) & filters.group)
async def skip_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("❌ Nothing to skip.")
        return
        
    await message.reply("⏭️ **Skipping...**")
    await play_next_song(message.chat.id)

@app.on_message(filters.command("pause", config.COMMAND_PREFIXES) & filters.group)
async def pause_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("❌ Nothing playing.")
        return
    try:
        await pytgcalls.pause_stream(message.chat.id)
        await message.reply("⏸️ **Paused.**")
    except:
        await message.reply("❌ Failed to pause.")

@app.on_message(filters.command("resume", config.COMMAND_PREFIXES) & filters.group)
async def resume_cmd(_, message):
    if message.chat.id not in current_playing:
        await message.reply("❌ Nothing playing.")
        return
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("▶️ **Resumed.**")
    except:
        await message.reply("❌ Failed to resume.")

@app.on_message(filters.command("queue", config.COMMAND_PREFIXES) & filters.group)
async def queue_cmd(_, message):
    queue = get_queue(message.chat.id)
    if not queue:
        await message.reply("📭 **Queue is empty!**")
        return
    
    text = "🎵 **Current Queue:**\n\n"
    if message.chat.id in current_playing:
        curr = current_playing[message.chat.id]
        text += f"▶️ **Now:** {curr['title']}\n\n"
    
    for i, song in enumerate(queue[:10], 1):
        text += f"{i}. {song['title']}\n"
        
    if len(queue) > 10:
        text += f"\n*...and {len(queue)-10} more*"
        
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
        if chat_id in current_playing: del current_playing[chat_id]
        await pytgcalls.leave_call(chat_id)
        await query.message.delete()
        await query.answer("Stopped")
        
    elif action == "skip":
        await query.answer("Skipped")
        await play_next_song(chat_id)
        
    elif action == "pause":
        await pytgcalls.pause_stream(chat_id)
        await query.answer("Paused")
        
    elif action == "resume":
        await pytgcalls.resume_stream(chat_id)
        await query.answer("Resumed")

# ==========================================
# 🤖 LOGIC HELPERS
# ==========================================
async def send_now_playing(chat_id, info):
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸", callback_data=f"pause"),
            InlineKeyboardButton("▶️", callback_data=f"resume"),
            InlineKeyboardButton("⏭", callback_data=f"skip"),
            InlineKeyboardButton("⏹", callback_data=f"stop")
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])
    
    text = (
        f"**▶️ Now Playing**\n\n"
        f"🎵 `{info['title']}`\n"
        f"⏱️ `{info['duration'] // 60}:{info['duration'] % 60:02d}`\n"
        f"🎧 Source: **Samurai Network**"
    )
    
    try:
        if info.get('thumbnail'):
            await app.send_photo(chat_id, info['thumbnail'], caption=text, reply_markup=buttons)
        else:
            await app.send_message(chat_id, text, reply_markup=buttons)
    except:
        pass

# ==========================================
# ℹ️ MODULE INFO
# ==========================================
__module__ = "Music"
__help__ = """
**🎵 Music Player (API Powered)**

• `/play <song>` - Play or queue a song
• `/skip` - Skip current song
• `/stop` - Stop & Clear Queue
• `/pause` - Pause playback
• `/resume` - Resume playback
• `/queue` - Check current list

*Powered by XBitCode*
"""
