#!/bin/bash

echo "🚀 HEROKU STARTUP: Initializing..."

# 1. Install RustyPipe (Just in case we need it later)
python3 -c "
import requests, os
url = 'https://github.com/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-linux-x86_64'
output = 'rustypipe-botguard'
if not os.path.exists(output):
    print('📥 Downloading Botguard...')
    r = requests.get(url, allow_redirects=True)
    with open(output, 'wb') as f: f.write(r.content)
    os.chmod(output, 0o755)
"
export RUSTYPIPE_BOTGUARD_PATH="$(pwd)/rustypipe-botguard"

# 2. Run the Diagnostic Script FIRST
echo "🔍 Running API Diagnostic..."
python3 debug_api.py

# 3. Start the Bot (Optional: Comment this out if you only want to test)
# echo "🎵 Starting Music Bot..."
# python3 main.py
