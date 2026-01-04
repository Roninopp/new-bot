import asyncio
import os
import re
import stat
import shutil
import subprocess
import logging
import requests
import tarfile
from typing import Optional
from pyrogram import filters, Client
from pyrogram.types import Message

# ==========================================
# 🔧 CRITICAL: SETUP ENVIRONMENT (Node.js + Rustypipe)
# ==========================================
def setup_environment():
    """
    Sets up the entire environment:
    1. rustypipe-botguard (For PoTokens)
    2. node (For executing JS challenges)
    """
    base_bin_dir = os.path.join(os.getcwd(), "bin")
    if not os.path.exists(base_bin_dir):
        os.makedirs(base_bin_dir, exist_ok=True)

    # Add bin to PATH immediately so the rest of the script sees it
    if base_bin_dir not in os.environ["PATH"]:
        os.environ["PATH"] = base_bin_dir + os.pathsep + os.environ["PATH"]
        print(f"✅ DEBUG: Added {base_bin_dir} to PATH")

    # ---------------------------------------------------------
    # 1. SETUP RUSTYPIPE (The Token Generator)
    # ---------------------------------------------------------
    rustypipe_path = os.path.join(base_bin_dir, "rustypipe-botguard")
    if not os.path.exists(rustypipe_path):
        print("⬇️ DEBUG: Downloading Rustypipe...")
        # This is the Codeberg URL that worked in your logs
        url = "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-v0.1.2-x86_64-unknown-linux-gnu.tar.xz"
        try:
            r = requests.get(url, stream=True, timeout=20)
            if r.status_code == 200:
                with open("temp_rp.tar.xz", "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                with tarfile.open("temp_rp.tar.xz", "r:xz") as tar:
                    for member in tar.getnames():
                        if "rustypipe-botguard" in member and "api" not in member:
                            extracted = tar.extractfile(member)
                            with open(rustypipe_path, "wb") as out:
                                out.write(extracted.read())
                            break
                os.chmod(rustypipe_path, 0o755) # Make executable
                print("✅ DEBUG: Rustypipe Installed.")
            else:
                print(f"❌ DEBUG: Rustypipe download failed: {r.status_code}")
        except Exception as e:
            print(f"❌ DEBUG: Rustypipe Setup Failed: {e}")
        finally:
            if os.path.exists("temp_rp.tar.xz"): os.remove("temp_rp.tar.xz")

    # ---------------------------------------------------------
    # 2. SETUP NODE.JS (The Puzzle Solver - Fixes "No JS runtime")
    # ---------------------------------------------------------
    node_path = os.path.join(base_bin_dir, "node")
    # We check if 'node' works. If not, we download it.
    node_working = False
    try:
        if subprocess.run(["node", "-v"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            node_working = True
    except: pass

    if not node_working and not os.path.exists(node_path):
        print("⬇️ DEBUG: Downloading Node.js (Required for YouTube)...")
        # Downloading a standalone Linux binary for Node.js v18 (Stable)
        node_url = "https://nodejs.org/dist/v18.16.0/node-v18.16.0-linux-x64.tar.xz"
        try:
            r = requests.get(node_url, stream=True, timeout=30)
            if r.status_code == 200:
                with open("temp_node.tar.xz", "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                with tarfile.open("temp_node.tar.xz", "r:xz") as tar:
                    # Look for bin/node inside the archive
                    for member in tar.getnames():
                        if member.endswith("/bin/node"):
                            extracted = tar.extractfile(member)
                            with open(node_path, "wb") as out:
                                out.write(extracted.read())
                            break
                os.chmod(node_path, 0o755)
                print("✅ DEBUG: Node.js Installed manually.")
            else:
                 print(f"❌ DEBUG: Node.js download failed: {r.status_code}")
        except Exception as e:
            print(f"❌ DEBUG: Node.js Setup Failed: {e}")
        finally:
            if os.path.exists("temp_node.tar.xz"): os.remove("temp_node.tar.xz")

    # ---------------------------------------------------------
    # 3. VERIFICATION
    # ---------------------------------------------------------
    print("\n🔍 SYSTEM CHECK:")
    try:
        rp_ver = subprocess.getoutput(f"{rustypipe_path} --version") if os.path.exists(rustypipe_path) else "MISSING"
        print(f"   • Rustypipe: {rp_ver}")
    except: pass
    
    try:
        # We explicitly check the local bin node first
        node_ver = subprocess.getoutput(f"{node_path} --version") if os.path.exists(node_path) else subprocess.getoutput("node --version")
        print(f"   • Node.js:   {node_ver}")
    except: print("   • Node.js:   MISSING")
    print("-------------------------------------------\n")

# RUN SETUP NOW
setup_environment()

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
        
        # KEY SETTINGS
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'web'],
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
