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
    if [[ -n "$FASTAPI_PID" ]]; then
        echo "Stopping FastAPI backend (PID: $FASTAPI_PID)"
        kill $FASTAPI_PID 2>/dev/null || true
        wait $FASTAPI_PID 2>/dev/null || true
    fi
    if [[ -n "$EXPRESS_PID" ]]; then
        echo "Stopping Express proxy (PID: $EXPRESS_PID)"
        kill $EXPRESS_PID 2>/dev/null || true
        wait $EXPRESS_PID 2>/dev/null || true
    fi
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
    echo "📡 Starting local dashboard servers..."
    
    # Navigate to project root
    cd ..
    
    # Check if virtual environment activation is needed
    if [[ -z "$VIRTUAL_ENV" ]]; then
        echo "🐍 Activating virtual environment..."
        source ~/Projects/ius/venv/bin/activate
    fi
    
    # Install Node.js dependencies if needed
    if [[ ! -d "node_modules" ]]; then
        echo "📦 Installing Node.js dependencies..."
        npm install
    fi
    
    # Start FastAPI backend in background (port 8000)
    echo "🔧 Starting FastAPI backend on port 8000..."
    cd railway-app
    uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
    FASTAPI_PID=$!
    
    # Start Express proxy server in background (port 3000)
    echo "🔒 Starting Express proxy server on port 3000..."
    cd ..
    FASTAPI_PORT=8000 node server.js &
    EXPRESS_PID=$!
    UVICORN_PID=$EXPRESS_PID  # For cleanup compatibility
    
    echo "✅ FastAPI backend started (PID: $FASTAPI_PID)"
    echo "✅ Express proxy started (PID: $EXPRESS_PID)"
    echo "🌐 Dashboard available at: http://localhost:3000"
    echo "🔒 DetectiveQA content requires authentication"
    
    # Wait a moment for servers to start
    echo "⏳ Waiting for servers to start..."
    sleep 5
    
    # Test if proxy server is responding
    if curl -s http://localhost:3000/health > /dev/null 2>&1; then
        echo "✅ Proxy server is responding"
    else
        echo "⚠️  Servers may still be starting up..."
    fi
    
    # Navigate to watcher directory
    cd watcher
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