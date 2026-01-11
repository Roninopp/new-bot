"""
Music Player Module - Clean API Version (v8)
Fixed: Proper metadata handling, no weird dummy data
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
# 🎵 CLEAN METADATA ENGINE
# ==========================================
async def get_video_info(video_id: str):
    """
    Gets clean metadata from YouTube.
    Returns proper data or None if fails.
    """
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'skip_download': True,
        'extract_flat': 'in_playlist',
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(
                ydl.extract_info, 
                f"https://www.youtube.com/watch?v={video_id}", 
                download=False
            )
            
            if info:
                # Get best thumbnail
                thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                if 'thumbnail' in info:
                    thumbnail = info['thumbnail']
                
                return {
                    "title": info.get('title', 'Unknown'),
                    "duration": int(info.get('duration', 0)),
                    "thumbnail": thumbnail,
                    "uploader": info.get('uploader', info.get('channel', 'Unknown'))
                }
    except:
        pass
    
    return None

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
    Clean downloader with proper metadata.
    """
    logger.info(f"📥 [PROCESS] Processing: {url}")
    
    # 1. Extract ID
    regex = r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})"
    match = re.search(regex, url)
    if not match:
        match = re.search(r"([a-zA-Z0-9_-]{11})", url)
        if not match:
             raise Exception("Invalid URL")
    
    video_id = match.group(1)
    
    # 2. Get metadata (can be None)
    meta = await get_video_info(video_id)
    
    # 3. Get Stream URL from API
    stream_url, api_title = await get_stream_link(video_id)
    if not stream_url:
        raise Exception("Failed to get download link")
    
    # 4. Use API title if metadata failed
    if not meta and api_title:
        meta = {
            "title": api_title,
            "duration": 0,
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            "uploader": "Unknown"
        }
    elif not meta:
        raise Exception("Failed to get song info")

    # 5. Download the File
    file_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp3")
    
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logger.info(f"📥 Downloading: {meta['title']}")
        headers = {
            "x-api-key": API_KEY,
            "User-Agent": "Mozilla/5.0"
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
                    raise Exception(f"Download failed: HTTP {resp.status}")

    # 6. Return clean data
    return {
        'title': meta['title'],
        'duration': meta['duration'],
        'file_path': file_path,
        'url': f"https://www.youtube.com/watch?v={video_id}",
        'thumbnail': meta['thumbnail'],
        'vidid': video_id,
        'uploader': meta['uploader']
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
    
    ydl_opts = {
        'quiet': True, 
        'default_search': 'ytsearch', 
        'extract_flat': True,
        'no_warnings': True
    }
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

print(f"\n✅ MUSIC MODULE LOADED (Clean v8 - Fixed Output)")
