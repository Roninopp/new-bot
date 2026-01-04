import asyncio
import os
import re
import stat
import shutil
import subprocess
import logging
from typing import Optional
from pyrogram import filters, Client
from pyrogram.types import Message

# ==========================================
# 🔧 CRITICAL: SETUP BINARY BEFORE IMPORTS
# ==========================================
def setup_rustypipe():
    """
    Installs the Static MUSL binary.
    Runs BEFORE yt-dlp imports to ensure the plugin finds it.
    """
    binary_name = "rustypipe-botguard"
    install_dir = os.path.join(os.getcwd(), "bin")
    target_path = os.path.join(install_dir, binary_name)
    
    # 1. Setup PATH
    if not os.path.exists(install_dir):
        os.makedirs(install_dir, exist_ok=True)

    if install_dir not in os.environ["PATH"]:
        os.environ["PATH"] += os.pathsep + install_dir
        print(f"✅ DEBUG: Added {install_dir} to PATH")

    # 2. Force Re-Download if broken (Exec format error fix)
    need_download = True
    if os.path.exists(target_path):
        try:
            # Test run
            result = subprocess.run([target_path, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ DEBUG: Binary is valid: {result.stdout.strip()}")
                need_download = False
            else:
                print("⚠️ DEBUG: Binary is broken. Deleting...")
                os.remove(target_path)
        except OSError:
            print("⚠️ DEBUG: Binary cannot execute (Exec format error). Deleting...")
            os.remove(target_path)

    # 3. Download STATIC MUSL Version (Safest for Heroku)
    if need_download:
        print(f"⬇️ DEBUG: Downloading RustyPipe (MUSL Static Version)...")
        # This URL is the most compatible version
        url = "https://github.com/ThetaDev/rustypipe-botguard/releases/latest/download/rustypipe-botguard-x86_64-unknown-linux-musl"
        
        try:
            subprocess.run(["curl", "-L", "-o", target_path, url], check=True)
            st = os.stat(target_path)
            os.chmod(target_path, st.st_mode | stat.S_IEXEC)
            print(f"✅ DEBUG: Installed successfully.")
        except Exception as e:
            print(f"❌ DEBUG: Download failed: {e}")

# --- RUN SETUP NOW ---
setup_rustypipe()

# ==========================================
# 📦 NOW IMPORT YT-DLP
# ==========================================
import yt_dlp
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream, AudioQuality
from Yumeko import app
from config import config
from Yumeko.decorator.save import save
from Yumeko.decorator.errors import error

# ==========================================
# 🎵 MUSIC CLIENT SETUP
# ==========================================

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
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'verbose': True,
        'quiet': False,
        'no_warnings': True,
        'extract_flat': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'prefer_ffmpeg': True,
        
        # Force iOS to use the Token
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
    return opts

async def download_audio(url: str) -> dict:
    ydl_opts = get_ydl_opts()
    print(f"🔍 DEBUG: Starting download for: {url}")
    
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
            print(f"❌ DEBUG: Download failed: {str(e)}")
            raise Exception(f"Download failed: {str(e)}")

def is_youtube_url(url: str) -> bool:
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
    return bool(re.match(youtube_regex, url))

async def search_youtube(query: str) -> Optional[str]:
    ydl_opts = {'format': 'bestaudio', 'noplaylist': True, 'quiet': True, 'default_search': 'ytsearch', 'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                return f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
        except Exception:
            pass
    return None

def add_to_queue(chat_id: int, song_data: dict):
    if chat_id not in music_queue:
        music_queue[chat_id] = []
    music_queue[chat_id].append(song_data)

def get_queue(chat_id: int) -> list:
    return music_queue.get(chat_id, [])

def clear_queue(chat_id: int):
    if chat_id in music_queue:
        music_queue[chat_id] = []
    if chat_id in current_playing:
        del current_playing[chat_id]

async def play_next(chat_id: int):
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
            MediaStream(next_song['file_path'], audio_parameters=AudioQuality.HIGH)
        )
    except Exception:
        await play_next(chat_id)

@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    if len(message.command) < 2:
        await message.reply("**Usage:** `/play <song name>`")
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
            await status_msg.edit(f"✅ **Added to queue:** {audio_data['title']}")
        else:
            current_playing[message.chat.id] = song_info
            await status_msg.edit("🎵 **Joining voice chat...**")
            
            try:
                await pytgcalls.play(
                    message.chat.id,
                    MediaStream(audio_data['file_path'], audio_parameters=AudioQuality.HIGH)
                )
                await status_msg.edit(f"▶️ **Now Playing:** {audio_data['title']}")
                asyncio.create_task(monitor_stream(message.chat.id, audio_data['file_path']))
            except Exception as e:
                await status_msg.edit(f"❌ **Error:** {e}")
                
    except Exception as e:
        await status_msg.edit(f"❌ **Error:** {str(e)}")

async def monitor_stream(chat_id: int, file_path: str):
    try:
        while chat_id in current_playing:
            await asyncio.sleep(2)
            try:
                await pytgcalls.get_call(chat_id)
            except:
                break
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass
        await play_next(chat_id)
    except Exception:
        pass

@app.on_message(filters.command("skip", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def skip_command(client, message: Message):
    chat_id = message.chat.id
    if chat_id in current_playing:
        await message.reply("⏭️ **Skipped!**")
        await play_next(chat_id)
    else:
        await message.reply("❌ **Nothing playing.**")

@app.on_message(filters.command("stop", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def stop_command(client, message: Message):
    chat_id = message.chat.id
    clear_queue(chat_id)
    try:
        await pytgcalls.leave_call(chat_id)
        await message.reply("⏹️ **Stopped.**")
    except:
        await message.reply("❌ **Not connected.**")

@app.on_message(filters.command("pause", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def pause_command(client, message: Message):
    chat_id = message.chat.id
    try:
        await pytgcalls.pause_stream(chat_id)
        await message.reply("⏸️ **Paused!**")
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("resume", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def resume_command(client, message: Message):
    chat_id = message.chat.id
    try:
        await pytgcalls.resume_stream(chat_id)
        await message.reply("▶️ **Resumed!**")
    except Exception as e:
        await message.reply(f"❌ **Error:** {str(e)}")

@app.on_message(filters.command("queue", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def queue_command(client, message: Message):
    chat_id = message.chat.id
    current = current_playing.get(chat_id)
    if not current:
        await message.reply("❌ **Nothing playing.**")
        return
    
    queue = get_queue(chat_id)
    text = f"▶️ **Now Playing:**\n🎵 {current['title']}\n\n"
    if queue:
        text += "📝 **Queue:**\n" + "\n".join([f"{i}. {s['title']}" for i, s in enumerate(queue, 1)])
    else:
        text += "📝 **Queue is empty!**"
    await message.reply(text)

__module__ = "Music"
__help__ = """**🎵 Music Player**\n\n/play <song>\n/skip\n/stop"""
