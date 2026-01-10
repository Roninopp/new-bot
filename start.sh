#!/bin/bash
set -e

echo "🚀 Starting Music Bot with RustyPipe Support..."
echo "================================================"

BOTGUARD_PATH="/app/rustypipe-botguard"

# Function to download and verify botguard
download_botguard() {
    echo "📥 Downloading rustypipe-botguard..."
    
    # CRITICAL: We need v1.x for yt-dlp compatibility
    # The v0.1.x versions from Codeberg are INCOMPATIBLE
    
    # Source 1: nickshanks347 fork (v1.x compatible)
    echo "📥 Trying nickshanks347 release (v1.x)..."
    if curl -L -f -o "$BOTGUARD_PATH" \
        "https://github.com/nickshanks347/rustypipe-botguard/releases/download/v1.0.1/rustypipe-botguard-x86_64-unknown-linux-musl" \
        --max-time 120 --retry 3 2>/dev/null; then
        chmod +x "$BOTGUARD_PATH"
        if "$BOTGUARD_PATH" --version 2>&1 | grep -q "1\."; then
            echo "✅ Downloaded v1.x from nickshanks347"
            return 0
        fi
    fi
    
    # Source 2: ytdl-patched fork
    echo "📥 Trying ytdl-patched release..."
    if curl -L -f -o "$BOTGUARD_PATH" \
        "https://github.com/nickshanks347/rustypipe-botguard/releases/latest/download/rustypipe-botguard-x86_64-unknown-linux-musl" \
        --max-time 120 --retry 3 2>/dev/null; then
        chmod +x "$BOTGUARD_PATH"
        if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
            echo "✅ Downloaded from ytdl-patched"
            return 0
        fi
    fi
    
    # Source 3: Try glibc version instead of musl
    echo "📥 Trying glibc version..."
    if curl -L -f -o "$BOTGUARD_PATH" \
        "https://github.com/nickshanks347/rustypipe-botguard/releases/download/v1.0.1/rustypipe-botguard-x86_64-unknown-linux-gnu" \
        --max-time 120 --retry 3 2>/dev/null; then
        chmod +x "$BOTGUARD_PATH"
        if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
            echo "✅ Downloaded glibc version"
            return 0
        fi
    fi
    
    echo "❌ All download sources failed"
    return 1
}

# Function to verify botguard is working and compatible
verify_botguard() {
    if [ ! -f "$BOTGUARD_PATH" ]; then
        return 1
    fi
    
    if [ ! -x "$BOTGUARD_PATH" ]; then
        chmod +x "$BOTGUARD_PATH" 2>/dev/null || return 1
    fi
    
    # Test if it runs
    if ! "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
        return 1
    fi
    
    # Check version (we need v1.x)
    VERSION=$("$BOTGUARD_PATH" --version 2>&1 || echo "unknown")
    echo "📋 Botguard version: $VERSION"
    
    if echo "$VERSION" | grep -q "v1\." || echo "$VERSION" | grep -q "1\."; then
        echo "✅ Version is compatible (v1.x)"
        return 0
    elif echo "$VERSION" | grep -q "v0\."; then
        echo "⚠️  Version v0.x detected - may not work with yt-dlp"
        echo "⚠️  yt-dlp requires rustypipe-botguard v1.x"
        return 1
    fi
    
    # Unknown version, try anyway
    return 0
}

# Main logic
echo ""
echo "🔍 Checking existing botguard..."

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

# Final status
echo ""
echo "================================================"
if [ -f "$BOTGUARD_PATH" ] && [ -x "$BOTGUARD_PATH" ]; then
    # Set environment variables
    export RUSTYPIPE_BOTGUARD_PATH="$BOTGUARD_PATH"
    export YT_DLP_RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
    export RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
    export RUSTYPIPE_BOTGUARD_BINARY="$BOTGUARD_PATH"
    
    echo "✅ RustyPipe Botguard: READY"
    echo "📂 Path: $BOTGUARD_PATH"
    echo "🔧 Environment variables set"
    
    # Show version
    VERSION=$("$BOTGUARD_PATH" --version 2>&1 || echo "unknown")
    echo "📋 Version: $VERSION"
else
    echo "⚠️  RustyPipe Botguard: NOT AVAILABLE"
    echo "⚠️  Bot will rely on cookies only"
    echo "⚠️  This may cause faster cookie expiration"
fi
echo "================================================"
echo ""

# Verify cookies exist
if [ -f "/app/cookies.txt" ]; then
    COOKIE_SIZE=$(stat -f%z "/app/cookies.txt" 2>/dev/null || stat -c%s "/app/cookies.txt" 2>/dev/null || echo "0")
    echo "🍪 Cookies: Found (/app/cookies.txt, ${COOKIE_SIZE} bytes)"
else
    echo "⚠️  Cookies: NOT FOUND"
    echo "⚠️  Music playback will likely fail without cookies"
fi
echo ""

echo "🎵 Starting Python Bot..."
echo "================================================"

# Start bot with environment preserved
exec python3 -m Yumeko
