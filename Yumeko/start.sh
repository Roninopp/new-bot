#!/bin/bash

echo "🚀 HEROKU STARTUP: Initializing RustyPipe..."

# 1. Download the binary (Using a specific known version based on logs)
# Note: Ensure v0.1.2 or the latest version tag is correct for your needs
if [ ! -f "rustypipe-botguard" ]; then
    echo "📥 Downloading RustyPipe Botguard..."
    wget -q https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-linux-x86_64 -O rustypipe-botguard
    
    # Fallback to GitHub if Codeberg fails
    if [ ! -s "rustypipe-botguard" ]; then
        echo "⚠️ Codeberg failed, trying GitHub mirror..."
        wget -q https://github.com/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-linux-x86_64 -O rustypipe-botguard
    fi
fi

# 2. Make it executable
chmod +x rustypipe-botguard

# 3. Export the path so yt-dlp can find it
# This is CRITICAL. The previous script failed because it only exported to ~/.profile
export RUSTYPIPE_BOTGUARD_PATH="$(pwd)/rustypipe-botguard"

echo "✅ Botguard Path set to: $RUSTYPIPE_BOTGUARD_PATH"

# 4. Start your bot
echo "🎵 Starting Music Bot..."
python3 main.py
