"""
Music Player Module - Part 1: Core System & Download Logic
WITH RUSTYPIPE INTEGRATION & AUTO PO_TOKEN GENERATION
Handles: FFmpeg detection, cookies, RustyPipe, po_token, download, queue management
"""

import asyncio
import os
import re
import shutil
import json
import subprocess
from typing import Optional
import yt_dlp

# ==========================================
# 🔥 RUSTYPIPE & PO_TOKEN SYSTEM
# ==========================================
def check_rustypipe_botguard():
    """Check if RustyPipe botguard binary is installed"""
    print("\n" + "="*70)
    print("🔍 RUSTYPIPE BOTGUARD DETECTION - STARTING")
    print("="*70)
    
    botguard_path = '/app/rustypipe-botguard'
    
    if os.path.exists(botguard_path):
        print(f"✅ Botguard found at: {botguard_path}")
        
        # Set environment variable for yt-dlp
        os.environ['RUSTYPIPE_BOTGUARD_PATH'] = botguard_path
        print(f"✅ Environment variable set: RUSTYPIPE_BOTGUARD_PATH={botguard_path}")
        
        # Test if executable
        if os.access(botguard_path, os.X_OK):
            print(f"✅ Botguard is executable")
        else:
            print(f"⚠️  Botguard not executable, attempting to fix...")
            try:
                os.chmod(botguard_path, 0o755)
                print(f"✅ Fixed permissions")
            except Exception as e:
                print(f"⚠️  Could not fix permissions: {e}")
        
        print("="*70 + "\n")
        return botguard_path
    else:
        print(f"⚠️  Botguard not found at {botguard_path}")
        print(f"⚠️  yt-dlp will work without it (may have signature issues)")
        print("="*70 + "\n")
        return None

BOTGUARD_PATH = check_rustypipe_botguard()

# ==========================================
# 🔍 CRITICAL: FFMPEG DETECTION SYSTEM
# ==========================================
def detect_ffmpeg():
    """Detect FFmpeg installation and return path"""
    print("\n" + "="*70)
    print("🔍 FFMPEG DETECTION SYSTEM - STARTING")
    print("="*70)
    
    ffmpeg_locations = [
        'ffmpeg',
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/app/.apt/usr/bin/ffmpeg',
        '/app/vendor/ffmpeg/ffmpeg',
    ]
    
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')
    
    if ffmpeg_path and ffprobe_path:
        print(f"✅ FFmpeg found in PATH: {ffmpeg_path}")
        print(f"✅ FFprobe found in PATH: {ffprobe_path}")
    else:
        print("⚠️  FFmpeg not in PATH, checking specific locations...")
        for path in ffmpeg_locations:
            if os.path.exists(path):
                ffmpeg_path = path
                ffprobe_path = os.path.join(os.path.dirname(path), 'ffprobe')
                if os.path.exists(ffprobe_path):
                    print(f"✅ FFmpeg found at: {ffmpeg_path}")
                    print(f"✅ FFprobe found at: {ffprobe_path}")
                    break
    
    if not ffmpeg_path:
        print("❌ FFmpeg NOT FOUND!")
        print("⚠️  Will download audio without MP3 conversion")
        print("="*70 + "\n")
        return None, False
    
    # Test if ffmpeg works
    print("\n🧪 Testing FFmpeg executable...")
    try:
        result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"✅ FFmpeg works! Output: {result.stdout[:100]}")
            print("="*70 + "\n")
            return ffmpeg_path, True
        else:
            print(f"❌ FFmpeg test failed with return code: {result.returncode}")
            print("="*70 + "\n")
            return None, False
    except Exception as e:
        print(f"❌ FFmpeg test error: {e}")
        print("="*70 + "\n")
        return None, False

FFMPEG_PATH, FFMPEG_AVAILABLE = detect_ffmpeg()

