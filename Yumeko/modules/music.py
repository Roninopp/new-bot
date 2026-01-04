import asyncio
import os
import re
from typing import Optional
from pyrogram import filters, Client
from pyrogram.types import Message

# ==========================================
# 📦 IMPORTS
# ==========================================
import yt_dlp
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality
from Yumeko import app
from config import config
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error

# ==========================================
# 🎵 MUSIC CLIENT
# ==========================================

userbot = Client(
    "music_userbot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.USERBOT_SESSION
)

pytgcalls = PyTgCalls(userbot)

music_queue = {}
current_playing = {}

DOWNLOAD_FOLDER = "downloads/music"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# 🔥 COOKIE STORAGE (set via /setcookie command)
YOUTUBE_COOKIES = None

def get_ydl_opts():
    print(f"🔍 [get_ydl_opts] Function called!")
    
    # Check for cookies file
    cookie_path = "cookies.txt"
    if not os.path.exists(cookie_path):
        print(f"⚠️ [get_ydl_opts] cookies.txt NOT FOUND!")
        cookie_path = None
    else:
        print(f"✅ [get_ydl_opts] Using cookies from {cookie_path}")
    
    opts = {
        # 🔥 CRITICAL: Use format that doesn't require signature solving
        # This works with cookies without needing Node.js challenges
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
        
        # Use Android client (doesn't require signature solving)
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'skip': ['webpage', 'configs'],
            }
        },
        
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    
    # Add cookies if available
    if cookie_path:
        opts['cookiefile'] = cookie_path
    
    print(f"✅ [get_ydl_opts] Config complete with Android client")
    return opts

async def download_audio(url: str) -> dict:
    print(f"🔍 [download_audio] Starting: {url}")
    
    ydl_opts = get_ydl_opts()
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"🔍 [download_audio] Extracting info...")
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            
            if 'entries' in info: 
                info = info['entries'][0]
            
            file_path = ydl.prepare_filename(info)
            file_path = os.path.splitext(file_path)[0] + '.mp3'
            
            print(f"✅ [download_audio] Success! File: {file_path}")
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'file_path': file_path,
                'url': url
            }
        except Exception as e:
            print(f"❌ [download_audio] FAILED: {str(e)[:200]}")
            raise e

def is_youtube_url(url: str) -> bool:
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

async def search_youtube(query: str) -> Optional[str]:
    ydl_opts = {'quiet': True, 'no_warnings': True, 'default_search': 'ytsearch'}
    if YOUTUBE_COOKIES:
        ydl_opts['cookiefile'] = YOUTUBE_COOKIES
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                return f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
        except: 
            pass
    return None

def add_to_queue(chat_id: int, song_data: dict):
    if chat_id not in music_queue: music_queue[chat_id] = []
    music_queue[chat_id].append(song_data)

def get_queue(chat_id: int) -> list:
    return music_queue.get(chat_id, [])

def clear_queue(chat_id: int):
    if chat_id in music_queue: music_queue[chat_id] = []
    if chat_id in current_playing: del current_playing[chat_id]

async def play_next(chat_id: int):
    queue = get_queue(chat_id)
    if not queue:
        try: await pytgcalls.leave_call(chat_id)
        except: pass
        if chat_id in current_playing: del current_playing[chat_id]
        return
    
    next_song = queue.pop(0)
    current_playing[chat_id] = next_song
    try:
        await pytgcalls.play(chat_id, MediaStream(next_song['file_path'], audio_parameters=AudioQuality.HIGH))
    except: 
        await play_next(chat_id)

@app.on_message(filters.command("setcookie", config.COMMAND_PREFIXES) & filters.private)
async def set_cookie_command(client, message: Message):
    """Set YouTube cookies file path. Reply to a message with the cookies.txt file."""
    global YOUTUBE_COOKIES
    
    if message.reply_to_message and message.reply_to_message.document:
        # Download the cookies file
        file_path = await message.reply_to_message.download(file_name="cookies/youtube_cookies.txt")
        YOUTUBE_COOKIES = file_path
        await message.reply(f"✅ **Cookies set!** File: `{file_path}`\n\nMusic should now work without bot detection.")
    else:
        await message.reply(
            "**Usage:** Reply to a cookies.txt file with `/setcookie`\n\n"
            "**How to get cookies:**\n"
            "1. Install browser extension 'Get cookies.txt LOCALLY'\n"
            "2. Go to youtube.com while logged in\n"
            "3. Click extension → Export cookies.txt\n"
            "4. Send file here and reply with /setcookie"
        )

