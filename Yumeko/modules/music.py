import asyncio
import os
import re
import shutil
from typing import Optional
from datetime import datetime
from pyrogram import filters, Client
from pyrogram.types import Message

# ==========================================
# 🔍 CRITICAL: FFMPEG DETECTION SYSTEM
# ==========================================
def detect_ffmpeg():
    """
    Detect FFmpeg installation and return path
    """
    print("\n" + "="*60)
    print("🔍 FFMPEG DETECTION SYSTEM - STARTING")
    print("="*60)
    
    # Check common locations
    ffmpeg_locations = [
        'ffmpeg',  # In PATH
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/app/.apt/usr/bin/ffmpeg',  # Heroku buildpack location
        '/app/vendor/ffmpeg/ffmpeg',
    ]
    
    ffmpeg_path = None
    ffprobe_path = None
    
    # Method 1: Use shutil.which (checks PATH)
    ffmpeg_in_path = shutil.which('ffmpeg')
    ffprobe_in_path = shutil.which('ffprobe')
    
    if ffmpeg_in_path and ffprobe_in_path:
        print(f"✅ FFmpeg found in PATH: {ffmpeg_in_path}")
        print(f"✅ FFprobe found in PATH: {ffprobe_in_path}")
        return ffmpeg_in_path, True
    
    # Method 2: Check specific locations
    print("⚠️ FFmpeg not in PATH, checking specific locations...")
    for path in ffmpeg_locations:
        if os.path.exists(path):
            ffmpeg_path = path
            # Check for ffprobe in same directory
            ffprobe_path = os.path.join(os.path.dirname(path), 'ffprobe')
            if os.path.exists(ffprobe_path):
                print(f"✅ FFmpeg found at: {ffmpeg_path}")
                print(f"✅ FFprobe found at: {ffprobe_path}")
                return ffmpeg_path, True
    
    print("❌ FFmpeg NOT FOUND!")
    print("⚠️ Will download audio without MP3 conversion")
    print("="*60)
    print("🔍 FFMPEG DETECTION SYSTEM - COMPLETE")
    print("="*60 + "\n")
    
    return None, False

FFMPEG_PATH, FFMPEG_AVAILABLE = detect_ffmpeg()

# If FFmpeg is found, add its directory to PATH
if FFMPEG_AVAILABLE and FFMPEG_PATH:
    ffmpeg_dir = os.path.dirname(FFMPEG_PATH)
    current_path = os.environ.get('PATH', '')
    
    print(f"\n🔧 PATH MODIFICATION:")
    print(f"   FFmpeg directory: {ffmpeg_dir}")
    print(f"   Current PATH: {current_path[:200]}...")
    
    if ffmpeg_dir not in current_path:
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + current_path
        print(f"   ✅ Added to PATH")
    else:
        print(f"   ℹ️ Already in PATH")
    
    print(f"   New PATH: {os.environ['PATH'][:200]}...")
    
    # Verify ffmpeg is now accessible
    import subprocess
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"   ✅ FFmpeg is accessible via subprocess!")
        else:
            print(f"   ❌ FFmpeg subprocess test failed!")
    except Exception as e:
        print(f"   ❌ FFmpeg subprocess error: {e}")
    
    print()

