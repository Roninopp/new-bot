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
# 📥 CORE HANDLER (API DOWNLOAD WITH RETRY!)
# ==========================================
async def get_stream_link(video_id: str, retry: int = 0):
    """Get stream link with retry logic"""
    endpoint = f"{BASE_URL}/info/{video_id}"
    headers = {"x-api-key": API_KEY}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(endpoint, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("audio_url"), data.get("title"), None
                elif resp.status == 500:
                    # Server error - retry
                    if retry < 2:
                        await asyncio.sleep(2)
                        return await get_stream_link(video_id, retry + 1)
                    return None, None, "API server error (500). Try again later."
                elif resp.status == 400:
                    return None, None, "Invalid video or API error (400)"
                else:
                    return None, None, f"API error: HTTP {resp.status}"
        except asyncio.TimeoutError:
            if retry < 2:
                await asyncio.sleep(1)
                return await get_stream_link(video_id, retry + 1)
            return None, None, "API timeout. Try again."
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None, None, f"Network error: {str(e)[:50]}"

async def download_audio(url: str):
    """
    Enhanced downloader with better error handling and validation.
    """
    logger.info(f"📥 [PROCESS] Processing: {url}")
    
    # 1. Extract ID
    regex = r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})"
    match = re.search(regex, url)
    if not match:
        match = re.search(r"([a-zA-Z0-9_-]{11})", url)
        if not match:
             raise Exception("Could not extract video ID")
    
    video_id = match.group(1)
    logger.info(f"📥 Video ID: {video_id}")
    
    # 2. Get Metadata (Soft Fail - Don't crash here!)
    try:
        meta = await get_video_info(video_id)
        logger.info(f"✅ Metadata: {meta['title']} - Duration: {meta['duration']}s")
    except Exception as e:
        logger.error(f"Metadata failed: {e}")
        meta = {
            "title": "Music Track",
            "duration": 0,
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        }
    
    title = meta['title']
    duration = meta['duration']
    
    # 3. Get Stream URL from API (WITH RETRY!)
    stream_url, api_title, error = await get_stream_link(video_id)
    
    if error:
        # Log detailed error
        logger.error(f"API Error for {video_id}: {error}")
        raise Exception(error)
    
    if not stream_url:
        raise Exception("API returned empty audio URL")
    
    # Validate stream URL
    if not stream_url.startswith('http'):
        logger.error(f"Invalid stream URL: {stream_url}")
        raise Exception("API returned invalid download URL")
    
    # Use API title if metadata failed
    if title.startswith("Music Track") and api_title:
        title = api_title
        logger.info(f"Using API title: {title}")

    # 4. Download the File (WITH RETRY!)
    file_path = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp3")
    
    # Check if already downloaded and valid
    if os.path.exists(file_path) and os.path.getsize(file_path) > 100000:  # > 100KB
        logger.info(f"✅ Using cached file: {title}")
        return {
            'title': title,
            'duration': duration,
            'file_path': file_path,
            'url': f"https://www.youtube.com/watch?v={video_id}",
            'thumbnail': meta['thumbnail'],
            'vidid': video_id
        }
    
    # Download with retry
    logger.info(f"📥 Downloading from: {stream_url[:100]}")
    max_retries = 2  # Reduced to 2 for faster failure
    
    for attempt in range(max_retries):
        try:
            headers = {
                "x-api-key": API_KEY,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "*/*",
                "Connection": "keep-alive"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    stream_url, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=90),  # Increased timeout
                    allow_redirects=True
                ) as resp:
                    
                    # Log response details
                    logger.info(f"Download response: {resp.status} - Content-Type: {resp.content_type}")
                    
                    if resp.status == 200:
                        # Download in chunks
                        with open(file_path, 'wb') as f:
                            downloaded = 0
                            chunk_count = 0
                            async for chunk in resp.content.iter_chunked(1024*512):  # 512KB chunks
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    chunk_count += 1
                                    if chunk_count % 10 == 0:  # Log every ~5MB
                                        logger.info(f"Downloaded: {downloaded / 1024 / 1024:.2f}MB")
                        
                        # Verify download
                        file_size = os.path.getsize(file_path)
                        logger.info(f"✅ Download complete: {file_size / 1024 / 1024:.2f}MB")
                        
                        if file_size > 50000:  # > 50KB
                            break
                        else:
                            logger.warning(f"File too small: {file_size} bytes")
                            raise Exception("Downloaded file is too small (corrupted)")
                    
                    elif resp.status == 400:
                        error_text = await resp.text()
                        logger.error(f"API 400 Error: {error_text[:200]}")
                        raise Exception(
                            "This video cannot be downloaded. It may be:\n"
                            "• Age-restricted or private\n"
                            "• Geo-blocked in your region\n"
                            "• Removed or unavailable\n"
                            "Try a different song!"
                        )
                    elif resp.status == 403:
                        raise Exception("Access forbidden (403). API key issue or video blocked.")
                    elif resp.status == 404:
                        raise Exception("Audio not found (404). Video may be unavailable.")
                    elif resp.status == 500:
                        if attempt < max_retries - 1:
                            logger.warning(f"API 500 error, retry {attempt + 1}/{max_retries}")
                            await asyncio.sleep(3)
                            continue
                        raise Exception("API server error (500). Try again later.")
                    else:
                        raise Exception(f"Download failed: HTTP {resp.status}")
        
        except asyncio.TimeoutError:
            if attempt < max_retries - 1:
                logger.warning(f"Timeout, retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(2)
                continue
            raise Exception("Download timeout. Check your internet or try again.")
        
        except aiohttp.ClientError as e:
            if attempt < max_retries - 1:
                logger.warning(f"Network error: {e}, retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(2)
                continue
            raise Exception(f"Network error: {str(e)[:80]}")
        
        except Exception as e:
            error_str = str(e)
            if "too small" in error_str or "corrupted" in error_str:
                if attempt < max_retries - 1:
                    logger.warning(f"Corrupted download, retry {attempt + 1}/{max_retries}")
                    await asyncio.sleep(2)
                    continue
            raise e

    # 5. Final verification
    if not os.path.exists(file_path):
        raise Exception("Download failed: File was not created")
    
    file_size = os.path.getsize(file_path)
    if file_size < 50000:
        logger.error(f"File too small: {file_size} bytes")
        raise Exception("Download failed: File is corrupted or incomplete")

    # 6. Return Data
    logger.info(f"✅ Ready to play: {title}")
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
