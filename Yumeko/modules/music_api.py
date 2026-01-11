import aiohttp
import logging
import re

# Set up logging
logger = logging.getLogger(__name__)

# YOUR API KEY (Directly added as requested)
API_KEY = "xbit_qxkNri00qFMQcYL3L1cOGML0qTTI5fJE"
BASE_URL = "https://tgapi.xbitcode.com"

async def get_stream_link(query_or_url: str):
    """
    1. Extracts Video ID from the user's input.
    2. Calls the XBitCode API to get the direct stream URL.
    """
    
    # --- Step 1: Extract Video ID ---
    video_id = None
    
    # Regex to find video ID from various YouTube URL formats
    regex = r"(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^\"&?\/\s]{11})"
    match = re.search(regex, query_or_url)
    
    if match:
        video_id = match.group(1)
    else:
        # If it's not a link, assume it's a search query (Simple extraction won't work)
        # For this API test, tell the user to provide a LINK, 
        # OR you need to keep your old 'search_youtube' function just to get the ID.
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
                
                # Check for errors
                if response.status == 403:
                    return None, "❌ API Key is invalid or blocked!"
                if response.status == 429:
                    return None, "❌ Daily Request Limit Reached (100/100)!"
                if response.status != 200:
                    return None, f"❌ API Error: HTTP {response.status}"

                data = await response.json()
                
                # Check API Status
                if data.get("status") == "success":
                    audio_url = data.get("audio_url")
                    title = data.get("title", "Unknown Title") # API might return title, or not
                    
                    logger.info(f"✅ API Success! Got Audio URL.")
                    return audio_url, title
                else:
                    error_message = data.get("message", "Unknown API error")
                    return None, f"❌ API Failed: {error_message}"

        except Exception as e:
            logger.error(f"❌ Connection Error: {e}")
            return None, f"❌ Connection Error: {e}"
