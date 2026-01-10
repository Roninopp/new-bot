"""
Music Player Module - Part 2A: Core Streaming & PyTgCalls
Handles: Voice chat streaming, monitoring, auto-join, playback control
"""

import asyncio
import os
from pyrogram import Client
from pyrogram.errors import (
    UserAlreadyParticipant, 
    ChatAdminRequired, 
    UserNotParticipant, 
    RPCError
)
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality, StreamAudioEnded
from pytgcalls.exceptions import NoActiveGroupCall, GroupCallNotFound

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

# Track monitoring tasks & stream states
monitoring_tasks = {}
stream_started = {}  # Track if stream actually started

# ==========================================
# 🎵 START USERBOT & PYTGCALLS
# ==========================================
async def start_music_services():
    """Start userbot and pytgcalls with proper error handling"""
    try:
        print("🎵 [start_music_services] Starting userbot...")
        await userbot.start()
        print("✅ [start_music_services] Userbot started!")
        
        print("🎵 [start_music_services] Starting pytgcalls...")
        await pytgcalls.start()
        print("✅ [start_music_services] PyTgCalls started!")
        
        # Register stream ended handler
        @pytgcalls.on_stream_end()
        async def on_stream_end(client, update):
            """Auto-play next song when stream ends naturally"""
            chat_id = update.chat_id
            print(f"🎵 [on_stream_end] Stream ended in chat {chat_id}")
            
            # Clean up current file
            if chat_id in current_playing:
                file_path = current_playing[chat_id].get('file_path')
                if file_path and os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"🗑️ [on_stream_end] Deleted: {file_path}")
                    except Exception as e:
                        print(f"⚠️ [on_stream_end] Delete failed: {e}")
            
            # Play next song
            await play_next(chat_id, send_message=True, force_skip=False)
        
        print("✅ [start_music_services] Stream end handler registered!")
        
    except Exception as e:
        print(f"❌ [start_music_services] Failed to start: {e}")

# Start services
loop = asyncio.get_event_loop()
loop.create_task(start_music_services())