# ==========================================
# 🔍 CRITICAL: COOKIE DIAGNOSTIC SYSTEM
# ==========================================
def diagnose_cookies():
    """
    Comprehensive cookie file analysis and testing
    """
    print("\n" + "="*60)
    print("🔍 COOKIE DIAGNOSTIC SYSTEM - STARTING")
    print("="*60)
    
    # 1. Check current directory
    cwd = os.getcwd()
    print(f"📁 Current Working Directory: {cwd}")
    
    # 2. List files in current directory
    try:
        files = os.listdir('.')
        print(f"📂 Files in root: {[f for f in files if not f.startswith('.')[:20]]}")
    except Exception as e:
        print(f"❌ Error listing files: {e}")
    
    # 3. Search for cookies.txt in multiple locations
    cookie_locations = [
        'cookies.txt',
        './cookies.txt',
        'Yumeko/cookies.txt',
        '../cookies.txt',
        os.path.join(cwd, 'cookies.txt'),
    ]
    
    found_cookie_path = None
    for path in cookie_locations:
        abs_path = os.path.abspath(path)
        exists = os.path.exists(path)
        print(f"🔍 Checking: {path}")
        print(f"   → Absolute: {abs_path}")
        print(f"   → Exists: {exists}")
        
        if exists:
            found_cookie_path = path
            # Check file size
            size = os.path.getsize(path)
            print(f"   → Size: {size} bytes")
            
            # Check file readability
            try:
                with open(path, 'r') as f:
                    first_line = f.readline().strip()
                    print(f"   → First line: {first_line[:50]}...")
                    
                    # Count cookie entries
                    f.seek(0)
                    lines = f.readlines()
                    cookie_count = sum(1 for line in lines if line.strip() and not line.startswith('#'))
                    print(f"   → Cookie entries: {cookie_count}")
                    
                    # Check for critical cookies
                    content = ''.join(lines)
                    has_sid = 'SID' in content
                    has_hsid = 'HSID' in content
                    has_ssid = 'SSID' in content
                    print(f"   → Has SID: {has_sid}")
                    print(f"   → Has HSID: {has_hsid}")
                    print(f"   → Has SSID: {has_ssid}")
                    
                    if cookie_count == 0:
                        print(f"   ⚠️ WARNING: No valid cookies found!")
                    elif not (has_sid and has_hsid and has_ssid):
                        print(f"   ⚠️ WARNING: Missing critical YouTube cookies!")
                    else:
                        print(f"   ✅ Cookies look valid!")
                        
            except Exception as e:
                print(f"   ❌ Error reading file: {e}")
    
    if found_cookie_path:
        print(f"\n✅ FOUND COOKIE FILE: {found_cookie_path}")
    else:
        print(f"\n❌ NO COOKIE FILE FOUND!")
        print(f"   Please create 'cookies.txt' in: {cwd}")
    
    print("="*60)
    print("🔍 COOKIE DIAGNOSTIC SYSTEM - COMPLETE")
    print("="*60 + "\n")
    
    return found_cookie_path

# RUN DIAGNOSTICS IMMEDIATELY
COOKIE_PATH = diagnose_cookies()

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
    print(f"\n🔧 [get_ydl_opts] === STARTING ===")
    print(f"🔧 [get_ydl_opts] COOKIE_PATH from startup: {COOKIE_PATH}")
    print(f"🔧 [get_ydl_opts] FFMPEG_AVAILABLE: {FFMPEG_AVAILABLE}")
    if FFMPEG_PATH:
        print(f"🔧 [get_ydl_opts] FFMPEG_PATH: {FFMPEG_PATH}")
    
    # Double-check cookie file exists NOW
    if COOKIE_PATH and os.path.exists(COOKIE_PATH):
        cookie_file = COOKIE_PATH
        print(f"✅ [get_ydl_opts] Using cookies: {cookie_file}")
        
        # Verify it's readable
        try:
            with open(cookie_file, 'r') as f:
                line_count = len(f.readlines())
                print(f"✅ [get_ydl_opts] Cookie file readable, {line_count} lines")
        except Exception as e:
            print(f"❌ [get_ydl_opts] Cookie file NOT readable: {e}")
            cookie_file = None
    else:
        cookie_file = None
        print(f"❌ [get_ydl_opts] NO COOKIES AVAILABLE!")
    
    opts = {
        # Simple format selection - prefer m4a audio for best compatibility
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
    }
    
    # Only add FFmpeg postprocessor if FFmpeg is available
    if FFMPEG_AVAILABLE and FFMPEG_PATH:
        print(f"✅ [get_ydl_opts] Adding FFmpeg postprocessor for MP3 conversion")
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        # Specify FFmpeg location - use the full path to the binary
        opts['ffmpeg_location'] = FFMPEG_PATH
        print(f"✅ [get_ydl_opts] Set ffmpeg_location to: {FFMPEG_PATH}")
    else:
        print(f"⚠️ [get_ydl_opts] FFmpeg not available - will use direct audio format")
    
    # Add cookies if available
    if cookie_file:
        opts['cookiefile'] = cookie_file
        print(f"✅ [get_ydl_opts] Added cookiefile to opts")
    else:
        print(f"⚠️ [get_ydl_opts] NO COOKIES - Will likely fail!")
    
    print(f"🔧 [get_ydl_opts] Final opts keys: {list(opts.keys())}")
    print(f"🔧 [get_ydl_opts] === COMPLETE ===\n")
    
    return opts

