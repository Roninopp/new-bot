#!/bin/bash
# Simple script - RustyPipe support is built into yt-dlp
# We just need to install the botguard binary

echo "🔥 Setting up YouTube access with RustyPipe support..."

# Install rustypipe-botguard binary for yt-dlp
echo "📥 Installing rustypipe-botguard..."
cd /app

# Download botguard
wget -q https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v1.0.0/rustypipe-botguard-linux-x86_64 -O rustypipe-botguard 2>/dev/null || {
    echo "⚠️  Primary download failed, trying mirror..."
    wget -q https://github.com/ThetaDev/rustypipe-botguard/releases/download/v1.0.0/rustypipe-botguard-linux-x86_64 -O rustypipe-botguard 2>/dev/null || {
        echo "⚠️  Botguard download failed (yt-dlp will work without it)"
        echo "⚠️  Bot will use cookies only"
        exit 0  # Don't fail, just warn
    }
}

if [ -f "/app/rustypipe-botguard" ]; then
    chmod +x rustypipe-botguard
    echo "✅ Botguard installed at /app/rustypipe-botguard"
    
    # Set environment variable for yt-dlp
    export RUSTYPIPE_BOTGUARD_PATH="/app/rustypipe-botguard"
    echo "export RUSTYPIPE_BOTGUARD_PATH='/app/rustypipe-botguard'" >> ~/.profile 2>/dev/null || true
    
    # Test if it works
    ./rustypipe-botguard --help >/dev/null 2>&1 && {
        echo "✅ Botguard is executable and working!"
    } || {
        echo "⚠️  Botguard may not work on this system"
    }
else
    echo "⚠️  Botguard not available"
fi

echo "✅ Setup complete!"
echo ""
echo "📊 Status:"
if [ -f "/app/rustypipe-botguard" ]; then
    echo "  • RustyPipe Botguard: ✅ Installed"
    echo "  • Location: /app/rustypipe-botguard"
else
    echo "  • RustyPipe Botguard: ⚠️  Not installed"
fi

if [ -f "/app/cookies.txt" ]; then
    echo "  • Cookies: ✅ Available"
else
    echo "  • Cookies: ⚠️  Not found"
fi

echo ""
echo "ℹ️  Note: yt-dlp has RustyPipe support built-in!"
echo "ℹ️  The botguard binary helps with signature challenges"
