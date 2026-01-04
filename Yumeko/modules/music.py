import asyncio
import os
import re
import stat
import shutil
import subprocess
import logging
import requests
from typing import Optional
from pyrogram import filters, Client
from pyrogram.types import Message

# ==========================================
# 🔧 CRITICAL: UNIVERSAL BINARY DOWNLOADER
# ==========================================
def setup_rustypipe():
    """
    Tries to download rustypipe-botguard from multiple possible mirrors/versions.
    """
    binary_name = "rustypipe-botguard"
    install_dir = os.path.join(os.getcwd(), "bin")
    target_path = os.path.join(install_dir, binary_name)
    
    # List of potential URLs (Main Repo, Botguard Repo, different versions)
    # We prioritize the MUSL version for Heroku
    URLS_TO_TRY = [
        # Main Rustypipe Repo (Most likely location for newer builds)
        "https://codeberg.org/ThetaDev/rustypipe/releases/download/v0.1.2/rustypipe-botguard-x86_64-unknown-linux-musl",
        "https://codeberg.org/ThetaDev/rustypipe/releases/download/v0.1.0/rustypipe-botguard-x86_64-unknown-linux-musl",
        # Original Botguard Repo (Try older versions if new ones fail)
        "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-x86_64-unknown-linux-musl",
        "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.0/rustypipe-botguard-x86_64-unknown-linux-musl",
        # Fallback to GNU if MUSL fails completely
        "https://codeberg.org/ThetaDev/rustypipe/releases/download/v0.1.2/rustypipe-botguard-x86_64-unknown-linux-gnu",
    ]

    if not os.path.exists(install_dir):
        os.makedirs(install_dir, exist_ok=True)

    # Add to PATH
    if install_dir not in os.environ["PATH"]:
        os.environ["PATH"] = install_dir + os.pathsep + os.environ["PATH"]
        print(f"✅ DEBUG: Added {install_dir} to PATH")

    # Check if we already have a working binary
    if os.path.exists(target_path):
        try:
            res = subprocess.run([target_path, "--version"], capture_output=True, text=True)
            if res.returncode == 0:
                print(f"✅ DEBUG: Existing binary verified: {res.stdout.strip()}")
                return # It works, no need to download
            else:
                print("⚠️ DEBUG: Existing binary broken. Deleting...")
                os.remove(target_path)
        except:
            os.remove(target_path)

    # Loop through URLs until one works
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    success = False
    for url in URLS_TO_TRY:
        print(f"⬇️ DEBUG: Trying {url}...")
        try:
            response = requests.get(url, stream=True, timeout=15, headers=headers)
            if response.status_code == 200:
                with open(target_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Make executable
                st = os.stat(target_path)
                os.chmod(target_path, st.st_mode | stat.S_IEXEC)
                
                # Test it
                res = subprocess.run([target_path, "--version"], capture_output=True, text=True)
                if res.returncode == 0:
                    print(f"✅ DEBUG: SUCCESS! Downloaded from {url}")
                    success = True
                    break
            else:
                print(f"⚠️ DEBUG: Failed with {response.status_code}")
        except Exception as e:
            print(f"❌ DEBUG: Error: {e}")
    
    if not success:
        print("❌ CRITICAL: All download attempts failed. Music playback may fail.")

# --- RUN SETUP ---
setup_rustypipe()

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

def get_ydl_opts():
    return {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'verbose': True,
        'quiet': False,
        'no_warnings': True,
        'extract_flat': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'prefer_ffmpeg': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web'],
                'skip': ['hls', 'dash'],
                'player_skip': ['js', 'configs', 'web']
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

async def download_audio(url: str) -> dict:
    ydl_opts = get_ydl_opts()
    print(f"🔍 DEBUG: Downloading {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, url, download=True)
        if 'entries' in info: info = info['entries'][0]
        file_path = ydl.prepare_filename(info)
        file_path = os.path.splitext(file_path)[0] + '.mp3'
        return {'title': info.get('title', 'Unknown'), 'duration': info.get('duration', 0), 'file_path': file_path, 'url': url}

def is_youtube_url(url: str) -> bool:
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

async def search_youtube(query: str) -> Optional[str]:
    with yt_dlp.YoutubeDL({'format': 'bestaudio', 'noplaylist': True, 'quiet': True, 'default_search': 'ytsearch'}) as ydl:
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