async def download_audio(url: str) -> dict:
    print(f"\n📥 [download_audio] === STARTING ===")
    print(f"📥 [download_audio] URL: {url}")
    
    ydl_opts = get_ydl_opts()
    print(f"📥 [download_audio] Got ydl_opts, creating YoutubeDL...")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"📥 [download_audio] Calling extract_info()...")
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            
            if 'entries' in info: 
                info = info['entries'][0]
                print(f"📥 [download_audio] Got playlist entry")
            
            file_path = ydl.prepare_filename(info)
            
            # If FFmpeg is available, the file will be .mp3
            # Otherwise, it will be the original format (usually .m4a or .webm)
            if FFMPEG_AVAILABLE:
                file_path = os.path.splitext(file_path)[0] + '.mp3'
                print(f"✅ [download_audio] Converted to MP3")
            else:
                print(f"✅ [download_audio] Using direct audio format: {os.path.splitext(file_path)[1]}")
            
            print(f"✅ [download_audio] SUCCESS! File: {file_path}")
            print(f"✅ [download_audio] Title: {info.get('title', 'Unknown')}")
            print(f"📥 [download_audio] === COMPLETE ===\n")
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'file_path': file_path,
                'url': url
            }
        except Exception as e:
            error_str = str(e)
            print(f"\n❌ [download_audio] === FAILED ===")
            print(f"❌ [download_audio] Error type: {type(e).__name__}")
            print(f"❌ [download_audio] Error message: {error_str[:500]}")
            
            # Analyze the error
            if "Sign in to confirm" in error_str or "bot" in error_str.lower():
                print(f"❌ [download_audio] DIAGNOSIS: Cookie authentication failed!")
                print(f"❌ [download_audio] Either cookies are expired or not being used")
            elif "Signature" in error_str:
                print(f"❌ [download_audio] DIAGNOSIS: Signature challenge failed!")
            elif "format" in error_str.lower():
                print(f"❌ [download_audio] DIAGNOSIS: Format selection failed!")
            elif "ffmpeg" in error_str.lower() or "ffprobe" in error_str.lower():
                print(f"❌ [download_audio] DIAGNOSIS: FFmpeg error!")
                print(f"❌ [download_audio] FFmpeg might not be properly installed")
            
            print(f"❌ [download_audio] === END ===\n")
            raise e

def is_youtube_url(url: str) -> bool:
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

async def search_youtube(query: str) -> Optional[str]:
    print(f"🔍 [search_youtube] Searching: {query}")
    
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'default_search': 'ytsearch'
    }
    
    # Add cookies if available
    if COOKIE_PATH and os.path.exists(COOKIE_PATH):
        ydl_opts['cookiefile'] = COOKIE_PATH
        print(f"🔍 [search_youtube] Using cookies for search")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                url = f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
                print(f"✅ [search_youtube] Found: {url}")
                return url
        except Exception as e:
            print(f"❌ [search_youtube] Search failed: {str(e)[:100]}")
    
    print(f"❌ [search_youtube] No results")
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