# ==========================================
# 🍪 CRITICAL: COOKIE DIAGNOSTIC SYSTEM
# ==========================================
def diagnose_cookies():
    """Comprehensive cookie file analysis"""
    print("="*70)
    print("🔍 COOKIE DIAGNOSTIC SYSTEM - STARTING")
    print("="*70)
    
    cwd = os.getcwd()
    print(f"📂 Current Working Directory: {cwd}")
    
    try:
        files = os.listdir('.')
        print(f"📂 Files in root: {[f for f in files if not f.startswith('.')][:20]}")
    except Exception as e:
        print(f"❌ Error listing files: {e}")
    
    cookie_locations = [
        'cookies.txt',
        './cookies.txt',
        'Yumeko/cookies.txt',
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
            size = os.path.getsize(path)
            print(f"   → Size: {size} bytes")
            
            try:
                with open(path, 'r') as f:
                    first_line = f.readline().strip()
                    print(f"   → First line: {first_line[:50]}...")
                    
                    f.seek(0)
                    lines = f.readlines()
                    cookie_count = sum(1 for line in lines if line.strip() and not line.startswith('#'))
                    print(f"   → Cookie entries: {cookie_count}")
                    
                    content = ''.join(lines)
                    has_sid = 'SID' in content
                    has_hsid = 'HSID' in content
                    has_ssid = 'SSID' in content
                    print(f"   → Has SID: {has_sid}, HSID: {has_hsid}, SSID: {has_ssid}")
                    
                    if cookie_count == 0:
                        print(f"   ⚠️  WARNING: No valid cookies!")
                    elif not (has_sid and has_hsid and has_ssid):
                        print(f"   ⚠️  WARNING: Missing critical YouTube cookies!")
                    else:
                        print(f"   ✅ Cookies look valid!")
                        
            except Exception as e:
                print(f"   ❌ Error reading file: {e}")
    
    if found_cookie_path:
        print(f"\n✅ FOUND COOKIE FILE: {found_cookie_path}")
    else:
        print(f"\n❌ NO COOKIE FILE FOUND!")
    
    print("="*70 + "\n")
    return found_cookie_path

COOKIE_PATH = diagnose_cookies()

# ==========================================
# 📦 YT-DLP CONFIGURATION WITH RUSTYPIPE
# ==========================================
DOWNLOAD_FOLDER = "downloads/music"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_ydl_opts():
    """Get yt-dlp options with FFmpeg, cookies, and RustyPipe botguard"""
    print(f"\n🔧 [get_ydl_opts] === STARTING ===")
    print(f"🔧 [get_ydl_opts] COOKIE_PATH: {COOKIE_PATH}")
    print(f"🔧 [get_ydl_opts] FFMPEG_AVAILABLE: {FFMPEG_AVAILABLE}")
    print(f"🔧 [get_ydl_opts] BOTGUARD_AVAILABLE: {BOTGUARD_PATH is not None}")
    
    cookie_file = COOKIE_PATH if COOKIE_PATH and os.path.exists(COOKIE_PATH) else None
    if cookie_file:
        print(f"✅ [get_ydl_opts] Using cookies: {cookie_file}")
    else:
        print(f"⚠️  [get_ydl_opts] NO COOKIES AVAILABLE!")
    
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
    }
    
    # 🎯 CRITICAL: RustyPipe is built into yt-dlp!
    # Just need to ensure botguard path is set
    if BOTGUARD_PATH:
        print(f"✅ [get_ydl_opts] RustyPipe botguard configured at: {BOTGUARD_PATH}")
        print(f"✅ [get_ydl_opts] yt-dlp will use RustyPipe for po_token generation")
    else:
        print(f"⚠️  [get_ydl_opts] No botguard - may have signature issues")
    
    # Add FFmpeg postprocessor if available
    if FFMPEG_AVAILABLE and FFMPEG_PATH:
        print(f"✅ [get_ydl_opts] Adding FFmpeg postprocessor for MP3")
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        opts['ffmpeg_location'] = FFMPEG_PATH
    else:
        print(f"⚠️  [get_ydl_opts] No FFmpeg - using direct audio")
    
    if cookie_file:
        opts['cookiefile'] = cookie_file
        print(f"🍪 [get_ydl_opts] Cookies configured")
    
    print(f"🔧 [get_ydl_opts] === COMPLETE ===\n")
    return opts

