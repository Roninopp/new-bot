"""
Music Player Module - Part 2B: Commands & Callbacks
FIXED VERSION - Simplified and more reliable
Handles: User commands and button interactions
"""

import asyncio
import os
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# Import from Part 1
from Yumeko.modules.music import (
    FFMPEG_AVAILABLE,
    download_audio,
    search_youtube,
    is_youtube_url,
    add_to_queue,
    get_queue,
    clear_queue,
    current_playing
)

# Import from Part 2A (Core)
from Yumeko.modules.music_v2 import (
    userbot,
    pytgcalls,
    ensure_userbot_in_chat,
    download_and_stream,
    play_next,
    send_now_playing,
    monitoring_tasks,
    stream_started,
    monitor_stream_duration
)

from Yumeko import app
from config import config
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error

# ==========================================
# 🎵 ENHANCED PLAY COMMAND (RELIABLE MODE)
# ==========================================
@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    """
    Enhanced play command with:
    - Always download first (more reliable)
    - Better error handling
    - Auto-join fixes
    """
    print(f"\n🎵 [play_command] ========== RECEIVED ==========")
    print(f"🎵 [play_command] Chat: {message.chat.id}, User: {message.from_user.id}")
    
    # Check query
    if len(message.command) < 2:
        await message.reply(
            "**Usage:** `/play <song name or URL>`\n\n"
            "**Example:** `/play Believer`"
        )
        return
    
    query = message.text.split(maxsplit=1)[1].strip()
    
    status_msg = await message.reply(
        "```\n"
        "[░░░░░░░░░░] 0%\n"
        "⏳ Initializing...\n"
        "```"
    )
    
    try:
        # Step 1: Ensure userbot in chat
        await status_msg.edit(
            "```\n"
            "[██░░░░░░░░] 20%\n"
            "🔄 Verifying userbot access...\n"
            "```"
        )
        
        success, error_msg = await ensure_userbot_in_chat(message.chat.id)
        if not success:
            await status_msg.edit(
                f"❌ **Failed to join chat!**\n\n"
                f"**Reason:** {error_msg}\n\n"
                "**Solutions:**\n"
                "• Make bot admin with 'Invite Users' permission\n"
                "• Manually add userbot to group\n"
                "• Check group privacy settings"
            )
            return
        
        # Step 2: Search YouTube
        await status_msg.edit(
            "```\n"
            "[████░░░░░░] 40%\n"
            "🔍 Searching YouTube...\n"
            "```"
        )
        
        if is_youtube_url(query):
            url = query
            print(f"🔗 [play_command] Direct URL provided: {url}")
        else:
            url = await search_youtube(query)
            if not url:
                await status_msg.edit("❌ **No results found!**\n\nTry a different search query.")
                return
            print(f"🔍 [play_command] Search result: {url}")
        
        # Step 3: Prepare song info
        song_info = {
            'title': query[:50] if not is_youtube_url(query) else 'Loading...',
            'url': url,
            'file_path': None,
            'duration': 0,
            'requester': message.from_user.mention,
            'thumbnail': None
        }
        
        # Step 4: Check if already playing (queue it)
        if message.chat.id in current_playing and stream_started.get(message.chat.id):
            await status_msg.edit(
                "```\n"
                "[██████░░░░] 60%\n"
                "📥 Downloading for queue...\n"
                "```"
            )
            
            # Download first to get proper info
            try:
                audio_data = await download_audio(url)
                song_info['title'] = audio_data.get('title', song_info['title'])
                song_info['duration'] = audio_data.get('duration', 0)
                song_info['file_path'] = audio_data.get('file_path')
                song_info['thumbnail'] = audio_data.get('thumbnail')
            except Exception as e:
                print(f"⚠️ [play_command] Queue download failed: {e}")
                # Still add to queue with basic info
            
            add_to_queue(message.chat.id, song_info)
            position = len(get_queue(message.chat.id))
            
            duration = song_info.get('duration', 0)
            queue_msg = (
                f"**✅ Added to Queue #{position}**\n\n"
                f"🎵 **Title:** {song_info['title']}\n"
                f"👤 **Requested by:** {message.from_user.mention}\n"
                f"⏱️ **Duration:** {duration // 60}:{duration % 60:02d}"
            )
            await status_msg.edit(queue_msg)
            print(f"✅ [play_command] Added to queue at position {position}")
            return
        
        # Step 5: Download audio
        await status_msg.edit(
            "```\n"
            "[██████░░░░] 60%\n"
            "📥 Downloading audio...\n"
            "```"
        )
        
        try:
            audio_data = await download_audio(url)
            song_info['title'] = audio_data.get('title', song_info['title'])
            song_info['duration'] = audio_data.get('duration', 0)
            song_info['file_path'] = audio_data.get('file_path')
            song_info['thumbnail'] = audio_data.get('thumbnail')
            print(f"✅ [play_command] Downloaded: {song_info['file_path']}")
        except Exception as e:
            error_str = str(e)
            print(f"❌ [play_command] Download failed: {error_str}")
            
            # Provide helpful error message
            if "Sign in" in error_str or "bot" in error_str.lower():
                await status_msg.edit(
                    "❌ **Download Failed - Bot Detection**\n\n"
                    "YouTube detected the bot. Possible fixes:\n"
                    "• Refresh cookies (export from incognito)\n"
                    "• Wait a few minutes and try again\n"
                    "• Try a different video"
                )
            elif "format" in error_str.lower() or "Only images" in error_str:
                await status_msg.edit(
                    "❌ **Download Failed - No Audio Available**\n\n"
                    "YouTube blocked audio formats. Possible fixes:\n"
                    "• Update cookies\n"
                    "• Install rustypipe-botguard v1.x\n"
                    "• Try a different video"
                )
            else:
                await status_msg.edit(
                    f"❌ **Download Failed**\n\n"
                    f"`{error_str[:150]}`"
                )
            return
        
        # Step 6: Start streaming
        await status_msg.edit(
            "```\n"
            "[████████░░] 80%\n"
            "🎙️ Connecting to voice chat...\n"
            "```"
        )
        
        current_playing[message.chat.id] = song_info
        
        # Stream with retry logic
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    await status_msg.edit(f"🔄 **Retry {attempt}/{max_retries}** - Reconnecting...")
                    
                    # Leave and refresh
                    try:
                        await pytgcalls.leave_call(message.chat.id)
                    except:
                        pass
                    
                    await userbot.get_chat(message.chat.id)
                    await asyncio.sleep(2)
                
                # Import here to avoid circular import
                from pytgcalls.types import MediaStream, AudioQuality
                
                print(f"🎵 [play_command] Streaming: {song_info['file_path']}")
                
                await pytgcalls.play(
                    message.chat.id,
                    MediaStream(
                        song_info['file_path'],
                        audio_parameters=AudioQuality.HIGH
                    )
                )
                
                stream_started[message.chat.id] = True
                print("✅ [play_command] Stream started successfully!")
                
                # Start duration monitoring
                duration = song_info.get('duration', 0)
                if duration > 0:
                    task = asyncio.create_task(
                        monitor_stream_duration(
                            message.chat.id, 
                            song_info['file_path'], 
                            duration
                        )
                    )
                    monitoring_tasks[message.chat.id] = task
                    print(f"⏰ [play_command] Duration monitor started for {duration}s")
                
                break  # Success!
                
            except Exception as e:
                last_error = str(e)
                print(f"❌ [play_command] Attempt {attempt + 1} failed: {last_error}")
                
                if attempt == max_retries - 1:
                    # All retries failed
                    # Clean up
                    if message.chat.id in current_playing:
                        del current_playing[message.chat.id]
                    if song_info.get('file_path') and os.path.exists(song_info['file_path']):
                        try:
                            os.remove(song_info['file_path'])
                        except:
                            pass
                    
                    if "NoActiveGroupCall" in last_error or "GROUPCALL" in last_error:
                        await status_msg.edit(
                            "❌ **No Active Voice Chat!**\n\n"
                            "Please start a voice chat in this group first, then try `/play` again."
                        )
                    else:
                        await status_msg.edit(
                            f"❌ **Stream Failed**\n\n"
                            f"`{last_error[:150]}`\n\n"
                            "Please try again."
                        )
                    return
        
        # Step 7: Send now playing message
        await status_msg.edit(
            "```\n"
            "[██████████] 100%\n"
            "✅ Playing!\n"
            "```"
        )
        await asyncio.sleep(1)
        
        format_type = "MP3" if FFMPEG_AVAILABLE else "M4A"
        duration = song_info.get('duration', 0)
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{message.chat.id}"),
                InlineKeyboardButton("⏭ Skip", callback_data=f"skip_{message.chat.id}"),
                InlineKeyboardButton("⏹ Stop", callback_data=f"stop_{message.chat.id}")
            ],
            [
                InlineKeyboardButton("📋 Queue", callback_data=f"queue_{message.chat.id}"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])
        
        now_playing = (
            f"**▶️ Now Playing**\n\n"
            f"> 🎵 Title: `{song_info['title']}`\n"
            f"> 👤 Requested by: {message.from_user.mention}\n"
            f"> ⏱️ Duration: `{duration // 60}:{duration % 60:02d}`\n"
            f"> 🎧 Quality: **{format_type}**"
        )
        
        if song_info.get('thumbnail'):
            try:
                await status_msg.delete()
                await message.reply_photo(
                    song_info['thumbnail'],
                    caption=now_playing,
                    reply_markup=buttons
                )
            except:
                await status_msg.edit(now_playing, reply_markup=buttons)
        else:
            await status_msg.edit(now_playing, reply_markup=buttons)
                
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [play_command] Critical Error: {error_msg}")
        await status_msg.edit(
            f"❌ **Error**\n\n`{error_msg[:150]}`\n\n"
            "Please try again or contact support."
        )

