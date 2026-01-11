"""
Music Player Module - API Download Version (v3)
Fixes HTTP 400 Error by sending API Headers during download.
"""

import asyncio
import logging
import os
import re
import aiohttp
import yt_dlp

# Setup Logging
logger = logging.getLogger(__name__)

# ==========================================
# 🧱 CONFIGURATION & DUMMY VARS
# ==========================================
FFMPEG_AVAILABLE = True  
COOKIE_PATH = None
BOTGUARD_WORKING = False
DOWNLOAD_FOLDER = '/tmp/music_downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# API Config
API_KEY = "xbit_qxkNri00qFMQcYL3L1cOGML0qTTI5fJE"
BASE_URL = "https://tgapi.xbitcode.com"

# ==========================================
# 🔧 HELPER FUNCTIONS
# ==========================================
def is_youtube_url(url: str) -> bool:
    """Check if string is a YouTube URL."""
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

async def get_stream_link(video_id: str):
    """
    Fetches audio link from XBitCode API.
    """
    endpoint = f"{BASE_URL}/info/{video_id}"
    headers = {
        "x-api-key": API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(endpoint, headers=headers) as response:
                if response.status != 200:
                    return None, f"API Error: {response.status}"

                data = await response.json()
                if data.get("status") == "success":
                    return data.get("audio_url"), data.get("title", "Unknown Title")
                else:
                    return None, data.get("message", "Unknown API Error")
        except Exception as e:
            return None, f"Connection Error: {e}"

# ==========================================
# 🎵 SEARCH FUNCTION
# ==========================================
async def search_youtube(query: str):
    """
    Searches YouTube to get a Video URL. 
    """
    if is_youtube_url(query):
        return query

    logger.info(f"🔍 [search_youtube] Searching for: {query}")
    ydl_opts = {'quiet': True, 'no_warnings': True, 'default_search': 'ytsearch', 'extract_flat': True}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                return f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
    except Exception as e:
        logger.error(f"❌ [search_youtube] Failed: {e}")
    
    return None

# ==========================================
# 🔥 CORE HANDLER (DOWNLOAD MODE)
# ==========================================
async def download_audio(url: str):
    """
    1. Gets Stream URL from API.
    2. Downloads the file to /tmp WITH HEADERS.
    3. Returns the LOCAL path to the player.
    """
    logger.info(f"🔥 [API DOWNLOAD] Processing: {url}")
    
    # 1. Extract ID
    regex = r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})"
    match = re.search(regex, url)
    if not match:
        raise Exception("Invalid YouTube URL")
    
    video_id = match.group(1)
    
    # 2. Get Stream Link
    stream_url, title = await get_stream_link(video_id)
    if not stream_url:
        raise Exception(f"API Failed: {title}")

    # 3. DOWNLOAD the file (Fixed Headers)
    file_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp3")
    
    # Check if we need to download
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logger.info(f"📥 Downloading from API to: {file_path}")
        
        # HEADERS ARE CRITICAL HERE
        headers = {
            "x-api-key": API_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(stream_url, headers=headers) as resp:
                if resp.status == 200:
                    with open(file_path, 'wb') as f:
                        while True:
                            chunk = await resp.content.read(1024*1024) # 1MB chunks
                            if not chunk:
                                break
                            f.write(chunk)
                else:
                    # Log the response text to debug if it fails again
                    error_text = await resp.text()
                    logger.error(f"❌ Download Failed {resp.status}: {error_text}")
                    raise Exception(f"Download Failed: HTTP {resp.status}")
    else:
        logger.info(f"✅ File already exists in cache: {file_path}")

    # 4. Return LOCAL path
    return {
        'title': title,
        'duration': 0,
        'file_path': file_path,
        'url': url,
        'thumbnail': None
    }

# ==========================================
# 🎵 QUEUE MANAGEMENT
# ==========================================
music_queue = {}
current_playing = {}

def add_to_queue(chat_id: int, song_data: dict):
    if chat_id not in music_queue: music_queue[chat_id] = []
    music_queue[chat_id].append(song_data)

def get_queue(chat_id: int) -> list: return music_queue.get(chat_id, [])

def clear_queue(chat_id: int):
    if chat_id in music_queue: music_queue[chat_id] = []
    if chat_id in current_playing: del current_playing[chat_id]

# ==========================================
# 📊 STARTUP SUMMARY
# ==========================================
print(f"\n{'='*70}")
print(f"✅ MUSIC MODULE LOADED (DOWNLOAD MODE V3)")
print(f"🚀 Status: Headers Added to Download Request")
print(f"{'='*70}\n")
