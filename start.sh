#!/bin/bash
set -e

echo "🚀 HEROKU STARTUP: Initializing RustyPipe Botguard..."

# Download the botguard binary
BOTGUARD_PATH="/app/rustypipe-botguard"
BOTGUARD_URL="https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-linux-x86_64"

if [ ! -f "$BOTGUARD_PATH" ]; then
    echo "📥 Downloading rustypipe-botguard..."
    
    # Try with curl first
    if curl -L -f -o "$BOTGUARD_PATH" "$BOTGUARD_URL" --max-time 60 --retry 3; then
        echo "✅ Downloaded with curl"
    else
        # Fallback to wget
        echo "⚠️  curl failed, trying wget..."
        if wget -O "$BOTGUARD_PATH" "$BOTGUARD_URL" --timeout=60 --tries=3; then
            echo "✅ Downloaded with wget"
        else
            echo "❌ Both curl and wget failed"
            echo "⚠️  Bot will run without RustyPipe (shorter lifespan)"
            # Don't exit, let bot try to run anyway
        fi
    fi
else
    echo "✅ Botguard already exists"
fi

# Make executable
if [ -f "$BOTGUARD_PATH" ]; then
    chmod +x "$BOTGUARD_PATH"
    
    # Test if it works
    if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
        echo "✅ Botguard is working!"
    else
        echo "⚠️  Botguard test failed (may still work)"
    fi
    
    # CRITICAL: Export environment variable
    export RUSTYPIPE_BOTGUARD_PATH="$BOTGUARD_PATH"
    export YT_DLP_RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
    export RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
    
    echo "✅ Environment variables set:"
    echo "   RUSTYPIPE_BOTGUARD_PATH=$RUSTYPIPE_BOTGUARD_PATH"
    echo "   YT_DLP_RUSTYPIPE_BOTGUARD=$YT_DLP_RUSTYPIPE_BOTGUARD"
    echo "   RUSTYPIPE_BOTGUARD=$RUSTYPIPE_BOTGUARD"
else
    echo "⚠️  No botguard binary available"
fi

echo ""
echo "🎵 Starting Music Bot..."
echo "================================================"

# Start the bot with environment variables preserved
exec python3 -m Yumeko