# ==========================================
# 🎵 BUTTON CALLBACKS
# ==========================================
@app.on_callback_query(filters.regex(r"^(pause|resume|skip|stop|queue|close)"))
async def button_handler(client, query: CallbackQuery):
    """Handle control button presses"""
    data = query.data
    action = data.split("_")[0]
    
    if action == "close":
        await query.message.delete()
        return
    
    # Extract chat_id from callback data
    try:
        chat_id = int(data.split("_")[1])
    except (IndexError, ValueError):
        chat_id = query.message.chat.id
    
    if action == "skip":
        if chat_id in current_playing and stream_started.get(chat_id):
            await query.answer("⏭️ Skipping...", show_alert=False)
            await play_next(chat_id, send_message=True, force_skip=True)
        else:
            await query.answer("❌ Nothing playing!", show_alert=True)
    
    elif action == "stop":
        # Cancel monitoring
        if chat_id in monitoring_tasks:
            try:
                monitoring_tasks[chat_id].cancel()
                del monitoring_tasks[chat_id]
            except:
                pass
        
        # Clear state
        clear_queue(chat_id)
        if chat_id in current_playing:
            # Clean up file
            file_path = current_playing[chat_id].get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass
            del current_playing[chat_id]
        
        if chat_id in stream_started:
            del stream_started[chat_id]
        
        # Leave call
        try:
            await pytgcalls.leave_call(chat_id)
        except:
            pass
        
        await query.answer("⏹️ Stopped", show_alert=False)
        try:
            await query.message.edit_caption("⏹️ **Playback stopped**")
        except:
            try:
                await query.message.edit_text("⏹️ **Playback stopped**")
            except:
                pass
    
    elif action == "queue":
        queue = get_queue(chat_id)
        if not queue and chat_id not in current_playing:
            await query.answer("📭 Queue empty!", show_alert=True)
            return
        
        text = "🎵 **Queue:**\n\n"
        if chat_id in current_playing:
            text += f"▶️ {current_playing[chat_id]['title'][:35]}\n\n"
        
        for i, song in enumerate(queue[:10], 1):
            text += f"{i}. {song['title'][:35]}\n"
        
        if len(queue) > 10:
            text += f"\n... and {len(queue) - 10} more"
        
        await query.answer(text[:200], show_alert=True)
    
    elif action == "pause":
        try:
            await pytgcalls.pause_stream(chat_id)
            await query.answer("⏸️ Paused", show_alert=False)
        except:
            await query.answer("❌ Failed to pause!", show_alert=True)
    
    elif action == "resume":
        try:
            await pytgcalls.resume_stream(chat_id)
            await query.answer("▶️ Resumed", show_alert=False)
        except:
            await query.answer("❌ Failed to resume!", show_alert=True)

