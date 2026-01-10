#!/bin/bash
set -e

echo "🚀 Starting Music Bot with RustyPipe Support..."
echo "================================================"

BOTGUARD_PATH="/app/rustypipe-botguard"

# Function to download and extract botguard
download_botguard() {
    echo "📥 Downloading rustypipe-botguard..."
    
    # The Codeberg releases are .tar.xz files, we need to extract them
    TEMP_DIR="/tmp/botguard_download"
    mkdir -p "$TEMP_DIR"
    
    # Source 1: Codeberg v0.1.2 (latest stable)
    echo "📥 Trying Codeberg v0.1.2 (tar.xz)..."
    if curl -L -f -o "$TEMP_DIR/botguard.tar.xz" \
        "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-v0.1.2-x86_64-unknown-linux-gnu.tar.xz" \
        --max-time 120 --retry 3 2>/dev/null; then
        
        echo "📦 Extracting..."
        cd "$TEMP_DIR"
        if tar -xJf botguard.tar.xz 2>/dev/null; then
            # Find the binary
            EXTRACTED_BIN=$(find . -name "rustypipe-botguard" -type f 2>/dev/null | head -1)
            if [ -n "$EXTRACTED_BIN" ]; then
                mv "$EXTRACTED_BIN" "$BOTGUARD_PATH"
                chmod +x "$BOTGUARD_PATH"
                if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
                    echo "✅ Downloaded and extracted from Codeberg v0.1.2"
                    rm -rf "$TEMP_DIR"
                    return 0
                fi
            fi
        fi
    fi
    
    # Source 2: Try v0.1.1
    echo "📥 Trying Codeberg v0.1.1 (tar.xz)..."
    if curl -L -f -o "$TEMP_DIR/botguard.tar.xz" \
        "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.1/rustypipe-botguard-v0.1.1-x86_64-unknown-linux-gnu.tar.xz" \
        --max-time 120 --retry 3 2>/dev/null; then
        
        echo "📦 Extracting..."
        cd "$TEMP_DIR"
        if tar -xJf botguard.tar.xz 2>/dev/null; then
            EXTRACTED_BIN=$(find . -name "rustypipe-botguard" -type f 2>/dev/null | head -1)
            if [ -n "$EXTRACTED_BIN" ]; then
                mv "$EXTRACTED_BIN" "$BOTGUARD_PATH"
                chmod +x "$BOTGUARD_PATH"
                if "$BOTGUARD_PATH" --version >/dev/null 2>&1; then
                    echo "✅ Downloaded and extracted from Codeberg v0.1.1"
                    rm -rf "$TEMP_DIR"
                    return 0
                fi
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
    
    VERSION=$("$BOTGUARD_PATH" --version 2>&1 || echo "unknown")
    echo "📋 Botguard version: $VERSION"
    return 0
}

# Install yt-dlp plugin for PO token generation
install_pot_plugin() {
    echo ""
    echo "📦 Installing yt-dlp PO Token plugin..."
    
    # Install the official yt-dlp plugin for rustypipe-botguard
    if pip install yt-dlp-get-pot-rustypipe --break-system-packages -q 2>/dev/null; then
        echo "✅ yt-dlp-get-pot-rustypipe plugin installed"
        return 0
    else
        echo "⚠️  Could not install PO Token plugin"
        return 1
    fi
}

# Main logic
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

# Install the PO Token plugin
echo ""
echo "🔍 Step 2: Installing PO Token plugin..."
install_pot_plugin || true

# Update yt-dlp to latest
echo ""
echo "🔍 Step 3: Updating yt-dlp..."
pip install -U yt-dlp --break-system-packages -q 2>/dev/null && echo "✅ yt-dlp updated" || echo "⚠️  Could not update yt-dlp"

# Final status
echo ""
echo "================================================"
echo "📊 FINAL STATUS:"
echo "================================================"

if [ -f "$BOTGUARD_PATH" ] && [ -x "$BOTGUARD_PATH" ]; then
    # Set environment variables
    export RUSTYPIPE_BOTGUARD_PATH="$BOTGUARD_PATH"
    export YT_DLP_RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
    export RUSTYPIPE_BOTGUARD="$BOTGUARD_PATH"
    export RUSTYPIPE_BOTGUARD_BINARY="$BOTGUARD_PATH"
    
    echo "✅ RustyPipe Botguard: READY"
    echo "   📂 Path: $BOTGUARD_PATH"
    VERSION=$("$BOTGUARD_PATH" --version 2>&1 || echo "unknown")
    echo "   📋 Version: $VERSION"
else
    echo "⚠️  RustyPipe Botguard: NOT AVAILABLE"
    echo "   ⚠️  Bot will rely on cookies only"
fi

# Check cookies
if [ -f "/app/cookies.txt" ]; then
    COOKIE_SIZE=$(stat -c%s "/app/cookies.txt" 2>/dev/null || echo "0")
    echo "✅ Cookies: Found (/app/cookies.txt, ${COOKIE_SIZE} bytes)"
else
    echo "⚠️  Cookies: NOT FOUND"
fi

# Check yt-dlp version
YT_DLP_VERSION=$(yt-dlp --version 2>/dev/null || echo "unknown")
echo "✅ yt-dlp version: $YT_DLP_VERSION"

# Check if plugin is installed
if pip show yt-dlp-get-pot-rustypipe >/dev/null 2>&1; then
    echo "✅ PO Token plugin: Installed"
else
    echo "⚠️  PO Token plugin: Not installed"
fi

echo "================================================"
echo ""

echo "🎵 Starting Python Bot..."
echo "================================================"

# Start bot with environment preserved
exec python3 -m Yumeko