@app.on_message(filters.command("play", config.COMMAND_PREFIXES) & filters.group)
@error
@save
async def play_command(client, message: Message):
    print(f"\n🎵 [play_command] ========== COMMAND RECEIVED ==========")
    print(f"🎵 [play_command] Chat: {message.chat.id}")
    print(f"🎵 [play_command] User: {message.from_user.id}")
    
    if len(message.command) < 2:
        await message.reply("**Usage:** `/play <song name or URL>`")
        return
    
    query = message.text.split(maxsplit=1)[1]
    print(f"🎵 [play_command] Query: {query}")
    
    status_msg = await message.reply("🔍 **Searching...**")
    
    try:
        url = query if is_youtube_url(query) else await search_youtube(query)
        if not url:
            await status_msg.edit("❌ **No results found!**")
            return
        
        print(f"🎵 [play_command] URL: {url}")
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
                format_type = "MP3" if FFMPEG_AVAILABLE else "M4A/WebM"
                await status_msg.edit(f"▶️ **Playing ({format_type}):** {audio_data['title']}")
                asyncio.create_task(monitor_stream(message.chat.id, audio_data['file_path']))
            except Exception as e:
                await status_msg.edit(f"❌ **Error joining VC:** {str(e)}")
    except Exception as e:
        error_msg = str(e)
        print(f"❌ [play_command] ERROR: {error_msg[:200]}")
        
        if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            await status_msg.edit(
                "❌ **Cookie Authentication Failed!**\n\n"
                "Your cookies are either:\n"
                "• Expired\n"
                "• Invalid\n"
                "• Not found\n\n"
                "Check bot logs for cookie diagnostic info."
            )
        elif "ffmpeg" in error_msg.lower() or "ffprobe" in error_msg.lower():
            await status_msg.edit(
                "❌ **FFmpeg Error!**\n\n"
                "FFmpeg is not properly installed on the server.\n"
                "Please check your Aptfile and buildpack configuration."
            )
        else:
            await status_msg.edit(f"❌ **Error:** {error_msg[:150]}")

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

@app.on_message(filters.command("cookietest", config.COMMAND_PREFIXES) & filters.private)
async def cookie_test_command(client, message):
    """Manual cookie diagnostic trigger"""
    await message.reply("🔍 Running diagnostics...")
    diagnose_cookies()
    detect_ffmpeg()
    
    status = f"**Diagnostic Results:**\n\n"
    status += f"🍪 Cookies: {'✅ Found' if COOKIE_PATH else '❌ Not Found'}\n"
    status += f"🎬 FFmpeg: {'✅ Available' if FFMPEG_AVAILABLE else '❌ Not Available'}\n"
    if FFMPEG_PATH:
        status += f"📍 FFmpeg Path: `{FFMPEG_PATH}`\n"
    status += f"\nCheck bot logs for detailed diagnostic info!"
    
    await message.reply(status)

__module__ = "Music"
__help__ = """
**Music Player Commands:**

• `/play <song>` - Play a song (name or YouTube URL)
• `/stop` - Stop playing and clear queue
• `/skip` - Skip current song
• `/queue` - Show current queue
• `/cookietest` - Test cookie & FFmpeg configuration (DM only)

**Audio Format:**
• With FFmpeg: MP3 (192kbps)
• Without FFmpeg: M4A/WebM (direct from YouTube)

**Troubleshooting:**
If you get errors, check bot logs for diagnostic info.
"""

print(f"\n{'='*60}")
print(f"✅ MUSIC MODULE LOADED")
print(f"🍪 Cookies: {'✅ Available' if COOKIE_PATH else '❌ Not Found'}")
print(f"🎬 FFmpeg: {'✅ Available' if FFMPEG_AVAILABLE else '❌ Not Available'}")
if FFMPEG_PATH:
    print(f"📍 FFmpeg: {FFMPEG_PATH}")
print(f"{'='*60}\n")
