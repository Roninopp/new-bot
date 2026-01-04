#!/bin/bash
echo "📥 Installing RustyPipe for auto po_token generation..."

# Download RustyPipe
wget https://github.com/2bc4/rustypipe/releases/latest/download/rustypipe-x86_64-unknown-linux-gnu -O /app/rustypipe 2>/dev/null

# Make it executable
chmod +x /app/rustypipe

# Add to PATH
export PATH="/app:$PATH"

echo "✅ RustyPipe installed successfully!"
