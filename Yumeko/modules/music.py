import asyncio
import os
import re
import shutil
import subprocess
import requests
import zipfile
from typing import Optional
from pyrogram import filters, Client
from pyrogram.types import Message
import yt_dlp
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality
from Yumeko import app
from config import config
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error

# ==========================================
# 🔧 CRITICAL: INSTALL DENO (The "Brain")
# ==========================================
def setup_deno():
    """
    Installs Deno. This is REQUIRED to fix the 
    'No supported JavaScript runtime' error.
    """
    base_bin_dir = os.path.join(os.getcwd(), "bin")
    deno_path = os.path.join(base_bin_dir, "deno")
    
    if not os.path.exists(base_bin_dir):
        os.makedirs(base_bin_dir, exist_ok=True)

    # Add to PATH immediately
    if base_bin_dir not in os.environ["PATH"]:
        os.environ["PATH"] = base_bin_dir + os.pathsep + os.environ["PATH"]
        print(f"✅ DEBUG: Added {base_bin_dir} to PATH")

    # Check if Deno works
    if os.path.exists(deno_path):
        try:
            ver = subprocess.getoutput(f"{deno_path} --version")
            if "deno" in ver:
                print(f"✅ DEBUG: Deno is ready: {ver.split()[1]}")
                return
        except: pass

    print("⬇️ DEBUG: Downloading Deno (Essential for YouTube)...")
    try:
        # Download Deno v1.40.0 (Stable Linux)
        url = "https://github.com/denoland/deno/releases/download/v1.40.0/deno-x86_64-unknown-linux-gnu.zip"
        r = requests.get(url, stream=True, timeout=30)
        
        with open("deno.zip", "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        with zipfile.ZipFile("deno.zip", 'r') as z:
            z.extractall(base_bin_dir)
            
        os.chmod(deno_path, 0o755)
        print("✅ DEBUG: Deno Installed Successfully.")
    except Exception as e:
        print(f"❌ DEBUG: Deno Install Failed: {e}")
    finally:
        if os.path.exists("deno.zip"): os.remove("deno.zip")

# RUN SETUP
setup_deno()

# ==========================================
# 🎵 MUSIC CLIENT SETUP
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

def get_ydl_opts():
    # Check if cookies file exists
    cookie_path = "cookies.txt"
    if not os.path.exists(cookie_path):
        print("⚠️ WARNING: cookies.txt NOT FOUND! Upload it to fix 'Sign in' errors.")
    else:
        print(f"✅ DEBUG: Using cookies.txt for authentication.")

    opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'verbose': True,
        'quiet': False,
        'no_warnings': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
        
        # 🔥 CRITICAL: USE COOKIES FILE
        'cookiefile': cookie_path,
        
        # 🔥 CRITICAL: USE DENO RUNTIME
        # This fixes the 'No supported JavaScript runtime' error
        'js_runtimes': [('deno', os.path.join(os.getcwd(), 'bin', 'deno'))],
        
        'extractor_args': {
            'youtube': {
                'skip': ['hls', 'dash'],
                'player_skip': ['web'] # Don't skip JS, we have Deno now!
            }
        },
        
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    return opts

async def download_audio(url: str) -> dict:
    ydl_opts = get_ydl_opts()
    print(f"🔍 DEBUG: Downloading {url}")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            if 'entries' in info: info = info['entries'][0]
            
            file_path = ydl.prepare_filename(info)
            file_path = os.path.splitext(file_path)[0] + '.mp3'
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'file_path': file_path,
                'url': url
            }
        except Exception as e:
            print(f"❌ DOWNLOAD FAILED: {e}")
            raise e

# --- QUEUE & HELPERS ---

def is_youtube_url(url: str) -> bool:
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

async def search_youtube(query: str) -> Optional[str]:
    # Use cookies for search too
    cookie_path = "cookies.txt" if os.path.exists("cookies.txt") else None
    opts = {'format': 'bestaudio', 'noplaylist': True, 'quiet': True, 'default_search': 'ytsearch', 'cookiefile': cookie_path}
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                return f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
        except: pass
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
    except: await play_next(chat_id)

@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply("**Usage:** `/play <song>`")
        return
    
    query = message.text.split(maxsplit=1)[1]
    status_msg = await message.reply("🔍 **Searching...**")
    
    try:
        url = query if is_youtube_url(query) else await search_youtube(query)
        if not url:
            await status_msg.edit("❌ **No results found!**")
            return
        
        await status_msg.edit("⏬ **Downloading...**")
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
                await status_msg.edit(f"❌ **Error:** {e}")
    except Exception as e:
        await status_msg.edit(f"❌ **Error:** {str(e)}")

async def monitor_stream(chat_id: int, file_path: str):
    try:
        while chat_id in current_playing:
            await asyncio.sleep(2)
            try: await pytgcalls.get_call(chat_id)
            except: break
        if os.path.exists(file_path): os.remove(file_path)
        await play_next(chat_id)
    except: pass

@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
async def stop_command(client, message):
    clear_queue(message.chat.id)
    try: await pytgcalls.leave_call(message.chat.id)
    except: pass
    await message.reply("⏹️ **Stopped.**")

@app.on_message(filters.command("skip", config.COMMAND_PREFIXES) & filters.group)
async def skip_command(client, message):
    if message.chat.id in current_playing:
        await message.reply("⏭️ **Skipped!**")
        await play_next(message.chat.id)

__module__ = "Music"
__help__ = "/play, /skip, /stop"
