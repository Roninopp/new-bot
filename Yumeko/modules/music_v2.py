"""
Music Player Module - Part 2: PyTgCalls Integration & Commands
Handles: Voice chat playback, commands, button callbacks
"""

import asyncio
import os
from pyrogram import filters, Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserAlreadyParticipant, ChatAdminRequired, UserNotParticipant
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality
from pytgcalls.exceptions import NoActiveGroupCall

# Import from Part 1
from Yumeko.modules.music import (
    FFMPEG_AVAILABLE,
    download_audio,
    search_youtube,
    is_youtube_url,
    add_to_queue,
    get_queue,
    clear_queue,
    music_queue,
    current_playing
)

from Yumeko import app
from config import config
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error

# ==========================================
# 🎵 PYTGCALLS CLIENT
# ==========================================
userbot = Client(
    "music_userbot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.USERBOT_SESSION
)

pytgcalls = PyTgCalls(userbot)

# Track monitoring tasks
monitoring_tasks = {}

# ==========================================
# 🎵 START USERBOT & PYTGCALLS
# ==========================================
async def start_music_services():
    """Start userbot and pytgcalls"""
    try:
        print("🎵 [start_music_services] Starting userbot...")
        await userbot.start()
        print("✅ [start_music_services] Userbot started!")
        
        print("🎵 [start_music_services] Starting pytgcalls...")
        await pytgcalls.start()
        print("✅ [start_music_services] PyTgCalls started!")
    except Exception as e:
        print(f"❌ [start_music_services] Failed to start: {e}")

# Start services
import asyncio
loop = asyncio.get_event_loop()
loop.create_task(start_music_services())

# ==========================================
# 🎵 AUTO-JOIN GROUP HELPER
# ==========================================
async def ensure_userbot_in_chat(chat_id: int, message: Message = None):
    """Ensure userbot is in the chat, join if not"""
    try:
        # Get userbot info
        userbot_me = await userbot.get_me()
        
        # Check if userbot is already in chat using bot's perspective
        try:
            member = await app.get_chat_member(chat_id, userbot_me.id)
            print(f"✅ [ensure_userbot_in_chat] Already in chat {chat_id}")
            return True
        except:
            pass
        
        # Not in chat, need to join
        print(f"🔄 [ensure_userbot_in_chat] Not in chat, attempting to join...")
        
        try:
            # Get chat info using bot
            chat = await app.get_chat(chat_id)
            
            # Try using existing invite link
            if hasattr(chat, 'invite_link') and chat.invite_link:
                print(f"🔗 [ensure_userbot_in_chat] Using existing invite link")
                await userbot.join_chat(chat.invite_link)
                await asyncio.sleep(2)
                return True
            
            # Create new invite link
            print(f"🔗 [ensure_userbot_in_chat] Creating new invite link")
            try:
                invite_link = await app.create_chat_invite_link(chat_id)
                await userbot.join_chat(invite_link.invite_link)
                await asyncio.sleep(2)
                print(f"✅ [ensure_userbot_in_chat] Successfully joined {chat_id}")
                return True
            except:
                # Fallback: export chat invite link
                invite_link = await app.export_chat_invite_link(chat_id)
                await userbot.join_chat(invite_link)
                await asyncio.sleep(2)
                print(f"✅ [ensure_userbot_in_chat] Successfully joined {chat_id}")
                return True
                
        except UserAlreadyParticipant:
            print(f"✅ [ensure_userbot_in_chat] Already participant")
            return True
        except ChatAdminRequired:
            print(f"❌ [ensure_userbot_in_chat] Bot needs admin rights to invite")
            return False
        except Exception as e:
            print(f"❌ [ensure_userbot_in_chat] Failed to join: {e}")
            return False
            
    except Exception as e:
        print(f"❌ [ensure_userbot_in_chat] Error: {e}")
        return False

# ==========================================
# 🎵 STREAM MONITOR (Alternative to event handler)
# ==========================================
async def monitor_stream(chat_id: int, file_path: str, duration: int):
    """Monitor stream and auto-play next song when finished"""
    print(f"🎵 [monitor_stream] Started monitoring chat {chat_id} for {duration}s")
    
    try:
        # Wait for song duration + 2 seconds buffer
        await asyncio.sleep(duration + 2)
        
        print(f"🎵 [monitor_stream] Stream ended in {chat_id}")
        
        # Clean up current file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ [monitor_stream] Deleted: {file_path}")
            except Exception as e:
                print(f"⚠️ [monitor_stream] Delete failed: {e}")
        
        # Play next song
        await play_next(chat_id)
        
    except asyncio.CancelledError:
        print(f"🎵 [monitor_stream] Monitoring cancelled for {chat_id}")
        # Clean up on cancel
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
    except Exception as e:
        print(f"❌ [monitor_stream] Error: {e}")

