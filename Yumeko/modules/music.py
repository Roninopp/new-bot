"""
Music Player Module - Integrated API Version
Fixed: Added back 'is_youtube_url' to prevent ImportError
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
# 🧱 BACKWARD COMPATIBILITY (DUMMY VARS)
# ==========================================
# These prevent ImportError from other modules
FFMPEG_AVAILABLE = True  
COOKIE_PATH = None
BOTGUARD_WORKING = False
DOWNLOAD_FOLDER = '/tmp/music_downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ==========================================
# 🔧 HELPER FUNCTIONS (Restored)
# ==========================================
def is_youtube_url(url: str) -> bool:
    """Check if string is a YouTube URL. Restored to fix ImportError."""
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

# ==========================================
# 🎵 API HANDLER
# ==========================================
API_KEY = "xbit_qxkNri00qFMQcYL3L1cOGML0qTTI5fJE"
BASE_URL = "https://tgapi.xbitcode.com"

async def get_stream_link(query_or_url: str):
    """
    Fetches audio link from XBitCode API.
    """
    # --- Step 1: Extract Video ID ---
    video_id = None
    # Regex to extract ID from various YouTube URL formats
    regex = r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})"
    match = re.search(regex, query_or_url)
    
    if match:
        video_id = match.group(1)
    else:
        # Fallback: if user sends a search query instead of a link, we need to search first
        # But this function expects a link/ID mostly.
        logger.warning(f"Could not extract Video ID from: {query_or_url}")
        return None, "Please provide a valid YouTube Link for this API test."

    logger.info(f"🔍 Extracted Video ID: {video_id}")

    # --- Step 2: Call the API ---
    endpoint = f"{BASE_URL}/info/{video_id}"
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(endpoint, headers=headers) as response:
                if response.status == 403:
                    return None, "❌ API Key is invalid or blocked!"
                if response.status == 429:
                    return None, "❌ Daily Request Limit Reached (100/100)!"
                if response.status != 200:
                    return None, f"❌ API Error: HTTP {response.status}"

                data = await response.json()
                
                if data.get("status") == "success":
                    audio_url = data.get("audio_url")
                    title = data.get("title", "Unknown Title")
                    logger.info(f"✅ API Success! Got Audio URL.")
                    return audio_url, title
                else:
                    error_message = data.get("message", "Unknown API error")
                    return None, f"❌ API Failed: {error_message}"

        except Exception as e:
            logger.error(f"❌ Connection Error: {e}")
            return None, f"❌ Connection Error: {e}"

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
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'extract_flat': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
                video_id = entry.get('id')
                title = entry.get('title', 'Unknown')
                url = f"https://www.youtube.com/watch?v={video_id}"
                return url
    except Exception as e:
        logger.error(f"❌ [search_youtube] Failed: {e}")
    
    return None

# ==========================================
# 🔥 CORE HANDLER (API BRIDGE)
# ==========================================
async def download_audio(url: str):
    """
    Old name: download_audio
    New behavior: Fetches STREAM URL from API.
    """
    logger.info(f"🔥 [API BRIDGE] Requesting stream for: {url}")
    
    stream_url, title_or_error = await get_stream_link(url)
    
    if not stream_url:
        logger.error(f"❌ [API BRIDGE] Failed: {title_or_error}")
        raise Exception(f"API Error: {title_or_error}")

    return {
        'title': title_or_error,
        'duration': 0,
        'file_path': stream_url,  # Direct URL for PyTgCalls
        'url': url,
        'thumbnail': None
    }

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
print(f"✅ MUSIC MODULE LOADED (API MODE)")
print(f"🚀 Download Logic:   XBitCode API (Internal)")
print(f"🔧 Compatibility:    'is_youtube_url' restored")
print(f"{'='*70}\n")
