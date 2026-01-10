#!/bin/bash
# RustyPipe Botguard Installer for Heroku
# This downloads the correct binary and sets it up properly

echo "🔥 Setting up RustyPipe Botguard for YouTube access..."

# Download the correct version
echo "📥 Downloading rustypipe-botguard v0.1.2..."
curl -L -o /app/rustypipe-botguard \
  "https://codeberg.org/ThetaDev/rustypipe-botguard/releases/download/v0.1.2/rustypipe-botguard-linux-x86_64" \
  --max-time 60 \
  --retry 3 \
  --retry-delay 2

if [ -f "/app/rustypipe-botguard" ]; then
    # Make executable
    chmod +x /app/rustypipe-botguard
    
    # Test if it works
    if /app/rustypipe-botguard --version >/dev/null 2>&1; then
        echo "✅ RustyPipe Botguard installed and working!"
    else
        echo "⚠️  Binary downloaded but may not work"
    fi
    
    # Export environment variable
    export RUSTYPIPE_BOTGUARD_PATH="/app/rustypipe-botguard"
    echo "export RUSTYPIPE_BOTGUARD_PATH='/app/rustypipe-botguard'" >> ~/.profile
    echo "✅ Environment variable set"
else
    echo "❌ Failed to download botguard"
fi