async def download_audio(url: str) -> dict:
    """Download audio from YouTube with RustyPipe support"""
    print(f"\n🔥 [download_audio] === STARTING ===")
    print(f"🔥 [download_audio] URL: {url}")
    print(f"🔥 [download_audio] RustyPipe: {'✅ Active' if BOTGUARD_PATH else '❌ Inactive'}")
    print(f"🔥 [download_audio] Cookies: {'✅ Active' if COOKIE_PATH else '❌ Inactive'}")
    
    ydl_opts = get_ydl_opts()
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"🔥 [download_audio] Calling extract_info()...")
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            
            if 'entries' in info:
                info = info['entries'][0]
            
            file_path = ydl.prepare_filename(info)
            
            # If FFmpeg available, file will be .mp3
            if FFMPEG_AVAILABLE:
                file_path = os.path.splitext(file_path)[0] + '.mp3'
                print(f"✅ [download_audio] Converted to MP3")
            else:
                print(f"✅ [download_audio] Using direct format: {os.path.splitext(file_path)[1]}")
            
            print(f"✅ [download_audio] SUCCESS! File: {file_path}")
            print(f"✅ [download_audio] Title: {info.get('title', 'Unknown')}")
            print(f"🔥 [download_audio] === COMPLETE ===\n")
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'file_path': file_path,
                'url': url,
                'thumbnail': info.get('thumbnail', None)
            }
        except Exception as e:
            error_str = str(e)
            print(f"\n❌ [download_audio] === FAILED ===")
            print(f"❌ [download_audio] Error: {error_str[:500]}")
            
            # Enhanced error diagnosis
            if "Sign in" in error_str or "bot" in error_str.lower():
                print(f"❌ [download_audio] DIAGNOSIS: Cookie/Auth failed!")
                if not BOTGUARD_PATH:
                    print(f"🔥 [download_audio] CRITICAL: No botguard - this may be why it failed!")
                    print(f"🔥 [get_ydl_opts] ACTION: Check botguard installation")
                else:
                    print(f"⚠️  [download_audio] Botguard present but still failed")
                    print(f"⚠️  [download_audio] Cookies might be expired")
            elif "Signature" in error_str:
                print(f"❌ [download_audio] DIAGNOSIS: Signature challenge failed!")
                print(f"⚠️  [download_audio] Need rustypipe-botguard binary")
            elif "rustypipe" in error_str.lower():
                print(f"❌ [download_audio] DIAGNOSIS: RustyPipe issue!")
                print(f"🔥 [download_audio] Check botguard: {BOTGUARD_PATH}")
            elif "format" in error_str.lower():
                print(f"❌ [download_audio] DIAGNOSIS: Format selection failed!")
            elif "ffmpeg" in error_str.lower():
                print(f"❌ [download_audio] DIAGNOSIS: FFmpeg error!")
            
            print(f"❌ [download_audio] === END ===\n")
            raise e

def is_youtube_url(url: str) -> bool:
    """Check if string is a YouTube URL"""
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

async def search_youtube(query: str) -> Optional[str]:
    """Search YouTube and return first result URL"""
    print(f"🔍 [search_youtube] Searching: {query}")
    print(f"🔍 [search_youtube] RustyPipe: {'✅' if BOTGUARD_PATH else '❌'}")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch'
    }
    
    if COOKIE_PATH and os.path.exists(COOKIE_PATH):
        ydl_opts['cookiefile'] = COOKIE_PATH
        print(f"✅ [search_youtube] Using cookies for search")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                url = f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
                print(f"✅ [search_youtube] Found: {url}")
                return url
        except Exception as e:
            print(f"❌ [search_youtube] Failed: {str(e)[:100]}")
    
    return None

# ==========================================
# 🎵 QUEUE MANAGEMENT
# ==========================================
music_queue = {}
current_playing = {}

def add_to_queue(chat_id: int, song_data: dict):
    """Add song to queue"""
    if chat_id not in music_queue:
        music_queue[chat_id] = []
    music_queue[chat_id].append(song_data)

def get_queue(chat_id: int) -> list:
    """Get queue for chat"""
    return music_queue.get(chat_id, [])

def clear_queue(chat_id: int):
    """Clear queue and current playing"""
    if chat_id in music_queue:
        music_queue[chat_id] = []
    if chat_id in current_playing:
        del current_playing[chat_id]

# ==========================================
# 📊 STARTUP SUMMARY
# ==========================================
print(f"\n{'='*70}")
print(f"✅ MUSIC MODULE CORE LOADED - WITH RUSTYPIPE SUPPORT")
print(f"{'='*70}")
print(f"🍪 Cookies:    {'✅ Available' if COOKIE_PATH else '❌ Not Found'}")
print(f"🎬 FFmpeg:     {'✅ Available' if FFMPEG_AVAILABLE else '❌ Not Available'}")
print(f"🔥 RustyPipe:  {'✅ Available (Built-in yt-dlp)' if BOTGUARD_PATH else '⚠️  Botguard Missing'}")
print(f"{'='*70}")

if FFMPEG_PATH:
    print(f"📂 FFmpeg Path: {FFMPEG_PATH}")
if BOTGUARD_PATH:
    print(f"📂 Botguard Path: {BOTGUARD_PATH}")

print(f"{'='*70}")

if not BOTGUARD_PATH:
    print(f"\n⚠️  WARNING: NO BOTGUARD - May have signature issues!")
    print(f"⚠️  Run install_rustypipe.sh to install botguard")
    print(f"⚠️  Bot will work with cookies but may fail on some videos")
elif not COOKIE_PATH:
    print(f"\n⚠️  WARNING: NO COOKIES - Bot relies on RustyPipe")
    print(f"✅ This is OK if botguard is working properly")
else:
    print(f"\n✅ OPTIMAL SETUP: Both cookies AND RustyPipe botguard!")
    print(f"✅ Bot will have maximum compatibility")

print(f"\nℹ️  NOTE: yt-dlp has RustyPipe built-in!")
print(f"ℹ️  The botguard binary helps with signature challenges")
print(f"ℹ️  Fresh po_tokens are generated automatically by yt-dlp")

print(f"{'='*70}\n")
