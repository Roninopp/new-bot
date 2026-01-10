#!/bin/bash
set -e

echo "🔥 Installing RustyPipe for auto po_token generation..."

# Check if rustypipe already exists
if [ -f "/app/rustypipe/target/release/rustypipe" ]; then
    echo "✅ RustyPipe already installed, testing..."
    /app/rustypipe/target/release/rustypipe --version && {
        echo "✅ RustyPipe working! Skipping reinstall."
        exit 0
    }
fi

# Install Rust if not present
if ! command -v cargo &> /dev/null; then
    echo "📦 Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source $HOME/.cargo/env
    echo "✅ Rust installed!"
else
    echo "✅ Rust already installed"
    source $HOME/.cargo/env || true
fi

# Clone RustyPipe if not present
if [ ! -d "/app/rustypipe" ]; then
    echo "📥 Cloning RustyPipe repository..."
    cd /app
    git clone https://github.com/2bc4/rustypipe.git || {
        echo "⚠️  Git clone failed, trying alternative..."
        wget https://github.com/2bc4/rustypipe/archive/refs/heads/main.zip
        unzip main.zip
        mv rustypipe-main rustypipe
    }
    echo "✅ RustyPipe repository ready"
else
    echo "✅ RustyPipe repository already exists"
fi

# Build RustyPipe
echo "🔨 Building RustyPipe (this may take 2-3 minutes)..."
cd /app/rustypipe
cargo build --release --features youtube || {
    echo "❌ Build failed! Trying without features..."
    cargo build --release
}

# Verify build
if [ -f "/app/rustypipe/target/release/rustypipe" ]; then
    echo "✅ RustyPipe built successfully!"
    
    # Test it
    /app/rustypipe/target/release/rustypipe --version && {
        echo "✅ RustyPipe is working!"
    } || {
        echo "⚠️  RustyPipe binary exists but test failed"
    }
    
    # Try to generate a po_token
    echo "🎯 Testing po_token generation..."
    /app/rustypipe/target/release/rustypipe generate-po-token && {
        echo "✅ PO_TOKEN generation working!"
    } || {
        echo "⚠️  PO_TOKEN generation test failed (may work during runtime)"
    }
else
    echo "❌ RustyPipe build failed!"
    exit 1
fi

echo "✅ RustyPipe installation complete!"