# ==========================================
# 🎵 TEXT COMMANDS
# ==========================================
@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
@error
async def stop_command(client, message: Message):
    """Stop playback and clear queue"""
    chat_id = message.chat.id
    
    # Cancel monitoring
    if chat_id in monitoring_tasks:
        try:
            monitoring_tasks[chat_id].cancel()
            del monitoring_tasks[chat_id]
        except:
            pass
    
    # Clear state
    clear_queue(chat_id)
    if chat_id in current_playing:
        file_path = current_playing[chat_id].get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        del current_playing[chat_id]
    
    if chat_id in stream_started:
        del stream_started[chat_id]
    
    # Leave call
    try:
        await pytgcalls.leave_call(chat_id)
    except:
        pass
    
    await message.reply("⏹️ **Stopped and cleared queue**")

@app.on_message(filters.command("skip", config.COMMAND_PREFIXES) & filters.group)
@error
async def skip_command(client, message: Message):
    """Skip to next song"""
    if message.chat.id in current_playing and stream_started.get(message.chat.id):
        await message.reply("⏭️ **Skipping...**")
        await play_next(message.chat.id, send_message=True, force_skip=True)
    else:
        await message.reply("❌ **Nothing playing!**")

@app.on_message(filters.command("queue", config.COMMAND_PREFIXES) & filters.group)
@error
async def queue_command(client, message: Message):
    """Show current queue"""
    queue = get_queue(message.chat.id)
    if not queue and message.chat.id not in current_playing:
        await message.reply("📭 **Queue is empty!**")
        return
    
    text = "🎵 **Current Queue:**\n\n"
    if message.chat.id in current_playing:
        text += f"▶️ **Now:** {current_playing[message.chat.id]['title']}\n\n"
    
    if queue:
        for i, song in enumerate(queue, 1):
            text += f"{i}. {song['title']}\n"
    else:
        text += "No songs in queue"
    
    await message.reply(text)

