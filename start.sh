#!/bin/bash

echo "🚀 HEROKU STARTUP: Initializing RustyPipe..."

# Define file path
BP="rustypipe-botguard"

# 1. Clean up potential bad downloads from previous failed runs
rm -f $BP

# 2. Download from Codeberg (Primary) - Using -L for redirects and User-Agent to avoid blocks
echo "📥 Downloading RustyPipe Botguard (Primary)..."
curl -L -A "Mozilla/5.0" -o $BP "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-linux-x86_64"

# 3. Validation: Check if file is a valid binary
# We check if the file exists AND if it can print its version
chmod +x $BP
if ./$BP --version > /dev/null 2>&1; then
    echo "✅ RustyPipe Binary is valid!"
    ./$BP --version
else
    echo "⚠️ Primary download failed or invalid. Trying fallback..."
    rm -f $BP
    
    # Fallback to GitHub
    echo "📥 Downloading RustyPipe Botguard (Fallback)..."
    curl -L -A "Mozilla/5.0" -o $BP "https://github.com/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-linux-x86_64"
    
    chmod +x $BP
    if ./$BP --version > /dev/null 2>&1; then
        echo "✅ Fallback Binary is valid!"
    else
        echo "❌ CRITICAL: Could not download a valid RustyPipe binary."
        echo "⚠️ The bot will run, but music playback might fail."
    fi
fi

# 4. Export the path (Crucial step)
export RUSTYPIPE_BOTGUARD_PATH="$(pwd)/$BP"

echo "✅ Environment set: $RUSTYPIPE_BOTGUARD_PATH"

# 5. Start your bot
echo "🎵 Starting Music Bot..."
python3 -m Yumeko
