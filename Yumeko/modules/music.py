"""
Music Player Module - Part 1: Core System & Download Logic
FIXED VERSION - Proper PoToken & RustyPipe Integration
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
# 🔥 CONFIGURATION
# ==========================================
DOWNLOAD_FOLDER = '/tmp/music_downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ==========================================
# 🔥 RUSTYPIPE BOTGUARD SYSTEM (FIXED)
# ==========================================
def check_and_setup_botguard():
    """
    Check if RustyPipe botguard binary is installed and working.
    yt-dlp needs rustypipe-botguard v1.x (NOT v0.1.x!)
    """
    print("\n" + "="*70)
    print("🔍 RUSTYPIPE BOTGUARD DETECTION - STARTING")
    print("="*70)
    
    botguard_path = '/app/rustypipe-botguard'
    
    if not os.path.exists(botguard_path):
        print(f"❌ Botguard not found at: {botguard_path}")
        print("="*70 + "\n")
        return None, False
    
    print(f"📂 Botguard file exists at: {botguard_path}")
    
    # Check if executable
    if not os.access(botguard_path, os.X_OK):
        print(f"⚠️  Botguard not executable, fixing permissions...")
        try:
            os.chmod(botguard_path, 0o755)
            print(f"✅ Fixed permissions")
        except Exception as e:
            print(f"❌ Could not fix permissions: {e}")
            return botguard_path, False
    
    # Test if binary actually works and check version
    try:
        result = subprocess.run(
            [botguard_path, '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        version_output = result.stdout.strip() or result.stderr.strip()
        print(f"📋 Botguard version output: {version_output}")
        
        if result.returncode == 0:
            # Check if it's v1.x (required by yt-dlp)
            if 'v1.' in version_output or '1.' in version_output:
                print(f"✅ Botguard v1.x detected - Compatible!")
                
                # Set environment variables
                os.environ['RUSTYPIPE_BOTGUARD_PATH'] = botguard_path
                print(f"✅ Environment variable set: RUSTYPIPE_BOTGUARD_PATH={botguard_path}")
                print("="*70 + "\n")
                return botguard_path, True
            else:
                print(f"⚠️  Botguard version may be incompatible (need v1.x)")
                print(f"⚠️  yt-dlp requires rustypipe-botguard v1.0.0 or newer")
                os.environ['RUSTYPIPE_BOTGUARD_PATH'] = botguard_path
                print("="*70 + "\n")
                return botguard_path, False  # Exists but may not work
        else:
            print(f"❌ Botguard binary failed to run (return code: {result.returncode})")
            print("="*70 + "\n")
            return botguard_path, False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Botguard timed out")
        print("="*70 + "\n")
        return botguard_path, False
    except Exception as e:
        print(f"❌ Could not test botguard: {e}")
        print("="*70 + "\n")
        return botguard_path, False

BOTGUARD_PATH, BOTGUARD_WORKING = check_and_setup_botguard()

# ==========================================
# 🔍 FFMPEG DETECTION SYSTEM
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
# 🍪 COOKIE DIAGNOSTIC SYSTEM
# ==========================================
def diagnose_cookies():
    """Comprehensive cookie file analysis"""
    print("="*70)
    print("🔍 COOKIE DIAGNOSTIC SYSTEM - STARTING")
    print("="*70)
    
    cwd = os.getcwd()
    print(f"📂 Current Working Directory: {cwd}")
    
    cookie_locations = [
        'cookies.txt',
        './cookies.txt',
        'Yumeko/cookies.txt',
        os.path.join(cwd, 'cookies.txt'),
        '/app/cookies.txt',
    ]
    
    found_cookie_path = None
    for path in cookie_locations:
        abs_path = os.path.abspath(path)
        exists = os.path.exists(path)
        print(f"🔍 Checking: {path}")
        print(f"   → Absolute: {abs_path}")
        print(f"   → Exists: {exists}")
        
        if exists:
            found_cookie_path = abs_path  # Use absolute path
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
                    has_login_info = 'LOGIN_INFO' in content
                    print(f"   → Has SID: {has_sid}, HSID: {has_hsid}, SSID: {has_ssid}, LOGIN_INFO: {has_login_info}")
                    
                    if cookie_count == 0:
                        print(f"   ⚠️  WARNING: No valid cookies!")
                    elif not (has_sid and has_hsid and has_ssid):
                        print(f"   ⚠️  WARNING: Missing critical YouTube cookies!")
                    else:
                        print(f"   ✅ Cookies look valid!")
                        break  # Use this one
                        
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
# 🔧 YT-DLP OPTIONS (FIXED)
# ==========================================
def get_ydl_opts(use_cookies: bool = True):
    """
    Get yt-dlp options with PROPER configuration.
    
    KEY FIXES:
    1. Use 'web' client only when cookies are present (android doesn't support cookies)
    2. Don't rely on env vars for botguard - use extractor_args
    3. Add proper po_token provider configuration
    """
    print(f"\n🔧 [get_ydl_opts] === STARTING ===")
    print(f"🔧 [get_ydl_opts] COOKIE_PATH: {COOKIE_PATH}")
    print(f"🔧 [get_ydl_opts] FFMPEG_AVAILABLE: {FFMPEG_AVAILABLE}")
    print(f"🔧 [get_ydl_opts] BOTGUARD_PATH: {BOTGUARD_PATH}")
    print(f"🔧 [get_ydl_opts] BOTGUARD_WORKING: {BOTGUARD_WORKING}")
    
    cookie_file = COOKIE_PATH if (COOKIE_PATH and os.path.exists(COOKIE_PATH) and use_cookies) else None
    
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 3,
    }
    
    # Configure extractor args based on what's available
    extractor_args = {}
    
    if cookie_file:
        print(f"✅ [get_ydl_opts] Using cookies: {cookie_file}")
        opts['cookiefile'] = cookie_file
        
        # IMPORTANT: When using cookies, use 'web' client only
        # Android client does NOT support cookies!
        extractor_args['player_client'] = ['web']
        print(f"✅ [get_ydl_opts] Player client: web (cookies compatible)")
    else:
        print(f"⚠️  [get_ydl_opts] NO COOKIES - using mweb,tv client")
        # Without cookies, try other clients
        extractor_args['player_client'] = ['mweb', 'tv']
    
    # Configure po_token provider if botguard is working
    if BOTGUARD_WORKING and BOTGUARD_PATH:
        print(f"✅ [get_ydl_opts] Botguard working - configuring po_token provider")
        # yt-dlp looks for this in specific ways
        extractor_args['po_token_provider'] = ['rustypipe-botguard']
        print(f"✅ [get_ydl_opts] po_token_provider: rustypipe-botguard")
    else:
        print(f"⚠️  [get_ydl_opts] Botguard not working - relying on cookies only")
    
    if extractor_args:
        opts['extractor_args'] = {'youtube': extractor_args}
        print(f"✅ [get_ydl_opts] Extractor args: {extractor_args}")
    
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
        print(f"⚠️  [get_ydl_opts] No FFmpeg - using direct audio format")
    
    print(f"🔧 [get_ydl_opts] === COMPLETE ===\n")
    return opts


def get_ydl_opts_fallback():
    """
    Fallback yt-dlp options - tries different strategies.
    Used when primary method fails.
    """
    print(f"\n🔧 [get_ydl_opts_fallback] === TRYING FALLBACK ===")
    
    opts = {
        'format': 'bestaudio/best',  # More permissive format
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'socket_timeout': 60,
        'retries': 5,
    }
    
    # Try without cookies - use clients that don't need auth
    opts['extractor_args'] = {
        'youtube': {
            'player_client': ['ios', 'mweb'],  # iOS often works without cookies
        }
    }
    
    print(f"✅ [get_ydl_opts_fallback] Using iOS/mweb client without cookies")
    
    if FFMPEG_AVAILABLE and FFMPEG_PATH:
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',  # Lower quality for reliability
        }]
        opts['ffmpeg_location'] = FFMPEG_PATH
    
    print(f"🔧 [get_ydl_opts_fallback] === COMPLETE ===\n")
    return opts


async def download_audio(url: str, use_fallback: bool = False) -> dict:
    """
    Download audio from YouTube with proper error handling and fallback.
    """
    print(f"\n🔥 [download_audio] === STARTING ===")
    print(f"🔥 [download_audio] URL: {url}")
    print(f"🔥 [download_audio] Fallback mode: {use_fallback}")
    print(f"🔥 [download_audio] Botguard: {'✅ Working' if BOTGUARD_WORKING else '❌ Not Working'}")
    print(f"🔥 [download_audio] Cookies: {'✅ Available' if COOKIE_PATH else '❌ Not Available'}")
    
    ydl_opts = get_ydl_opts_fallback() if use_fallback else get_ydl_opts()
    
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
            
            # Verify file exists
            if not os.path.exists(file_path):
                # Try finding the actual downloaded file
                video_id = info.get('id', '')
                for ext in ['.mp3', '.m4a', '.webm', '.opus']:
                    potential_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}{ext}")
                    if os.path.exists(potential_path):
                        file_path = potential_path
                        break
            
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
            
            # Diagnose the error
            if "Sign in" in error_str or "bot" in error_str.lower():
                print(f"❌ [download_audio] DIAGNOSIS: Bot detection / Auth required")
                print(f"   → Cookies may be expired or invalid")
                print(f"   → Try refreshing cookies from incognito")
            elif "No valid rustypipe-botguard" in error_str:
                print(f"❌ [download_audio] DIAGNOSIS: Botguard binary issue")
                print(f"   → Need rustypipe-botguard v1.x (not v0.1.x)")
                print(f"   → Download from: https://github.com/nickshanks347/rustypipe-botguard/releases")
            elif "Signature" in error_str or "n challenge" in error_str:
                print(f"❌ [download_audio] DIAGNOSIS: Signature/Challenge failed")
                print(f"   → Botguard not working properly")
            elif "format" in error_str.lower() or "Only images" in error_str:
                print(f"❌ [download_audio] DIAGNOSIS: No audio formats available")
                print(f"   → YouTube blocked all audio formats")
                print(f"   → Need working po_token or valid cookies")
            
            print(f"❌ [download_audio] === END ===\n")
            
            # Try fallback if not already using it
            if not use_fallback:
                print(f"🔄 [download_audio] Attempting fallback method...")
                return await download_audio(url, use_fallback=True)
            
            raise e


def is_youtube_url(url: str) -> bool:
    """Check if string is a YouTube URL"""
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))


async def search_youtube(query: str) -> Optional[str]:
    """Search YouTube and return first result URL"""
    print(f"🔍 [search_youtube] Searching: {query}")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'extract_flat': True,  # Don't download, just get info
    }
    
    # Use cookies for search if available
    if COOKIE_PATH and os.path.exists(COOKIE_PATH):
        ydl_opts['cookiefile'] = COOKIE_PATH
        print(f"✅ [search_youtube] Using cookies for search")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
                video_id = entry.get('id') or entry.get('url', '').split('=')[-1]
                url = f"https://www.youtube.com/watch?v={video_id}"
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
print(f"✅ MUSIC MODULE CORE LOADED - FIXED VERSION")
print(f"{'='*70}")
print(f"🍪 Cookies:    {'✅ Available at ' + COOKIE_PATH if COOKIE_PATH else '❌ Not Found'}")
print(f"🎬 FFmpeg:     {'✅ Available' if FFMPEG_AVAILABLE else '❌ Not Available'}")
print(f"🔥 Botguard:   {'✅ Working' if BOTGUARD_WORKING else '⚠️  Not Working (path: ' + str(BOTGUARD_PATH) + ')'}")
print(f"{'='*70}")

if FFMPEG_PATH:
    print(f"📂 FFmpeg Path: {FFMPEG_PATH}")
if BOTGUARD_PATH:
    print(f"📂 Botguard Path: {BOTGUARD_PATH}")

print(f"{'='*70}")

if BOTGUARD_WORKING and COOKIE_PATH:
    print(f"\n✅ OPTIMAL SETUP: Both cookies AND working botguard!")
    print(f"✅ Bot should have maximum compatibility")
elif COOKIE_PATH:
    print(f"\n⚠️  COOKIES ONLY: Botguard not working")
    print(f"⚠️  Bot may fail on some videos - cookies will expire faster")
    print(f"⚠️  To fix: Install rustypipe-botguard v1.x (not v0.1.x)")
elif BOTGUARD_WORKING:
    print(f"\n⚠️  BOTGUARD ONLY: No cookies available")
    print(f"⚠️  Bot will use iOS/mweb clients")
else:
    print(f"\n❌ MINIMAL SETUP: Neither cookies nor botguard working")
    print(f"❌ Bot will likely fail on most videos")

print(f"{'='*70}\n")