# ==========================================
# 🎵 PLAYBACK CONTROL
# ==========================================
async def play_next(chat_id: int, send_message: bool = True):
    """Play the next song in queue"""
    print(f"🎵 [play_next] Called for chat {chat_id}")
    
    # Cancel existing monitoring task if any
    if chat_id in monitoring_tasks:
        monitoring_tasks[chat_id].cancel()
        del monitoring_tasks[chat_id]
    
    queue = get_queue(chat_id)
    
    if not queue:
        print(f"🎵 [play_next] Queue empty, leaving in 3 seconds")
        
        # Send leaving message if requested
        if send_message:
            try:
                await app.send_message(
                    chat_id,
                    "👋 **Userbot Left The VC**\n\n"
                    "No songs or queue left. Use `/play` to start again!"
                )
            except Exception as e:
                print(f"⚠️ [play_next] Failed to send leave message: {e}")
        
        await asyncio.sleep(3)
        
        try:
            await pytgcalls.leave_call(chat_id)
            print(f"👋 [play_next] Left voice chat")
        except Exception as e:
            print(f"⚠️ [play_next] Failed to leave: {e}")
        
        if chat_id in current_playing:
            del current_playing[chat_id]
        return
    
    # Get next song
    next_song = queue.pop(0)
    current_playing[chat_id] = next_song
    
    print(f"🎵 [play_next] Playing: {next_song['title']}")
    
    try:
        await pytgcalls.play(
            chat_id,
            MediaStream(
                next_song['file_path'],
                audio_parameters=AudioQuality.HIGH
            )
        )
        
        # Start monitoring for this song
        task = asyncio.create_task(
            monitor_stream(chat_id, next_song['file_path'], next_song.get('duration', 180))
        )
        monitoring_tasks[chat_id] = task
        print(f"✅ [play_next] Started playing and monitoring")
        
        # Send now playing message
        if send_message:
            try:
                format_type = "MP3" if FFMPEG_AVAILABLE else "M4A"
                now_playing = (
                    f"**▶️ Now Playing ({format_type})**\n\n"
                    f"🎵 **Title:** {next_song['title']}\n"
                    f"👤 **Requested by:** {next_song['requester']}\n"
                    f"⏱️ **Duration:** {next_song['duration'] // 60}:{next_song['duration'] % 60:02d}"
                )
                await app.send_message(chat_id, now_playing)
            except Exception as e:
                print(f"⚠️ [play_next] Failed to send now playing: {e}")
        
    except Exception as e:
        print(f"❌ [play_next] Failed: {e}")
        # Clean up file
        if os.path.exists(next_song['file_path']):
            try:
                os.remove(next_song['file_path'])
            except:
                pass
        # Try next song
        await play_next(chat_id, send_message)

