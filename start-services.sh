#!/bin/bash

# Start services script for Railway deployment
# This script starts both the Express proxy server and FastAPI backend

echo "🚀 Starting IUS Dashboard services..."
echo "🌍 Environment: PORT=$PORT, FASTAPI_PORT=8000"
echo "📁 Current directory: $(pwd)"
echo "📋 Directory contents: $(ls -la)"

# Check if railway-app exists
if [ ! -d "railway-app" ]; then
    echo "❌ ERROR: railway-app directory not found!"
    exit 1
fi

# Check if requirements are installed
echo "🐍 Checking Python environment..."
python --version
which uvicorn || echo "⚠️  uvicorn not found in PATH"

# Start FastAPI in the background on port 8000
echo "📡 Starting FastAPI backend on port 8000..."
cd railway-app
echo "📁 FastAPI directory: $(pwd)"
echo "📋 FastAPI directory contents: $(ls -la)"

# Start FastAPI with output logging
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level debug > ../fastapi.log 2>&1 &
FASTAPI_PID=$!
cd ..

echo "🔍 FastAPI PID: $FASTAPI_PID"

# Wait a moment for FastAPI to start and check if it's running
sleep 5

# Check if FastAPI process is still running
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
    echo "❌ ERROR: FastAPI failed to start!"
    echo "📋 FastAPI logs:"
    cat fastapi.log
    exit 1
fi

# Test if FastAPI is actually responding
echo "🔍 Testing FastAPI connectivity..."
echo "📋 Current FastAPI logs:"
cat fastapi.log

for i in {1..15}; do
    if curl -s http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "✅ FastAPI health check passed"
        break
    elif [ $i -eq 15 ]; then
        echo "❌ ERROR: FastAPI health check failed after 15 attempts"
        echo "📋 Full FastAPI logs:"
        cat fastapi.log
        echo ""
        echo "🔍 Network diagnostics:"
        echo "Processes listening on port 8000:"
        netstat -tlnp 2>/dev/null | grep 8000 || echo "  No process listening on port 8000"
        echo "All listening processes:"
        netstat -tlnp 2>/dev/null | head -10
        echo "FastAPI process status:"
        if kill -0 $FASTAPI_PID 2>/dev/null; then
            echo "  FastAPI process $FASTAPI_PID is still running"
        else
            echo "  FastAPI process $FASTAPI_PID has died"
        fi
        exit 1
    else
        echo "⏳ Waiting for FastAPI to be ready... (attempt $i/15)"
        sleep 2
    fi
done

# Start Express proxy server on the main port
echo "🔒 Starting Express proxy server on port $PORT..."
export FASTAPI_PORT=8000
node server.js &
EXPRESS_PID=$!

# Function to cleanup processes on exit
cleanup() {
    echo "🛑 Shutting down services..."
    kill $FASTAPI_PID 2>/dev/null
    kill $EXPRESS_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait for Express server (main process)
wait $EXPRESS_PID