#!/bin/bash

# sync.sh - Easy file synchronization script for dashboard
# Usage: ./sync.sh [local|server|both]

set -e  # Exit on any error

# Default to 'both' if no argument provided
TARGET=${1:-both}

# Validate target argument
if [[ "$TARGET" != "local" && "$TARGET" != "server" && "$TARGET" != "both" ]]; then
    echo "Error: Invalid target '$TARGET'"
    echo "Usage: $0 [local|server|both]"
    echo ""
    echo "  local  - Sync to local dashboard only (starts local server)"
    echo "  server - Sync to Railway production only"
    echo "  both   - Sync to both local and Railway (starts local server)"
    exit 1
fi

echo "🚀 Starting dashboard sync with target: $TARGET"

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    if [[ -n "$UVICORN_PID" ]]; then
        echo "Stopping local server (PID: $UVICORN_PID)"
        kill $UVICORN_PID 2>/dev/null || true
        wait $UVICORN_PID 2>/dev/null || true
    fi
    exit 0
}

# Set up cleanup trap
trap cleanup SIGINT SIGTERM

# Check if we need to start local server
if [[ "$TARGET" == "local" || "$TARGET" == "both" ]]; then
    echo "📡 Starting local dashboard server..."
    
    # Navigate to railway-app directory and start uvicorn in background
    cd ../railway-app
    
    # Check if virtual environment activation is needed
    if [[ -z "$VIRTUAL_ENV" ]]; then
        echo "🐍 Activating virtual environment..."
        source ~/Projects/ius/venv/bin/activate
    fi
    
    # Start uvicorn in background
    uvicorn main:app --reload --port 8000 &
    UVICORN_PID=$!
    
    echo "✅ Local server started (PID: $UVICORN_PID)"
    echo "🌐 Dashboard available at: http://localhost:8000"
    
    # Wait a moment for server to start
    echo "⏳ Waiting for server to start..."
    sleep 3
    
    # Test if server is responding
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Local server is responding"
    else
        echo "⚠️  Local server may still be starting up..."
    fi
    
    # Navigate back to watcher directory
    cd ../watcher
else
    echo "⏭️  Skipping local server (target is 'server' only)"
fi

# Ensure we're in the watcher directory
cd "$(dirname "$0")"

# Check if virtual environment activation is needed
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "🐍 Activating virtual environment..."
    source ~/Projects/ius/venv/bin/activate
fi

echo "👀 Starting file watcher..."
echo "📁 Monitoring directories for changes..."
echo "🎯 Target: $TARGET"
echo ""
echo "Press Ctrl+C to stop"

# Start the watcher (this will run in foreground)
python main.py --target "$TARGET"