# ==========================================
# 🎵 COMMANDS
# ==========================================
@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    """Main play command"""
    print(f"\n🎵 [play_command] ========== RECEIVED ==========")
    print(f"🎵 [play_command] Chat: {message.chat.id}, User: {message.from_user.id}")
    
    # Check if query provided
    if len(message.command) < 2:
        await message.reply("**Usage:** `/play <song name or URL>`\n\n**Example:** `/play Believer`")
        return
    
    query = message.text.split(maxsplit=1)[1].strip()
    if not query:
        await message.reply("**Usage:** `/play <song name or URL>`\n\n**Example:** `/play Believer`")
        return
    
    print(f"🎵 [play_command] Query: {query}")
    
    status_msg = await message.reply(
        "```\n"
        "[░░░░░░░░░░] 0%\n"
        "⏳ Initializing...\n"
        "```"
    )
    
    try:
        # Ensure userbot is in chat
        await status_msg.edit(
            "```\n"
            "[█░░░░░░░░░] 10%\n"
            "🔄 Checking userbot...\n"
            "```"
        )
        
        if not await ensure_userbot_in_chat(message.chat.id, message):
            await status_msg.edit(
                "❌ **Failed to join chat!**\n\n"
                "**Possible reasons:**\n"
                "• Bot needs admin rights to create invite links\n"
                "• Group has restricted invite settings\n\n"
                "**Solution:** Manually add the userbot to this group."
            )
            return
        
        # Search
        await status_msg.edit(
            "```\n"
            "[██░░░░░░░░] 20%\n"
            "🔍 Searching YouTube...\n"
            "```"
        )
        
        url = query if is_youtube_url(query) else await search_youtube(query)
        if not url:
            await status_msg.edit("❌ **No results found!**")
            return
        
        # Download
        await status_msg.edit(
            "```\n"
            "[████░░░░░░] 40%\n"
            "⬇️ Downloading audio...\n"
            "```"
        )
        
        audio_data = await download_audio(url)
        
        # Processing
        await status_msg.edit(
            "```\n"
            "[███████░░░] 70%\n"
            "🎵 Processing...\n"
            "```"
        )
        
        song_info = {
            'title': audio_data['title'],
            'url': url,
            'file_path': audio_data['file_path'],
            'duration': audio_data['duration'],
            'requester': message.from_user.mention,
            'thumbnail': audio_data.get('thumbnail')
        }
        
        # Check if already playing
        if message.chat.id in current_playing:
            add_to_queue(message.chat.id, song_info)
            position = len(get_queue(message.chat.id))
            
            queue_msg = (
                f"**✅ Queued at #{position}**\n\n"
                f"🎵 **Title:** {audio_data['title']}\n"
                f"👤 **Requested by:** {message.from_user.mention}\n"
                f"⏱️ **Duration:** {audio_data['duration'] // 60}:{audio_data['duration'] % 60:02d}"
            )
            await status_msg.edit(queue_msg)
            print(f"✅ [play_command] Added to queue at position {position}")
        else:
            current_playing[message.chat.id] = song_info
            
            # Joining
            await status_msg.edit(
                "```\n"
                "[█████████░] 90%\n"
                "🎙️ Connecting to voice chat...\n"
                "```"
            )
            
            try:
                await pytgcalls.play(
                    message.chat.id,
                    MediaStream(
                        audio_data['file_path'],
                        audio_parameters=AudioQuality.HIGH
                    )
                )
                
                # Start monitoring for auto-next
                task = asyncio.create_task(
                    monitor_stream(message.chat.id, audio_data['file_path'], audio_data['duration'])
                )
                monitoring_tasks[message.chat.id] = task
                
                print(f"✅ [play_command] Started playing and monitoring!")
                
                # Now playing message
                format_type = "MP3" if FFMPEG_AVAILABLE else "M4A"
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
                    f"🎵 **Title:** {audio_data['title']}\n"
                    f"👤 **Requested by:** {message.from_user.mention}\n"
                    f"⏱️ **Duration:** {audio_data['duration'] // 60}:{audio_data['duration'] % 60:02d}"
                )
                
                if audio_data.get('thumbnail'):
                    try:
                        await status_msg.delete()
                        await message.reply_photo(
                            audio_data['thumbnail'],
                            caption=now_playing,
                            reply_markup=buttons
                        )
                    except:
                        await status_msg.edit(now_playing, reply_markup=buttons)
                else:
                    await status_msg.edit(now_playing, reply_markup=buttons)
                
            except NoActiveGroupCall:
                await status_msg.edit(
                    "❌ **No active voice chat!**\n\n"
                    "Please start a voice chat first."
                )
                if message.chat.id in current_playing:
                    del current_playing[message.chat.id]
            except Exception as e:
                error_str = str(e)
                print(f"❌ [play_command] VC join error: {error_str}")
                
                if message.chat.id in current_playing:
                    del current_playing[message.chat.id]
                
                if "No active" in error_str or "GROUPCALL" in error_str:
                    await status_msg.edit(
                        "❌ **No active voice chat!**\n\n"
                        "Please start a voice chat first."
                    )
                elif "ADMIN_REQUIRED" in error_str or "privilege" in error_str.lower():
                    await status_msg.edit(
                        "❌ **Permission error!**\n\n"
                        "Make sure userbot can join voice chats."
                    )
                else:
                    await status_msg.edit(f"❌ **Error:** `{error_str[:150]}`")
                
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [play_command] Error: {error_msg[:200]}")
        
        if "Sign in" in error_msg or "bot" in error_msg.lower():
            await status_msg.edit(
                "❌ **Cookie Authentication Failed!**\n\n"
                "Cookies are expired or invalid."
            )
        elif "ffmpeg" in error_msg.lower():
            await status_msg.edit("❌ **FFmpeg Error!**")
        else:
            await status_msg.edit(f"❌ **Error:** `{error_msg[:150]}`")

