"""
Music Player Module - Final API Version (v5)
Fixes: Unknown Title, 0:00 Duration, and Queue Logic
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
# 🎵 QUEUE SYSTEM (Unified)
# ==========================================
music_queue = {}

def add_to_queue(chat_id: int, song_data: dict):
    if chat_id not in music_queue:
        music_queue[chat_id] = []
    music_queue[chat_id].append(song_data)

def get_queue(chat_id: int) -> list:
    return music_queue.get(chat_id, [])

def get_next_song(chat_id: int):
    """Returns the next song and removes it from queue"""
    if chat_id in music_queue and music_queue[chat_id]:
        return music_queue[chat_id].pop(0)
    return None

def clear_queue(chat_id: int):
    if chat_id in music_queue:
        music_queue[chat_id] = []

# ==========================================
# 🎵 METADATA ENGINE (The Fix for Unknown Title)
# ==========================================
async def get_video_info(url: str):
    """
    Uses yt-dlp to get REAL metadata without downloading.
    """
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'skip_download': True, # We only want info
        'extract_flat': True   # Fast mode
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=False)
            
            # Handle playlists/search results
            if 'entries' in info:
                info = info['entries'][0]
                
            return {
                "id": info.get('id'),
                "title": info.get('title', 'Unknown Title'),
                "duration": int(info.get('duration', 0)),
                "thumbnail": info.get('thumbnail')
            }
    except Exception as e:
        logger.error(f"Metadata Error: {e}")
        return None

# ==========================================
# 🔥 CORE HANDLER (API DOWNLOAD)
# ==========================================
async def get_stream_link(video_id: str):
    endpoint = f"{BASE_URL}/info/{video_id}"
    headers = {"x-api-key": API_KEY}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(endpoint, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("audio_url")
                return None
        except:
            return None

async def download_audio(url: str):
    """
    1. Get Metadata (Title/Duration) via yt-dlp.
    2. Download File via API.
    """
    logger.info(f"🔥 [PROCESS] Processing: {url}")
    
    # 1. Get Real Metadata First
    meta = await get_video_info(url)
    if not meta:
        raise Exception("Could not fetch video metadata")
    
    video_id = meta['id']
    title = meta['title']
    duration = meta['duration']
    
    # 2. Get Stream URL from API
    stream_url = await get_stream_link(video_id)
    if not stream_url:
        raise Exception("API failed to provide download link")

    # 3. Download the File (With Headers)
    file_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp3")
    
    # Download if not exists or empty
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        logger.info(f"📥 Downloading: {title}")
        headers = {
            "x-api-key": API_KEY,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
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

    # 4. Return Data (Compatible with PyTgCalls)
    return {
        'title': title,
        'duration': duration, # Real duration
        'file_path': file_path,
        'url': url,
        'thumbnail': meta['thumbnail'],
        'vidid': video_id
    }

# ==========================================
# 🎵 SEARCH UTILS
# ==========================================
# Helper to check if URL is YouTube
def is_youtube_url(url: str) -> bool:
    return bool(re.match(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/', url))

async def search_youtube(query: str):
    """Simple search to get URL."""
    if is_youtube_url(query): return query
    ydl_opts = {'quiet': True, 'default_search': 'ytsearch', 'extract_flat': True}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            if 'entries' in info and info['entries']:
                return f"https://www.youtube.com/watch?v={info['entries'][0]['id']}"
    except:
        pass
    return None

# ==========================================
# 🧹 CURRENT PLAYING TRACKER
# ==========================================
current_playing = {}

print(f"\n✅ MUSIC MODULE LOADED (FINAL v5)")
