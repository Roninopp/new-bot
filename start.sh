#!/bin/bash

echo "🚀 HEROKU STARTUP: Initializing RustyPipe..."

# Use Python to download the binary (More reliable than curl/wget)
python3 -c "
import requests
import os
import sys

url = 'https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-linux-x86_64'
output = 'rustypipe-botguard'

print(f'📥 Downloading from {url}...')
try:
    response = requests.get(url, timeout=30, allow_redirects=True)
    response.raise_for_status()
    
    with open(output, 'wb') as f:
        f.write(response.content)
    
    # Make executable
    os.chmod(output, 0o755)
    print('✅ Download successful!')
except Exception as e:
    print(f'❌ Download failed: {e}')
    sys.exit(1)
"

# Validation: Check if it works
if ./rustypipe-botguard --version; then
    echo "✅ Binary is valid and executable!"
    export RUSTYPIPE_BOTGUARD_PATH="$(pwd)/rustypipe-botguard"
    echo "✅ Environment set: $RUSTYPIPE_BOTGUARD_PATH"
else
    echo "❌ CRITICAL: The downloaded binary is corrupt or invalid."
    # Don't exit, try to run the bot anyway just in case
fi

echo "🎵 Starting Music Bot..."
python3 -m Yumeko
