#!/bin/bash
set -e

echo "🚀 Starting Music Bot with RustyPipe Support..."
echo "================================================"

# CRITICAL: Always work from /app
cd /app

BOTGUARD_PATH="/app/rustypipe-botguard"

# Function to download and extract botguard
download_botguard() {
    echo "📥 Downloading rustypipe-botguard..."
    
    TEMP_DIR="/tmp/botguard_download"
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
    
    # Source 1: Codeberg v0.1.2 (latest stable)
    echo "📥 Trying Codeberg v0.1.2 (tar.xz)..."
    if curl -L -f -o "$TEMP_DIR/botguard.tar.xz" \
        "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-v0.1.2-x86_64-unknown-linux-gnu.tar.xz" \
        --max-time 120 --retry 3 2>/dev/null; then
        
        echo "📦 Extracting..."
        # Extract in subshell to not change current directory
        (cd "$TEMP_DIR" && tar -xJf botguard.tar.xz 2>/dev/null) || true
        
        # Find the binary
        EXTRACTED_BIN=$(find "$TEMP_DIR" -name "rustypipe-botguard" -type f 2>/dev/null | head -1)
        if [ -n "$EXTRACTED_BIN" ] && [ -f "$EXTRACTED_BIN" ]; then
            cp "$EXTRACTED_BIN" "$BOTGUARD_PATH"
            chmod +x "$BOTGUARD_PATH"
            if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
                echo "✅ Downloaded and extracted from Codeberg v0.1.2"
                rm -rf "$TEMP_DIR"
                return 0
            fi
        fi
    fi
    
    # Source 2: Try v0.1.1
    echo "📥 Trying Codeberg v0.1.1 (tar.xz)..."
    if curl -L -f -o "$TEMP_DIR/botguard.tar.xz" \
        "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.1/rustypipe-botguard-v0.1.1-x86_64-unknown-linux-gnu.tar.xz" \
        --max-time 120 --retry 3 2>/dev/null; then
        
        echo "📦 Extracting..."
        (cd "$TEMP_DIR" && tar -xJf botguard.tar.xz 2>/dev/null) || true
        
        EXTRACTED_BIN=$(find "$TEMP_DIR" -name "rustypipe-botguard" -type f 2>/dev/null | head -1)
        if [ -n "$EXTRACTED_BIN" ] && [ -f "$EXTRACTED_BIN" ]; then
            cp "$EXTRACTED_BIN" "$BOTGUARD_PATH"
            chmod +x "$BOTGUARD_PATH"
            if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
                echo "✅ Downloaded and extracted from Codeberg v0.1.1"
                rm -rf "$TEMP_DIR"
                return 0
            fi
        fi
    fi
    
    rm -rf "$TEMP_DIR"
    echo "❌ All download sources failed"
    return 1
}

# Function to verify botguard
verify_botguard() {
    if [ ! -f "$BOTGUARD_PATH" ]; then
        return 1
    fi
    
    chmod +x "$BOTGUARD_PATH" 2>/dev/null || true
    
    if ! "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
        return 1
    fi
    
    VERSION=$("$BOTGUARD_PATH" --version 2>&1 | head -1 || echo "unknown")
    echo "📋 Botguard version: $VERSION"
    return 0
}

# Main logic - ALWAYS FROM /app
cd /app

echo ""
echo "🔍 Step 1: Checking existing botguard..."

if verify_botguard; then
    echo "✅ Existing botguard is working!"
else
    echo "⚠️  Botguard missing or incompatible, downloading..."
    rm -f "$BOTGUARD_PATH" 2>/dev/null
    
    if download_botguard; then
        if verify_botguard; then
            echo "✅ Botguard installed successfully!"
        else
            echo "⚠️  Downloaded but verification failed"
        fi
    else
        echo "⚠️  Could not download botguard"
    fi
fi

# CRITICAL: Ensure we're in /app
cd /app

# Create log.txt if it doesn't exist (fix for bot crash)
touch /app/log.txt 2>/dev/null || true

# Set environment variables
if [ -f "$BOTGUARD_PATH" ] && [ -x "$BOTGUARD_PATH" ]; then
    export RUSTYPIPE_BOTGUARD_PATH="$BOTGUARD_PATH"
    export YT_DLP_RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
    export RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
fi

# Final status
echo ""
echo "================================================"
echo "📊 FINAL STATUS:"
echo "================================================"

if [ -f "$BOTGUARD_PATH" ] && [ -x "$BOTGUARD_PATH" ]; then
    echo "✅ RustyPipe Botguard: READY"
    echo "   📂 Path: $BOTGUARD_PATH"
    VERSION=$("$BOTGUARD_PATH" --version 2>&1 | head -1 || echo "unknown")
    echo "   📋 Version: $VERSION"
else
    echo "⚠️  RustyPipe Botguard: NOT AVAILABLE"
    echo "   ⚠️  Bot will use TV/iOS client fallback"
fi

# Check cookies
if [ -f "/app/cookies.txt" ]; then
    COOKIE_SIZE=$(stat -c%s "/app/cookies.txt" 2>/dev/null || echo "0")
    echo "✅ Cookies: Found (${COOKIE_SIZE} bytes)"
else
    echo "⚠️  Cookies: NOT FOUND"
fi

# Check yt-dlp version
YT_DLP_VERSION=$(yt-dlp --version 2>/dev/null || echo "unknown")
echo "✅ yt-dlp version: $YT_DLP_VERSION"

echo "📂 Working directory: $(pwd)"

echo "================================================"
echo ""

echo "🎵 Starting Python Bot..."
echo "================================================"

# CRITICAL: Make sure we're in /app before starting Python
cd /app

# Start bot
exec python3 -m Yumeko
