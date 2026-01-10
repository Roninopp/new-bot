"""
Music Player Module - Part 1: Core System & Download Logic
FIXED VERSION V2 - Works without botguard using TV/iOS client fallback
Handles: FFmpeg detection, cookies, download, queue management
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
# 🔥 RUSTYPIPE BOTGUARD CHECK
# ==========================================
def check_botguard():
    """Check if RustyPipe botguard binary is available and working."""
    print("\n" + "="*70)
    print("🔍 RUSTYPIPE BOTGUARD DETECTION")
    print("="*70)
    
    botguard_path = os.environ.get('RUSTYPIPE_BOTGUARD_PATH', '/app/rustypipe-botguard')
    
    if not os.path.exists(botguard_path):
        print(f"❌ Botguard not found at: {botguard_path}")
        print("="*70 + "\n")
        return None, False
    
    # Make executable
    try:
        os.chmod(botguard_path, 0o755)
    except:
        pass
    
    # Test if it works
    try:
        result = subprocess.run(
            [botguard_path, '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        version = result.stdout.strip() or result.stderr.strip()
        print(f"📋 Botguard version: {version}")
        
        if result.returncode == 0:
            os.environ['RUSTYPIPE_BOTGUARD_PATH'] = botguard_path
            print(f"✅ Botguard is working!")
            print("="*70 + "\n")
            return botguard_path, True
        else:
            print(f"⚠️  Botguard returned error code: {result.returncode}")
            
    except Exception as e:
        print(f"❌ Botguard test failed: {e}")
    
    print("="*70 + "\n")
    return botguard_path, False

BOTGUARD_PATH, BOTGUARD_WORKING = check_botguard()

# ==========================================
# 🔍 FFMPEG DETECTION
# ==========================================
def detect_ffmpeg():
    """Detect FFmpeg installation and return path"""
    print("\n" + "="*70)
    print("🔍 FFMPEG DETECTION SYSTEM")
    print("="*70)
    
    ffmpeg_path = shutil.which('ffmpeg')
    ffprobe_path = shutil.which('ffprobe')
    
    if not ffmpeg_path:
        # Check common locations
        for path in ['/app/vendor/ffmpeg/ffmpeg', '/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg']:
            if os.path.exists(path):
                ffmpeg_path = path
                ffprobe_path = os.path.join(os.path.dirname(path), 'ffprobe')
                break
    
    if ffmpeg_path and os.path.exists(ffmpeg_path):
        print(f"✅ FFmpeg found: {ffmpeg_path}")
        try:
            result = subprocess.run([ffmpeg_path, '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"✅ FFmpeg works!")
                print("="*70 + "\n")
                return ffmpeg_path, True
        except:
            pass
    
    print("❌ FFmpeg not found or not working")
    print("="*70 + "\n")
    return None, False

FFMPEG_PATH, FFMPEG_AVAILABLE = detect_ffmpeg()

# ==========================================
# 🍪 COOKIE DETECTION
# ==========================================
def find_cookies():
    """Find cookie file"""
    print("="*70)
    print("🔍 COOKIE DETECTION")
    print("="*70)
    
    locations = ['/app/cookies.txt', 'cookies.txt', './cookies.txt', 'Yumeko/cookies.txt']
    
    for path in locations:
        if os.path.exists(path):
            abs_path = os.path.abspath(path)
            size = os.path.getsize(path)
            print(f"✅ Found cookies: {abs_path} ({size} bytes)")
            
            # Quick validation
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    has_sid = 'SID' in content
                    has_hsid = 'HSID' in content
                    if has_sid and has_hsid:
                        print(f"✅ Cookies appear valid (has SID, HSID)")
                    else:
                        print(f"⚠️  Cookies may be incomplete")
            except:
                pass
            
            print("="*70 + "\n")
            return abs_path
    
    print("❌ No cookies found")
    print("="*70 + "\n")
    return None

COOKIE_PATH = find_cookies()

# ==========================================
# 🔧 YT-DLP OPTIONS
# ==========================================
def get_ydl_opts(strategy: str = "default"):
    """
    Get yt-dlp options based on strategy.
    
    Strategies:
    - "default": Use web client with cookies + botguard
    - "tv": Use TV client (no cookies needed, works on most videos)
    - "ios": Use iOS client (fallback)
    - "android": Use Android client (another fallback)
    """
    print(f"\n🔧 [get_ydl_opts] Strategy: {strategy}")
    
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
        'quiet': False,
        'no_warnings': False,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 3,
        'ignoreerrors': False,
    }
    
    extractor_args = {}
    
    if strategy == "default":
        # Try web client with cookies
        if COOKIE_PATH:
            opts['cookiefile'] = COOKIE_PATH
            extractor_args['player_client'] = ['web']
            print(f"✅ Using WEB client with cookies")
            
            # If botguard is available, configure it for po_token
            if BOTGUARD_WORKING and BOTGUARD_PATH:
                # Tell yt-dlp where to find botguard
                extractor_args['getpot_bgutil_baseurl'] = ''  # Disable bgutil server
                extractor_args['getpot_bgutil_program'] = BOTGUARD_PATH
                print(f"✅ Botguard configured: {BOTGUARD_PATH}")
        else:
            # No cookies, fall back to TV
            extractor_args['player_client'] = ['tv', 'mweb']
            print(f"⚠️  No cookies, using TV/mweb client")
    
    elif strategy == "tv":
        # TV client doesn't require cookies or po_token for most videos
        extractor_args['player_client'] = ['tv']
        print(f"📺 Using TV client (no auth required)")
    
    elif strategy == "ios":
        # iOS client - good fallback
        extractor_args['player_client'] = ['ios']
        print(f"📱 Using iOS client")
    
    elif strategy == "android":
        # Android - requires no cookies
        extractor_args['player_client'] = ['android_vr']  # VR variant often works
        print(f"🤖 Using Android VR client")
    
    elif strategy == "mweb":
        # Mobile web
        extractor_args['player_client'] = ['mweb']
        print(f"📲 Using Mobile Web client")
    
    if extractor_args:
        opts['extractor_args'] = {'youtube': extractor_args}
    
    # Add FFmpeg if available
    if FFMPEG_AVAILABLE and FFMPEG_PATH:
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
        opts['ffmpeg_location'] = FFMPEG_PATH
        print(f"✅ FFmpeg postprocessor enabled")
    
    print(f"🔧 [get_ydl_opts] Complete\n")
    return opts


async def download_audio(url: str) -> dict:
    """
    Download audio from YouTube with multiple fallback strategies.
    """
    print(f"\n🔥 [download_audio] === STARTING ===")
    print(f"🔥 [download_audio] URL: {url}")
    print(f"🔥 [download_audio] Botguard: {'✅' if BOTGUARD_WORKING else '❌'}")
    print(f"🔥 [download_audio] Cookies: {'✅' if COOKIE_PATH else '❌'}")
    
    # Try different strategies in order
    strategies = []
    
    if COOKIE_PATH:
        strategies.append("default")  # Web with cookies
    
    # Always include these fallbacks
    strategies.extend(["tv", "ios", "mweb", "android"])
    
    last_error = None
    
    for strategy in strategies:
        print(f"\n📥 [download_audio] Trying strategy: {strategy}")
        
        ydl_opts = get_ydl_opts(strategy)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=True)
                
                if 'entries' in info:
                    info = info['entries'][0]
                
                file_path = ydl.prepare_filename(info)
                
                # Handle extension change from FFmpeg
                if FFMPEG_AVAILABLE:
                    mp3_path = os.path.splitext(file_path)[0] + '.mp3'
                    if os.path.exists(mp3_path):
                        file_path = mp3_path
                
                # Verify file exists
                if not os.path.exists(file_path):
                    video_id = info.get('id', '')
                    for ext in ['.mp3', '.m4a', '.webm', '.opus', '.ogg']:
                        potential = os.path.join(DOWNLOAD_FOLDER, f"{video_id}{ext}")
                        if os.path.exists(potential):
                            file_path = potential
                            break
                
                if not os.path.exists(file_path):
                    raise Exception(f"Downloaded file not found")
                
                print(f"✅ [download_audio] SUCCESS with strategy: {strategy}")
                print(f"✅ [download_audio] File: {file_path}")
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
            last_error = str(e)
            print(f"❌ [download_audio] Strategy '{strategy}' failed: {last_error[:100]}")
            
            # Don't try other strategies for certain errors
            if "Private video" in last_error or "Video unavailable" in last_error:
                break
    
    # All strategies failed
    print(f"\n❌ [download_audio] === ALL STRATEGIES FAILED ===")
    print(f"❌ [download_audio] Last error: {last_error}")
    print(f"🔥 [download_audio] === END ===\n")
    
    raise Exception(f"Download failed: {last_error}")


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
        'extract_flat': True,
    }
    
    if COOKIE_PATH:
        ydl_opts['cookiefile'] = COOKIE_PATH
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
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


# ==========================================
# 📊 STARTUP SUMMARY
# ==========================================
print(f"\n{'='*70}")
print(f"✅ MUSIC MODULE CORE LOADED - FIXED VERSION V2")
print(f"{'='*70}")
print(f"🍪 Cookies:    {'✅ ' + COOKIE_PATH if COOKIE_PATH else '❌ Not Found'}")
print(f"🎬 FFmpeg:     {'✅ Available' if FFMPEG_AVAILABLE else '❌ Not Available'}")
print(f"🔥 Botguard:   {'✅ Working' if BOTGUARD_WORKING else '⚠️  Not Available'}")
print(f"{'='*70}")

if not BOTGUARD_WORKING:
    print(f"\n⚠️  RUNNING WITHOUT BOTGUARD")
    print(f"✅ Will use TV/iOS client fallback (works for most videos)")
    print(f"⚠️  Some age-restricted videos may not work")

if not COOKIE_PATH:
    print(f"\n⚠️  NO COOKIES FOUND")
    print(f"⚠️  Some features may be limited")

print(f"{'='*70}\n")
