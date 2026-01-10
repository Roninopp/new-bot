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
def check_rustypipe_installation():
    """Check if RustyPipe binary is installed"""
    print("\n" + "="*70)
    print("🔍 RUSTYPIPE DETECTION SYSTEM - STARTING")
    print("="*70)
    
    rustypipe_paths = [
        '/app/rustypipe/target/release/rustypipe',
        './rustypipe/target/release/rustypipe',
        'rustypipe',
        '/usr/local/bin/rustypipe'
    ]
    
    rustypipe_path = None
    for path in rustypipe_paths:
        if os.path.exists(path):
            rustypipe_path = path
            print(f"✅ RustyPipe found at: {rustypipe_path}")
            break
    
    if not rustypipe_path:
        rustypipe_path = shutil.which('rustypipe')
        if rustypipe_path:
            print(f"✅ RustyPipe found in PATH: {rustypipe_path}")
    
    if not rustypipe_path:
        print("❌ RustyPipe NOT FOUND!")
        print("⚠️  Bot will work with cookies only (will die when cookies expire)")
        print("="*70 + "\n")
        return None
    
    # Test RustyPipe
    try:
        result = subprocess.run(
            [rustypipe_path, '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ RustyPipe works! Version: {result.stdout.strip()}")
            print("="*70 + "\n")
            return rustypipe_path
        else:
            print(f"❌ RustyPipe test failed")
            print("="*70 + "\n")
            return None
    except Exception as e:
        print(f"❌ RustyPipe test error: {e}")
        print("="*70 + "\n")
        return None

RUSTYPIPE_PATH = check_rustypipe_installation()

def generate_po_token():
    """Generate fresh po_token using RustyPipe"""
    print("\n" + "="*70)
    print("🎯 PO_TOKEN GENERATION - STARTING")
    print("="*70)
    
    if not RUSTYPIPE_PATH:
        print("❌ RustyPipe not available, cannot generate po_token")
        print("="*70 + "\n")
        return None
    
    try:
        print("🔄 Calling RustyPipe to generate po_token...")
        
        # RustyPipe command to generate po_token
        result = subprocess.run(
            [RUSTYPIPE_PATH, 'generate-po-token'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            po_token = result.stdout.strip()
            if po_token and len(po_token) > 10:
                print(f"✅ PO_TOKEN GENERATED: {po_token[:20]}...{po_token[-10:]}")
                print(f"📊 Token Length: {len(po_token)} characters")
                
                # Save to file for persistence
                po_token_file = '/app/po_token.txt'
                try:
                    with open(po_token_file, 'w') as f:
                        f.write(po_token)
                    print(f"💾 Saved to: {po_token_file}")
                except Exception as e:
                    print(f"⚠️  Failed to save token: {e}")
                
                print("="*70 + "\n")
                return po_token
            else:
                print(f"❌ Invalid po_token received: {po_token}")
                print("="*70 + "\n")
                return None
        else:
            print(f"❌ RustyPipe failed: {result.stderr[:200]}")
            print("="*70 + "\n")
            return None
            
    except subprocess.TimeoutExpired:
        print("❌ RustyPipe timeout (30s)")
        print("="*70 + "\n")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        print("="*70 + "\n")
        return None

def load_or_generate_po_token():
    """Load existing po_token or generate new one"""
    print("\n" + "="*70)
    print("🔑 PO_TOKEN LOADER - STARTING")
    print("="*70)
    
    po_token_file = '/app/po_token.txt'
    
    # Try to load existing token
    if os.path.exists(po_token_file):
        try:
            with open(po_token_file, 'r') as f:
                token = f.read().strip()
                if token and len(token) > 10:
                    print(f"✅ Loaded existing po_token: {token[:20]}...{token[-10:]}")
                    print(f"📊 Token age: {os.path.getmtime(po_token_file)}")
                    print("="*70 + "\n")
                    return token
        except Exception as e:
            print(f"⚠️  Failed to load token: {e}")
    
    # Generate new token
    print("🔄 No valid token found, generating fresh one...")
    token = generate_po_token()
    
    if token:
        print("✅ Fresh po_token ready!")
    else:
        print("❌ Failed to generate po_token")
    
    print("="*70 + "\n")
    return token

PO_TOKEN = load_or_generate_po_token()

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
    """Get yt-dlp options with FFmpeg, cookies, and RustyPipe po_token"""
    print(f"\n🔧 [get_ydl_opts] === STARTING ===")
    print(f"🔧 [get_ydl_opts] COOKIE_PATH: {COOKIE_PATH}")
    print(f"🔧 [get_ydl_opts] FFMPEG_AVAILABLE: {FFMPEG_AVAILABLE}")
    print(f"🔧 [get_ydl_opts] RUSTYPIPE_AVAILABLE: {RUSTYPIPE_PATH is not None}")
    print(f"🔧 [get_ydl_opts] PO_TOKEN_AVAILABLE: {PO_TOKEN is not None}")
    
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
    
    # 🎯 CRITICAL: Add RustyPipe po_token
    if PO_TOKEN:
        print(f"✅ [get_ydl_opts] Adding po_token to extractor args")
        opts['extractor_args'] = {
            'youtube': {
                'po_token': PO_TOKEN
            }
        }
        print(f"🔐 [get_ydl_opts] po_token configured: {PO_TOKEN[:20]}...{PO_TOKEN[-10:]}")
    else:
        print(f"⚠️  [get_ydl_opts] No po_token available - bot may fail soon!")
    
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
    print(f"🔥 [download_audio] RustyPipe: {'✅ Active' if PO_TOKEN else '❌ Inactive'}")
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
                if not PO_TOKEN:
                    print(f"🔥 [download_audio] CRITICAL: No po_token - this is why it failed!")
                    print(f"🔥 [download_audio] ACTION: Check RustyPipe installation")
                else:
                    print(f"⚠️  [download_audio] po_token present but still failed")
                    print(f"⚠️  [download_audio] Cookies might be expired")
            elif "Signature" in error_str:
                print(f"❌ [download_audio] DIAGNOSIS: Signature challenge failed!")
                print(f"⚠️  [download_audio] Need rustypipe-botguard binary")
            elif "rustypipe" in error_str.lower():
                print(f"❌ [download_audio] DIAGNOSIS: RustyPipe issue!")
                print(f"🔥 [download_audio] Check: {RUSTYPIPE_PATH}")
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
    print(f"🔍 [search_youtube] RustyPipe: {'✅' if PO_TOKEN else '❌'}")
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch'
    }
    
    # Add po_token for search
    if PO_TOKEN:
        ydl_opts['extractor_args'] = {
            'youtube': {
                'po_token': PO_TOKEN
            }
        }
        print(f"✅ [search_youtube] Using po_token for search")
    
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
print(f"✅ MUSIC MODULE CORE LOADED - ENHANCED WITH RUSTYPIPE")
print(f"{'='*70}")
print(f"🍪 Cookies:    {'✅ Available' if COOKIE_PATH else '❌ Not Found'}")
print(f"🎬 FFmpeg:     {'✅ Available' if FFMPEG_AVAILABLE else '❌ Not Available'}")
print(f"🔥 RustyPipe:  {'✅ Available' if RUSTYPIPE_PATH else '❌ Not Found'}")
print(f"🔑 PO_Token:   {'✅ Generated' if PO_TOKEN else '❌ Not Generated'}")
print(f"{'='*70}")

if FFMPEG_PATH:
    print(f"📂 FFmpeg Path: {FFMPEG_PATH}")
if RUSTYPIPE_PATH:
    print(f"📂 RustyPipe Path: {RUSTYPIPE_PATH}")
if PO_TOKEN:
    print(f"🔐 PO_Token: {PO_TOKEN[:20]}...{PO_TOKEN[-10:]} ({len(PO_TOKEN)} chars)")

print(f"{'='*70}")

if not PO_TOKEN:
    print(f"\n⚠️  WARNING: NO PO_TOKEN - BOT MAY DIE SOON!")
    print(f"⚠️  Check RustyPipe installation in install_rustypipe.sh")
    print(f"⚠️  Bot is running on cookies only (expires quickly)")
elif not COOKIE_PATH:
    print(f"\n⚠️  WARNING: NO COOKIES - Bot relies 100% on po_token")
    print(f"✅ This is OK if RustyPipe is working properly")
else:
    print(f"\n✅ OPTIMAL SETUP: Both cookies AND po_token available!")
    print(f"✅ Bot will have maximum lifespan")

print(f"{'='*70}\n")
