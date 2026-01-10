#!/bin/bash
set -e

echo "🚀 Starting Music Bot with RustyPipe Support..."
echo "================================================"

# CRITICAL: The botguard binary URL that actually works
BOTGUARD_PATH="/app/rustypipe-botguard"

# Try multiple sources for the botguard binary
download_botguard() {
    # Source 1: Latest GitHub release (most reliable)
    echo "📥 Trying GitHub releases..."
    if curl -L -f -o "$BOTGUARD_PATH" \
        "https://github.com/ytdl-patched/rustypipe-botguard/releases/latest/download/rustypipe-botguard-x86_64-unknown-linux-musl" \
        --max-time 60 --retry 2 2>/dev/null; then
        chmod +x "$BOTGUARD_PATH"
        if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
            echo "✅ Downloaded from GitHub (latest)"
            return 0
        fi
    fi
    
    # Source 2: Specific version from Codeberg
    echo "📥 Trying Codeberg v0.1.1..."
    if curl -L -f -o "$BOTGUARD_PATH" \
        "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.1/rustypipe-botguard-x86_64-unknown-linux-musl" \
        --max-time 60 --retry 2 2>/dev/null; then
        chmod +x "$BOTGUARD_PATH"
        if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
            echo "✅ Downloaded from Codeberg (v0.1.1)"
            return 0
        fi
    fi
    
    # Source 3: Alternative mirror
    echo "📥 Trying alternative source..."
    if wget -q -O "$BOTGUARD_PATH" \
        "https://github.com/ytdl-patched/rustypipe-botguard/releases/download/v0.1.1/rustypipe-botguard-x86_64-unknown-linux-musl" \
        --timeout=60 --tries=2 2>/dev/null; then
        chmod +x "$BOTGUARD_PATH"
        if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
            echo "✅ Downloaded from mirror"
            return 0
        fi
    fi
    
    echo "❌ All download sources failed"
    return 1
}

# Check if botguard already exists and works
if [ -f "$BOTGUARD_PATH" ]; then
    if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
        echo "✅ Existing botguard is working"
    else
        echo "⚠️  Existing botguard is corrupt, re-downloading..."
        rm -f "$BOTGUARD_PATH"
        download_botguard || echo "⚠️  Running without botguard"
    fi
else
    echo "📥 Botguard not found, downloading..."
    download_botguard || echo "⚠️  Running without botguard"
fi

# Verify final state
if [ -f "$BOTGUARD_PATH" ] && "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
    # CRITICAL: Set ALL possible environment variables
    export RUSTYPIPE_BOTGUARD_PATH="$BOTGUARD_PATH"
    export YT_DLP_RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
    export RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
    export RUSTYPIPE_BOTGUARD_BINARY="$BOTGUARD_PATH"
    
    echo ""
    echo "✅ RustyPipe Botguard Status: WORKING"
    echo "📂 Path: $BOTGUARD_PATH"
    echo "🔐 Environment variables set (4 variants)"
    echo ""
else
    echo ""
    echo "⚠️  RustyPipe Botguard Status: NOT AVAILABLE"
    echo "⚠️  Bot will use cookies only (shorter lifespan)"
    echo "⚠️  Music may fail on some videos"
    echo ""
fi

echo "🎵 Starting Python Bot..."
echo "================================================"

# Start bot with environment preserved
exec python3 -m Yumeko
