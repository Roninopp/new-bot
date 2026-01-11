"""
Music Player Module - Fixed Working Version (v9)
Back to the ORIGINAL working metadata method!
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
# 🧱 CONFIG & DUMMY VARS
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
# 🎵 QUEUE SYSTEM
# ==========================================
music_queue = {}

def add_to_queue(chat_id: int, song_data: dict):
    if chat_id not in music_queue:
        music_queue[chat_id] = []
    music_queue[chat_id].append(song_data)

def get_queue(chat_id: int) -> list:
    return music_queue.get(chat_id, [])

def get_next_song(chat_id: int):
    if chat_id in music_queue and music_queue[chat_id]:
        return music_queue[chat_id].pop(0)
    return None

def clear_queue(chat_id: int):
    if chat_id in music_queue:
        music_queue[chat_id] = []

# ==========================================
# 🎵 ORIGINAL WORKING METADATA (FROM YOUR FILE!)
# ==========================================
async def get_video_info(video_id: str):
    """
    YOUR ORIGINAL working method with ytsearch bypass!
    This was working perfectly, I shouldn't have changed it!
    """
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'extract_flat': True,  # Your original setting
        'ignoreerrors': True
    }
    
    try:
        # YOUR ORIGINAL TRICK: Search for the ID instead of visiting URL
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch1:{video_id}", download=False)
            
            if 'entries' in info and info['entries']:
                entry = info['entries'][0]
                return {
                    "title": entry.get('title', 'Unknown Title'),
                    "duration": int(entry.get('duration', 0)),
                    "thumbnail": entry.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg")
                }
    except Exception as e:
        logger.error(f"Metadata Bypass Failed: {e}")
    
    # FALLBACK: Return basic data (API will still work!)
    return {
        "title": f"Music Track",
        "duration": 0,
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    }

# ==========================================
# 📥 CORE HANDLER (API DOWNLOAD)
# ==========================================
async def get_stream_link(video_id: str):
    endpoint = f"{BASE_URL}/info/{video_id}"
    headers = {"x-api-key": API_KEY}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(endpoint, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("audio_url"), data.get("title") 
                return None, None
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None, None

async def download_audio(url: str):
    """
    YOUR ORIGINAL working download logic!
    """
    logger.info(f"📥 [PROCESS] Processing: {url}")
    
    # 1. Extract ID (YOUR ORIGINAL REGEX)
    regex = r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})"
    match = re.search(regex, url)
    if not match:
        # Fallback for search queries
        match = re.search(r"([a-zA-Z0-9_-]{11})", url)
        if not match:
             raise Exception("Could not find Video ID")
    
    video_id = match.group(1)
    
    # 2. Get Metadata (YOUR ORIGINAL WAY - Soft Fail)
    meta = await get_video_info(video_id)
    title = meta['title']
    duration = meta['duration']
    
    # 3. Get Stream URL from API
    stream_url, api_title = await get_stream_link(video_id)
    if not stream_url:
        raise Exception("API Download Link Failed")
    
    # If yt-dlp failed but API gave a title, use it!
    if title.startswith("Music Track") and api_title:
        title = api_title

    # 4. Download the File (YOUR ORIGINAL CODE)
    file_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp3")
    
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logger.info(f"📥 Downloading: {title}")
        headers = {
            "x-api-key": API_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(stream_url, headers=headers) as resp:
                if resp.status == 200:
                    with open(file_path, 'wb') as f:
                        while True:
                            chunk = await resp.content.read(1024*1024)
                            if not chunk: break
                            f.write(chunk)
                else:
                    raise Exception(f"Download HTTP {resp.status}")

    # 5. Return Data
    return {
        'title': title,
        'duration': duration,
        'file_path': file_path,
        'url': f"https://www.youtube.com/watch?v={video_id}",
        'thumbnail': meta['thumbnail'],
        'vidid': video_id
    }

# ==========================================
# 🎵 SEARCH UTILS
# ==========================================
def is_youtube_url(url: str) -> bool:
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

async def search_youtube(query: str):
    """Simple search to get URL."""
    if is_youtube_url(query): 
        return query
    
    # Use ytsearch1 trick here too
    ydl_opts = {'quiet': True, 'default_search': 'ytsearch', 'extract_flat': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch1:{query}", download=False)
            if 'entries' in info and info['entries']:
                return f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
    except:
        pass
    return None

# ==========================================
# 🧹 CURRENT PLAYING
# ==========================================
current_playing = {}

print(f"\n✅ MUSIC MODULE LOADED (Fixed v9 - Back to Working Original!)")