# Button handlers
@app.on_callback_query(filters.regex(r"^(pause|skip|stop|queue|close)"))
async def button_handler(client, query: CallbackQuery):
    """Handle button callbacks"""
    action = query.data.split("_")[0]
    
    if action == "close":
        await query.message.delete()
        return
    
    chat_id = int(query.data.split("_")[1])
    
    if action == "skip":
        if chat_id in current_playing:
            await query.answer("⏭️ Skipping...", show_alert=False)
            await play_next(chat_id, send_message=True)
        else:
            await query.answer("❌ Nothing playing!", show_alert=True)
    
    elif action == "stop":
        # Cancel monitoring
        if chat_id in monitoring_tasks:
            monitoring_tasks[chat_id].cancel()
            del monitoring_tasks[chat_id]
        
        clear_queue(chat_id)
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
            await query.answer("🔭 Queue empty!", show_alert=True)
            return
        
        text = "🎵 **Queue:**\n\n"
        if chat_id in current_playing:
            text += f"▶️ {current_playing[chat_id]['title'][:40]}\n\n"
        
        for i, song in enumerate(queue, 1):
            text += f"{i}. {song['title'][:40]}\n"
        
        await query.answer(text[:200], show_alert=True)
    
    elif action == "pause":
        try:
            await pytgcalls.pause_stream(chat_id)
            await query.answer("⏸️ Paused", show_alert=False)
        except:
            await query.answer("❌ Error!", show_alert=True)

@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
async def stop_command(client, message):
    """Stop playback"""
    # Cancel monitoring
    if message.chat.id in monitoring_tasks:
        monitoring_tasks[message.chat.id].cancel()
        del monitoring_tasks[message.chat.id]
    
    clear_queue(message.chat.id)
    try:
        await pytgcalls.leave_call(message.chat.id)
    except:
        pass
    await message.reply("⏹️ **Stopped**")

@app.on_message(filters.command("skip", config.COMMAND_PREFIXES) & filters.group)
async def skip_command(client, message):
    """Skip to next song"""
    if message.chat.id in current_playing:
        await message.reply("⏭️ **Skipped!**")
        await play_next(message.chat.id, send_message=True)
    else:
        await message.reply("❌ **Nothing playing!**")

@app.on_message(filters.command("queue", config.COMMAND_PREFIXES) & filters.group)
async def queue_command(client, message):
    """Show queue"""
    queue = get_queue(message.chat.id)
    if not queue and message.chat.id not in current_playing:
        await message.reply("🔭 **Queue is empty!**")
        return
    
    text = "🎵 **Current Queue:**\n\n"
    if message.chat.id in current_playing:
        text += f"▶️ **Now:** {current_playing[message.chat.id]['title']}\n\n"
    
    for i, song in enumerate(queue, 1):
        text += f"{i}. {song['title']}\n"
    
    await message.reply(text)

@app.on_message(filters.command("pause", config.COMMAND_PREFIXES) & filters.group)
async def pause_command(client, message):
    """Pause playback"""
    try:
        await pytgcalls.pause_stream(message.chat.id)
        await message.reply("⏸️ **Paused**")
    except Exception as e:
        await message.reply(f"❌ {str(e)[:100]}")

@app.on_message(filters.command("resume", config.COMMAND_PREFIXES) & filters.group)
async def resume_command(client, message):
    """Resume playback"""
    try:
        await pytgcalls.resume_stream(message.chat.id)
        await message.reply("▶️ **Resumed**")
    except Exception as e:
        await message.reply(f"❌ {str(e)[:100]}")

__module__ = "Music"
__help__ = """
**🎵 Music Player:**

• `/play <song>` - Play song (name or URL)
• `/pause` - Pause playback
• `/resume` - Resume playback  
• `/skip` - Skip to next
• `/stop` - Stop and clear queue
• `/queue` - Show queue

**Features:**
• Auto-converts to MP3 (192kbps)
• Queue system with auto-play
• Interactive controls
• Auto-cleanup after playback
• Leaves VC after 3s when queue empty
• Auto-joins new groups

**Note:** Voice chat must be active!
"""

print("✅ Music Player Commands Loaded")
