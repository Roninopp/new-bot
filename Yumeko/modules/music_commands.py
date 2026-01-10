"""
Music Player Module - Part 2B: Commands & Callbacks
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
    stream_from_url,
    play_next,
    send_now_playing,
    monitoring_tasks,
    stream_started
)

from Yumeko import app
from config import config
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error

# ==========================================
# 🎵 ENHANCED PLAY COMMAND (FAST MODE)
# ==========================================
@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    """
    Enhanced play command with:
    - Fast streaming (direct URL when possible)
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
        
        # Step 2: Search YouTube (FAST - no download yet)
        await status_msg.edit(
            "```\n"
            "[████░░░░░░] 40%\n"
            "🔍 Searching YouTube...\n"
            "```"
        )
        
        url = query if is_youtube_url(query) else await search_youtube(query)
        if not url:
            await status_msg.edit("❌ **No results found!**")
            return
        
        # Step 3: Get video info WITHOUT downloading
        await status_msg.edit(
            "```\n"
            "[██████░░░░] 60%\n"
            "📊 Fetching video info...\n"
            "```"
        )
        
        # Quick info fetch (use yt-dlp extract_info with download=False)
        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True  # Don't download, just get info
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                thumbnail = info.get('thumbnail')
                
                # Get best audio URL for direct streaming
                formats = info.get('formats', [])
                audio_url = None
                for fmt in formats:
                    if fmt.get('acodec') != 'none' and fmt.get('vcodec') == 'none':
                        audio_url = fmt.get('url')
                        break
                
                if not audio_url:
                    audio_url = url  # Fallback to video URL
        
        except Exception as e:
            print(f"⚠️ [play_command] Info extraction failed: {e}, using fallback")
            title = query[:50]
            duration = 180
            thumbnail = None
            audio_url = url
        
        song_info = {
            'title': title,
            'url': url,
            'audio_url': audio_url,
            'file_path': None,  # Will be set if download needed
            'duration': duration,
            'requester': message.from_user.mention,
            'thumbnail': thumbnail
        }
        
        # Step 4: Check if already playing (queue it)
        if message.chat.id in current_playing and stream_started.get(message.chat.id):
            add_to_queue(message.chat.id, song_info)
            position = len(get_queue(message.chat.id))
            
            queue_msg = (
                f"**✅ Queued at #{position}**\n\n"
                f"🎵 **Title:** {title}\n"
                f"👤 **Requested by:** {message.from_user.mention}\n"
                f"⏱️ **Duration:** {duration // 60}:{duration % 60:02d}"
            )
            await status_msg.edit(queue_msg)
            print(f"✅ [play_command] Added to queue at position {position}")
            return
        
        # Step 5: Start streaming (FAST - try direct stream first)
        await status_msg.edit(
            "```\n"
            "[████████░░] 80%\n"
            "🎙️ Connecting to voice chat...\n"
            "```"
        )
        
        current_playing[message.chat.id] = song_info
        
        # Enhanced connection with multiple retry strategies
        connection_success = False
        last_error = None
        
        for attempt in range(3):
            try:
                if attempt > 0:
                    await status_msg.edit(f"🔄 **Retry {attempt}/3** - Refreshing connection...")
                    
                    # Progressive fixes
                    if attempt == 1:
                        # First retry: Leave and refresh
                        try:
                            await pytgcalls.leave_call(message.chat.id)
                        except:
                            pass
                        await userbot.get_chat(message.chat.id)
                        await asyncio.sleep(2)
                    
                    elif attempt == 2:
                        # Second retry: Re-verify userbot membership
                        await status_msg.edit("🔄 **Final attempt** - Re-verifying access...")
                        success, _ = await ensure_userbot_in_chat(message.chat.id, max_retries=2)
                        if not success:
                            raise Exception("Userbot lost chat access")
                        await asyncio.sleep(2)
                
                # Try direct streaming first (FAST)
                print(f"⚡ [play_command] Attempting direct stream (attempt {attempt + 1})")
                success, result = await stream_from_url(
                    message.chat.id, 
                    audio_url,  # Use direct audio URL
                    song_info
                )
                
                if success:
                    connection_success = True
                    print("✅ [play_command] Stream started successfully!")
                    break
                else:
                    last_error = result
                    raise Exception(result)
                
            except Exception as e:
                last_error = str(e)
                print(f"❌ [play_command] Attempt {attempt + 1} failed: {last_error}")
                
                # Check if it's a "no active call" error
                if any(x in last_error.lower() for x in ["no active", "groupcall", "call"]):
                    if attempt < 2:
                        continue  # Retry
                    else:
                        # Final attempt failed - give clear instruction
                        await status_msg.edit(
                            "❌ **No Active Voice Chat Detected**\n\n"
                            "**Steps to fix:**\n"
                            "1. Start the voice chat in this group\n"
                            "2. Someone must join the voice chat\n"
                            "3. Try `/play` command again\n\n"
                            "**Note:** Voice chat must be ON before playing music!"
                        )
                        
                        # Cleanup
                        if message.chat.id in current_playing:
                            del current_playing[message.chat.id]
                        return
                else:
                    # Other error - retry if attempts left
                    if attempt >= 2:
                        await status_msg.edit(
                            f"❌ **Playback Error**\n\n"
                            f"**Error:** `{last_error[:100]}`\n\n"
                            "Try again or contact support."
                        )
                        if message.chat.id in current_playing:
                            del current_playing[message.chat.id]
                        return
        
        # Success - show now playing
        if connection_success:
            await status_msg.edit(
                "```\n"
                "[██████████] 100%\n"
                "✅ Stream started!\n"
                "```"
            )
            
            await asyncio.sleep(1)
            
            format_type = "MP3" if FFMPEG_AVAILABLE else "Stream"
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
                f"**▶️ Now Playing ({format_type})**\n\n"
                f"🎵 **Title:** {title}\n"
                f"👤 **Requested by:** {message.from_user.mention}\n"
                f"⏱️ **Duration:** {duration // 60}:{duration % 60:02d}"
            )
            
            if thumbnail:
                try:
                    await status_msg.delete()
                    await message.reply_photo(
                        thumbnail,
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
@app.on_callback_query(filters.regex(r"^(pause|skip|stop|queue|close)"))
async def button_handler(client, query: CallbackQuery):
    """Handle control button presses"""
    action = query.data.split("_")[0]
    
    if action == "close":
        await query.message.delete()
        return
    
    chat_id = int(query.data.split("_")[1])
    
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
            await query.message.edit_text("⏹️ **Playback stopped**")
    
    elif action == "queue":
        queue = get_queue(chat_id)
        if not queue and chat_id not in current_playing:
            await query.answer("📭 Queue empty!", show_alert=True)
            return
        
        text = "🎵 **Queue:**\n\n"
        if chat_id in current_playing:
            text += f"▶️ {current_playing[chat_id]['title'][:35]}\n\n"
        
        for i, song in enumerate(queue[:10], 1):  # Show max 10
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
        await message.reply("⏭️ **Skipped!**")
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
• **Fast Streaming** - Starts within 3-5 seconds
• **Auto-converts** to MP3 (192kbps) when needed
• **Smart Queue** - Auto-plays next song
• **Interactive Controls** - Pause, skip, stop buttons
• **Auto-cleanup** - Removes files after playback
• **Auto-join** - Userbot joins automatically
• **Error Recovery** - Fixes "No Active Call" issues
• **RustyPipe Support** - Uses po_token & cookies

**⚠️ Requirements:**
• Voice chat must be **active** (turned ON)
• At least one person in the voice chat
• Bot needs admin rights for userbot invite

**🔧 Troubleshooting:**
If "No Active Call" error persists:
1. Make sure voice chat is ON
2. Have someone join the VC
3. Try `/play` again
"""

print("✅ Music Player Commands Loaded")
