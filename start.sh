import requests
import os
import sys

# Your Config
API_KEY = "xbit_qxkNri00qFMQcYL3L1cOGML0qTTI5fJE"
VIDEO_ID = "gEo8IrFbecM" # "Let me down slowly"
BASE_URL = "https://tgapi.xbitcode.com"

print(f"🚀 DIAGNOSTIC: Testing API Connection...")

# 1. Get Info
url = f"{BASE_URL}/info/{VIDEO_ID}"
headers = {"x-api-key": API_KEY}

try:
    print(f"🔹 Fetching metadata from: {url}")
    resp = requests.get(url, headers=headers, timeout=10)
    
    if resp.status_code != 200:
        print(f"❌ API Error: {resp.status_code} - {resp.text}")
        sys.exit(1)
        
    data = resp.json()
    if data.get("status") != "success":
        print(f"❌ API Logic Error: {data}")
        sys.exit(1)
        
    stream_url = data.get("audio_url")
    print(f"✅ API Success! Stream URL received.")
    print(f"🔗 URL: {stream_url[:50]}...") # Print first 50 chars
    
except Exception as e:
    print(f"❌ Connection Failed: {e}")
    sys.exit(1)

# 2. Test Stream Access (The Critical Part)
print(f"\n🚀 DIAGNOSTIC: Testing Stream Access...")
try:
    # Check for redirects (Is it sending us to googlevideo?)
    print("🔹 Checking for redirects...")
    stream_resp = requests.head(stream_url, headers=headers, allow_redirects=True)
    
    final_url = stream_resp.url
    print(f"📍 Final URL Domain: {final_url.split('/')[2]}")
    
    if "googlevideo.com" in final_url:
        print("❌ CRITICAL FAIL: The API redirects to YouTube (googlevideo.com).")
        print("⚠️ This link is IP-LOCKED to the API server.")
        print("⚠️ Your Heroku bot CANNOT play this because the IPs do not match.")
        print("💡 CONCLUSION: This API will NOT work on Heroku for streaming.")
    
    elif stream_resp.status_code == 200:
        print("✅ Stream is accessible (HTTP 200)!")
        print("💡 CONCLUSION: The API works. The issue is in your Music Player (PyTgCalls).")
    elif stream_resp.status_code == 403:
        print("❌ Stream returned 403 Forbidden.")
        print("💡 CONCLUSION: The stream requires the 'x-api-key' header, but FFmpeg isn't sending it.")
    else:
        print(f"⚠️ Stream returned unexpected status: {stream_resp.status_code}")

except Exception as e:
    print(f"❌ Stream Test Failed: {e}")