# ==========================================
# 🎵 AUTO-JOIN WITH RETRY LOGIC
# ==========================================
async def ensure_userbot_in_chat(chat_id: int, max_retries: int = 3):
    """
    Ensure userbot is in the chat with enhanced retry logic
    Returns: (success: bool, error_message: str or None)
    """
    for attempt in range(max_retries):
        try:
            # Get userbot info
            userbot_me = await userbot.get_me()
            
            # Check if already in chat
            try:
                member = await userbot.get_chat_member(chat_id, userbot_me.id)
                print(f"✅ [ensure_userbot_in_chat] Already in chat {chat_id}")
                
                # Force refresh chat cache to get updated call info
                await userbot.get_chat(chat_id)
                await asyncio.sleep(1)
                return True, None
            except UserNotParticipant:
                pass
            
            # Not in chat, attempt to join
            print(f"🔄 [ensure_userbot_in_chat] Attempt {attempt + 1}/{max_retries} to join chat {chat_id}")
            
            try:
                # Get chat info
                chat = await app.get_chat(chat_id)
                
                # Try existing invite link
                if hasattr(chat, 'invite_link') and chat.invite_link:
                    print(f"🔗 [ensure_userbot_in_chat] Using existing invite link")
                    await userbot.join_chat(chat.invite_link)
                    await asyncio.sleep(2)
                    
                    # Verify join and refresh cache
                    await userbot.get_chat(chat_id)
                    print(f"✅ [ensure_userbot_in_chat] Successfully joined {chat_id}")
                    return True, None
                
                # Create new invite link
                print(f"🔗 [ensure_userbot_in_chat] Creating new invite link")
                try:
                    invite_link = await app.create_chat_invite_link(chat_id)
                    await userbot.join_chat(invite_link.invite_link)
                except Exception:
                    # Fallback to export
                    invite_link = await app.export_chat_invite_link(chat_id)
                    await userbot.join_chat(invite_link)
                
                await asyncio.sleep(2)
                
                # Verify and refresh
                await userbot.get_chat(chat_id)
                print(f"✅ [ensure_userbot_in_chat] Successfully joined {chat_id}")
                return True, None
                
            except UserAlreadyParticipant:
                await userbot.get_chat(chat_id)
                return True, None
                
            except ChatAdminRequired:
                return False, "Bot needs admin rights to create invite links"
                
        except Exception as e:
            print(f"⚠️ [ensure_userbot_in_chat] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                return False, f"Failed after {max_retries} attempts: {str(e)}"
    
    return False, "Unknown error"

# ==========================================
# 🎵 DIRECT STREAM FROM URL (Fast Mode)
# ==========================================
async def stream_from_url(chat_id: int, url: str, song_info: dict):
    """
    Stream directly from URL without downloading (FAST)
    Falls back to download if streaming fails
    """
    try:
        print(f"⚡ [stream_from_url] Attempting direct stream for {chat_id}")
        
        # Try to stream directly
        await pytgcalls.play(
            chat_id,
            MediaStream(
                url,
                audio_parameters=AudioQuality.HIGH
            )
        )
        
        stream_started[chat_id] = True
        print(f"✅ [stream_from_url] Direct streaming started!")
        return True, None
        
    except Exception as e:
        print(f"⚠️ [stream_from_url] Direct stream failed: {e}")
        print(f"🔄 [stream_from_url] Falling back to download mode...")
        
        # Download and stream
        try:
            audio_data = await download_audio(url)
            
            await pytgcalls.play(
                chat_id,
                MediaStream(
                    audio_data['file_path'],
                    audio_parameters=AudioQuality.HIGH
                )
            )
            
            stream_started[chat_id] = True
            song_info['file_path'] = audio_data['file_path']
            song_info['duration'] = audio_data['duration']
            print(f"✅ [stream_from_url] Downloaded stream started!")
            return True, audio_data['file_path']
            
        except Exception as download_error:
            print(f"❌ [stream_from_url] Download stream also failed: {download_error}")
            return False, str(download_error)

# ==========================================
# 🎵 ENHANCED PLAY NEXT WITH FIX
# ==========================================
async def play_next(chat_id: int, send_message: bool = True, force_skip: bool = False):
    """Play next song with enhanced error handling"""
    print(f"🎵 [play_next] Called for chat {chat_id} (Force Skip: {force_skip})")
    
    # Cancel monitoring if force skip
    if force_skip and chat_id in monitoring_tasks:
        try:
            monitoring_tasks[chat_id].cancel()
            del monitoring_tasks[chat_id]
        except Exception:
            pass
    
    # Clean up current playing file
    if chat_id in current_playing:
        file_path = current_playing[chat_id].get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ [play_next] Deleted previous file: {file_path}")
            except Exception as e:
                print(f"⚠️ [play_next] Failed to delete: {e}")
    
    queue = get_queue(chat_id)
    
    if not queue:
        print(f"🎵 [play_next] Queue empty, leaving voice chat")
        
        if send_message:
            try:
                await app.send_message(
                    chat_id,
                    "👋 **Playback Finished**\n\n"
                    "Queue is empty. Use `/play` to start again!"
                )
            except Exception as e:
                print(f"⚠️ [play_next] Failed to send message: {e}")
        
        await asyncio.sleep(2)
        
        try:
            await pytgcalls.leave_call(chat_id)
            print(f"👋 [play_next] Left voice chat {chat_id}")
        except Exception as e:
            print(f"⚠️ [play_next] Leave call error: {e}")
        
        # Cleanup
        if chat_id in current_playing:
            del current_playing[chat_id]
        if chat_id in stream_started:
            del stream_started[chat_id]
        return
    
    # Get next song
    next_song = queue.pop(0)
    current_playing[chat_id] = next_song
    
    print(f"🎵 [play_next] Playing: {next_song['title']}")
    
    # Try to play with retry logic
    max_retries = 2
    for attempt in range(max_retries):
        try:
            # Refresh chat cache before playing
            if attempt > 0:
                print(f"🔄 [play_next] Refreshing chat cache (attempt {attempt + 1})")
                await userbot.get_chat(chat_id)
                await asyncio.sleep(1)
            
            # Stream from URL or file
            if next_song.get('file_path') and os.path.exists(next_song['file_path']):
                # Already downloaded
                await pytgcalls.play(
                    chat_id,
                    MediaStream(
                        next_song['file_path'],
                        audio_parameters=AudioQuality.HIGH
                    )
                )
                stream_started[chat_id] = True
            else:
                # Direct stream
                success, result = await stream_from_url(chat_id, next_song['url'], next_song)
                if not success:
                    raise Exception(result)
            
            print(f"✅ [play_next] Successfully started stream")
            
            # Send now playing message
            if send_message:
                await send_now_playing(chat_id, next_song)
            
            break  # Success, exit retry loop
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ [play_next] Attempt {attempt + 1} failed: {error_str}")
            
            if attempt < max_retries - 1:
                # Retry on specific errors
                if any(err in error_str for err in ["GROUPCALL", "NoActiveGroupCall", "call"]):
                    print(f"🔄 [play_next] Retrying due to call error...")
                    try:
                        await pytgcalls.leave_call(chat_id)
                    except:
                        pass
                    await asyncio.sleep(2)
                else:
                    break  # Don't retry on other errors
            else:
                # Final attempt failed
                print(f"❌ [play_next] All attempts failed, skipping to next")
                
                # Clean up failed file
                if next_song.get('file_path') and os.path.exists(next_song['file_path']):
                    try:
                        os.remove(next_song['file_path'])
                    except:
                        pass
                
                # Try next song recursively
                if get_queue(chat_id):
                    await play_next(chat_id, send_message, force_skip=False)
                return

async def send_now_playing(chat_id: int, song_info: dict):
    """Send now playing message with buttons"""
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    try:
        format_type = "MP3" if FFMPEG_AVAILABLE else "M4A"
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⏸ Pause", callback_data=f"pause_{chat_id}"),
                InlineKeyboardButton("⏭ Skip", callback_data=f"skip_{chat_id}"),
                InlineKeyboardButton("⏹ Stop", callback_data=f"stop_{chat_id}")
            ],
            [
                InlineKeyboardButton("📋 Queue", callback_data=f"queue_{chat_id}"),
                InlineKeyboardButton("❌ Close", callback_data="close")
            ]
        ])

        now_playing = (
            f"**▶️ Now Playing ({format_type})**\n\n"
            f"🎵 **Title:** {song_info['title']}\n"
            f"👤 **Requested by:** {song_info['requester']}\n"
            f"⏱️ **Duration:** {song_info.get('duration', 0) // 60}:{song_info.get('duration', 0) % 60:02d}"
        )
        
        if song_info.get('thumbnail'):
            await app.send_photo(
                chat_id,
                photo=song_info['thumbnail'],
                caption=now_playing,
                reply_markup=buttons
            )
        else:
            await app.send_message(chat_id, now_playing, reply_markup=buttons)

    except Exception as e:
        print(f"⚠️ [send_now_playing] Failed: {e}")

# Export functions for command handler
__all__ = [
    'userbot',
    'pytgcalls',
    'ensure_userbot_in_chat',
    'stream_from_url',
    'play_next',
    'send_now_playing',
    'monitoring_tasks',
    'stream_started'
]

print("✅ Music Core & Stream Manager Loaded") 