@app.on_message(filters.command("pause", config.COMMAND_PREFIXES) & filters.group)
@error
async def pause_command(client, message: Message):
    """Pause playback"""
    try:
        await pytgcalls.pause_stream(message.chat.id)
        await message.reply("⏸️ **Paused**")
    except Exception as e:
        await message.reply(f"❌ {str(e)[:100]}")

@app.on_message(filters.command("resume", config.COMMAND_PREFIXES) & filters.group)
@error
async def resume_command(client, message: Message):
    """Resume playback"""
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("▶️ **Resumed**")
    except Exception as e:
        await message.reply(f"❌ {str(e)[:100]}")

# ==========================================
# 🎵 MODULE INFO
# ==========================================
__module__ = "Music"
__help__ = """
**🎵 Music Player Commands:**

• `/play <song>` - Play song (name or YouTube URL)
• `/pause` - Pause current playback
• `/resume` - Resume paused playback  
• `/skip` - Skip to next song
• `/stop` - Stop playback and clear queue
• `/queue` - Show current queue

**✨ Features:**
• **Reliable Download** - Downloads first for stability
• **Auto-converts** to MP3 (192kbps)
• **Smart Queue** - Auto-plays next song
• **Interactive Controls** - Pause, skip, stop buttons
• **Auto-cleanup** - Removes files after playback
• **Auto-join** - Userbot joins automatically
• **Error Recovery** - Multiple retry attempts

**⚠️ Requirements:**
• Voice chat must be **active** (turned ON)
• At least one person in the voice chat
• Bot needs admin rights for userbot invite

**🔧 Troubleshooting:**
If playback fails:
1. Make sure voice chat is ON
2. Have someone join the VC
3. Check if cookies are fresh
4. Try `/play` again
"""

print("✅ Music Player Commands Loaded (FIXED VERSION)")