@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    print(f"🎵 [play_command] Command received in chat {message.chat.id}")
    
    if len(message.command) < 2:
        await message.reply("**Usage:** `/play <song name or URL>`")
        return
    
    query = message.text.split(maxsplit=1)[1]
    status_msg = await message.reply("🔍 **Searching...**")
    
    try:
        url = query if is_youtube_url(query) else await search_youtube(query)
        if not url:
            await status_msg.edit("❌ **No results found!**")
            return
        
        await status_msg.edit("⬇️ **Downloading...**")
        audio_data = await download_audio(url)
        
        song_info = {
            'title': audio_data['title'],
            'url': url,
            'file_path': audio_data['file_path'],
            'requester': message.from_user.mention
        }
        
        if message.chat.id in current_playing:
            add_to_queue(message.chat.id, song_info)
            await status_msg.edit(f"✅ **Queued:** {audio_data['title']}")
        else:
            current_playing[message.chat.id] = song_info
            await status_msg.edit("🎵 **Joining VC...**")
            try:
                await pytgcalls.play(message.chat.id, MediaStream(audio_data['file_path'], audio_parameters=AudioQuality.HIGH))
                await status_msg.edit(f"▶️ **Playing:** {audio_data['title']}")
                asyncio.create_task(monitor_stream(message.chat.id, audio_data['file_path']))
            except Exception as e:
                await status_msg.edit(f"❌ **Error joining VC:** {str(e)}")
    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            await status_msg.edit(
                "❌ **Bot Detection Error!**\n\n"
                "YouTube is blocking requests. To fix:\n"
                "1. Get YouTube cookies (see /setcookie)\n"
                "2. Or try again in a few minutes"
            )
        else:
            await status_msg.edit(f"❌ **Error:** {error_msg[:200]}")

async def monitor_stream(chat_id: int, file_path: str):
    try:
        while chat_id in current_playing:
            await asyncio.sleep(2)
            try: 
                await pytgcalls.get_call(chat_id)
            except: 
                break
        if os.path.exists(file_path): 
            os.remove(file_path)
        await play_next(chat_id)
    except: 
        pass

@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
async def stop_command(client, message):
    clear_queue(message.chat.id)
    try: 
        await pytgcalls.leave_call(message.chat.id)
    except: 
        pass
    await message.reply("⏹️ **Stopped.**")

@app.on_message(filters.command("skip", config.COMMAND_PREFIXES) & filters.group)
async def skip_command(client, message):
    if message.chat.id in current_playing:
        await message.reply("⏭️ **Skipped!**")
        await play_next(message.chat.id)

@app.on_message(filters.command("queue", config.COMMAND_PREFIXES) & filters.group)
async def queue_command(client, message):
    queue = get_queue(message.chat.id)
    if not queue and message.chat.id not in current_playing:
        await message.reply("📭 **Queue is empty!**")
        return
    
    text = "🎵 **Current Queue:**\n\n"
    if message.chat.id in current_playing:
        text += f"▶️ **Now:** {current_playing[message.chat.id]['title']}\n\n"
    
    for i, song in enumerate(queue, 1):
        text += f"{i}. {song['title']}\n"
    
    await message.reply(text)

__module__ = "Music"
__help__ = """
**Music Player Commands:**

• `/play <song>` - Play a song (name or YouTube URL)
• `/stop` - Stop playing and clear queue
• `/skip` - Skip current song
• `/queue` - Show current queue
• `/setcookie` - Set YouTube cookies (owner only, DM)

**Note:** If bot detection occurs, use `/setcookie` with YouTube cookies.
"""

print("✅ Music module loaded with cookie support!")
