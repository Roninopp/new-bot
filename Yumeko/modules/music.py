"""
Music Player Module - Core System (API VERSION)
Replaced complex local download logic with XBitCode API.
"""

import asyncio
import logging
import os
import yt_dlp
from music_api import get_stream_link  # Import your new API handler

# Setup Logging
logger = logging.getLogger(__name__)

# ==========================================
# 🎵 SEARCH FUNCTION
# ==========================================
async def search_youtube(query: str):
    """
    Searches YouTube to get a Video URL. 
    We use yt-dlp here ONLY for searching IDs (lightweight), not downloading.
    """
    # If the user provided a direct link, just return it
    if "youtube.com" in query or "youtu.be" in query:
        return query

    logger.info(f"🔍 [search_youtube] Searching for: {query}")
    
    # Lightweight options just to get the ID
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'extract_flat': True, # Don't download, just get metadata
    }
    
    try:
        # Run in thread to avoid blocking bot
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, f"ytsearch:{query}", download=False)
            
            if info and 'entries' in info and len(info['entries']) > 0:
                entry = info['entries'][0]
                video_id = entry.get('id')
                title = entry.get('title', 'Unknown')
                url = f"https://www.youtube.com/watch?v={video_id}"
                
                logger.info(f"✅ [search_youtube] Found: {title} ({url})")
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
    New behavior: Fetches STREAM URL from API (Does not actually download file).
    Returns a dict compatible with your existing player code.
    """
    logger.info(f"🔥 [API BRIDGE] Requesting stream for: {url}")
    
    # 1. Get the direct stream link from your new API module
    stream_url, title_or_error = await get_stream_link(url)
    
    # 2. Handle Errors
    if not stream_url:
        logger.error(f"❌ [API BRIDGE] Failed: {title_or_error}")
        raise Exception(f"API Error: {title_or_error}")

    # 3. Return data in the format your bot expects
    # We cheat by putting the HTTP URL into 'file_path'. 
    # PyTgCalls handles HTTP URLs perfectly!
    return {
        'title': title_or_error,      # API returns title in second var on success
        'duration': 0,                # API doesn't give duration, set to 0 (live stream mode)
        'file_path': stream_url,      # <--- IMPORTANT: This is now a URL, not a local path
        'url': url,
        'thumbnail': None             # We skip thumbnails for speed
    }

# ==========================================
# 🎵 QUEUE MANAGEMENT (Kept same as before)
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
print(f"{'='*70}")
print(f"🚀 Download Logic:   Delegated to XBitCode API")
print(f"🔍 Search Logic:     Internal yt-dlp (Metadata only)")
print(f"🗑️  Bloatware:        Cookies/Botguard REMOVED")
print(f"{'='*70}\n")
