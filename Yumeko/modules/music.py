import asyncio
import os
import re
from typing import Optional
from pyrogram import filters, Client
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality
import yt_dlp
from Yumeko import app
from config import config
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error

# Create userbot client for voice chat
userbot = Client(
    "music_userbot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.USERBOT_SESSION
)

# Initialize PyTgCalls with USERBOT
pytgcalls = PyTgCalls(userbot)

# Queue system
music_queue = {}
current_playing = {}

# Download folder
DOWNLOAD_FOLDER = "downloads/music"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_ydl_opts():
    """Configure yt-dlp with automatic po_token generation"""
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'prefer_ffmpeg': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    return opts

async def download_audio(url: str) -> dict:
    """Download audio from YouTube using yt-dlp"""
    ydl_opts = get_ydl_opts()
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            
            if 'entries' in info:
                info = info['entries'][0]
            
            file_path = ydl.prepare_filename(info)
            file_path = os.path.splitext(file_path)[0] + '.mp3'
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'file_path': file_path,
                'thumbnail': info.get('thumbnail'),
                'url': url
            }
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

def is_youtube_url(url: str) -> bool:
    """Check if URL is a valid YouTube URL"""
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
    return bool(re.match(youtube_regex, url))

async def search_youtube(query: str) -> Optional[str]:
    """Search YouTube and return first result URL"""
    ydl_opts = {
        'format': 'bestaudio',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'extract_flat': True
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                return f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
        except Exception:
            pass
    return None

def add_to_queue(chat_id: int, song_data: dict):
    """Add song to queue"""
    if chat_id not in music_queue:
        music_queue[chat_id] = []
    music_queue[chat_id].append(song_data)

def get_queue(chat_id: int) -> list:
    """Get current queue"""
    return music_queue.get(chat_id, [])

def clear_queue(chat_id: int):
    """Clear queue for chat"""
    if chat_id in music_queue:
        music_queue[chat_id] = []
    if chat_id in current_playing:
        del current_playing[chat_id]

async def play_next(chat_id: int):
    """Play next song in queue"""
    queue = get_queue(chat_id)
    
    if not queue:
        try:
            await pytgcalls.leave_call(chat_id)
        except Exception:
            pass
        if chat_id in current_playing:
            del current_playing[chat_id]
        return
    
    next_song = queue.pop(0)
    current_playing[chat_id] = next_song
    
    try:
        await pytgcalls.play(
            chat_id,
            MediaStream(
                next_song['file_path'],
                audio_parameters=AudioQuality.HIGH
            )
        )
    except Exception:
        await play_next(chat_id)

@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    """Play music in voice chat"""
    
    if len(message.command) < 2:
        await message.reply(
            "**Usage:** `/play <YouTube URL or search query>`\n\n"
            "**Examples:**\n"
            "`/play shape of you`\n"
            "`/play https://youtu.be/...`"
        )
        return
    
    query = message.text.split(maxsplit=1)[1]
    status_msg = await message.reply("🔍 **Searching...**")
    
    try:
        if is_youtube_url(query):
            url = query
        else:
            url = await search_youtube(query)
            if not url:
                await status_msg.edit("❌ **No results found!**")
                return
        
        await status_msg.edit("⏬ **Downloading...**")
        
        audio_data = await download_audio(url)
        
        song_info = {
            'title': audio_data['title'],
            'url': url,
            'file_path': audio_data['file_path'],
            'requester': message.from_user.mention,
            'duration': audio_data.get('duration', 0)
        }
        
        if message.chat.id in current_playing:
            add_to_queue(message.chat.id, song_info)
            queue_position = len(get_queue(message.chat.id))
            await status_msg.edit(
                f"✅ **Added to queue at position #{queue_position}**\n\n"
                f"🎵 **Title:** {audio_data['title']}\n"
                f"👤 **Requested by:** {message.from_user.mention}"
            )
        else:
            current_playing[message.chat.id] = song_info
            await status_msg.edit("🎵 **Joining voice chat...**")
            
            try:
                await pytgcalls.play(
                    message.chat.id,
                    MediaStream(
                        audio_data['file_path'],
                        audio_parameters=AudioQuality.HIGH
                    )
                )
                
                duration_str = f"{audio_data['duration'] // 60}:{audio_data['duration'] % 60:02d}" if audio_data['duration'] else "Unknown"
                
                await status_msg.edit(
                    f"▶️ **Now Playing**\n\n"
                    f"🎵 **Title:** {audio_data['title']}\n"
                    f"⏱️ **Duration:** {duration_str}\n"
                    f"👤 **Requested by:** {message.from_user.mention}"
                )
                
                # Start monitoring for stream end
                asyncio.create_task(monitor_stream(message.chat.id, audio_data['file_path']))
                
            except Exception as e:
                error_msg = str(e).lower()
                
                if "no active" in error_msg or "group call" in error_msg:
                    await status_msg.edit("❌ **Please start a voice chat first!**")
                else:
                    await status_msg.edit(f"❌ **Error:** {str(e)}\n\nMake sure userbot is in the group!")
                
                if os.path.exists(audio_data['file_path']):
                    os.remove(audio_data['file_path'])
                if message.chat.id in current_playing:
                    del current_playing[message.chat.id]
                    
    except Exception as e:
        await status_msg.edit(f"❌ **Error:** {str(e)}")

async def monitor_stream(chat_id: int, file_path: str):
    """Monitor stream and play next when finished"""
    try:
        # Wait for the stream to finish
        while chat_id in current_playing:
            await asyncio.sleep(2)
            
            # Check if still playing
            try:
                # If we can't get stream info, it means it ended
                await pytgcalls.get_call(chat_id)
            except:
                break
        
        # Clean up file
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
        
        # Play next song
        await play_next(chat_id)
        
    except Exception:
        pass

@app.on_message(filters.command("skip", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def skip_command(client, message: Message):
    """Skip current song"""
    
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply("❌ **Nothing is playing!**")
        return
    
    current_song = current_playing.get(chat_id)
    if current_song:
        file_path = current_song.get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    
    queue = get_queue(chat_id)
    
    if not queue:
        await message.reply("⏭️ **Skipped! No more songs in queue.**")
        try:
            await pytgcalls.leave_call(chat_id)
        except Exception:
            pass
        if chat_id in current_playing:
            del current_playing[chat_id]
    else:
        await message.reply("⏭️ **Skipped! Playing next song...**")
        await play_next(chat_id)

@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def stop_command(client, message: Message):
    """Stop music and clear queue"""
    
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply("❌ **Nothing is playing!**")
        return
    
    current_song = current_playing.get(chat_id)
    if current_song:
        file_path = current_song.get('file_path')
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
    
    clear_queue(chat_id)
    
    try:
        await pytgcalls.leave_call(chat_id)
        await message.reply("⏹️ **Stopped and left voice chat!**")
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("pause", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def pause_command(client, message: Message):
    """Pause current song"""
    
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply("❌ **Nothing is playing!**")
        return
    
    try:
        await pytgcalls.pause_stream(chat_id)
        await message.reply("⏸️ **Paused!**")
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("resume", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def resume_command(client, message: Message):
    """Resume paused song"""
    
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply("❌ **Nothing is playing!**")
        return
    
    try:
        await pytgcalls.resume_stream(chat_id)
        await message.reply("▶️ **Resumed!**")
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("queue", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def queue_command(client, message: Message):
    """Show current queue"""
    
    chat_id = message.chat.id
    
    if chat_id not in current_playing:
        await message.reply("❌ **Nothing is playing!**")
        return
    
    current = current_playing[chat_id]
    queue = get_queue(chat_id)
    
    text = f"▶️ **Now Playing:**\n🎵 {current['title']}\n\n"
    
    if queue:
        text += "📝 **Queue:**\n"
        for i, song in enumerate(queue, 1):
            text += f"{i}. {song['title']}\n"
    else:
        text += "📝 **Queue is empty!**"
    
    await message.reply(text)

# Module info
__module__ = "Music"
__help__ = """**🎵 Music Player Commands:**

✧ /play <query or URL> - Play a song in voice chat
✧ /skip - Skip current song
✧ /pause - Pause current song
✧ /resume - Resume paused song
✧ /stop - Stop music and leave voice chat
✧ /queue - Show current queue

**Requirements:**
• Userbot must be in the group
• Voice chat must be active
• Bot uses auto po_token generation
"""
