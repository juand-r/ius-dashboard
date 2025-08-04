# Dashboard System

Automated file watcher and web dashboard for monitoring outputs and prompts.

## Quick Start

### 1. Setup Railway App (Local Testing)
```bash
cd ius-dashboard/railway-app
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Setup Local Watcher
```bash
cd ius-dashboard/watcher
pip install -r requirements.txt
cp env-template .env
# Edit .env if needed (default uses localhost:8000 for local testing)
```

### 3. Start the Watcher (Background Mode)
```bash
# From ius-dashboard/watcher directory
# Activate the Python virtual environment first:
source ../../ius/venv/bin/activate

# Start watcher in background to continuously monitor files:
python main.py &

# The watcher will now run in the background and automatically upload 
# any new/modified files from the ius project to your dashboard
```

### 4. Test the System
```bash
# Create a test file in the monitored ius directory
cd ../../ius  # Navigate to your main ius project
echo '{"test": "watcher working", "timestamp": "'$(date)'"}' > outputs/summaries/watcher-test.json

# Check watcher logs - should show file upload
# Visit http://localhost:8000 (local) or your Railway URL to see the file
```

### 5. Deploy to Railway
```bash
# From the ius-dashboard/ directory
railway link    # Link to your Railway project
railway up      # Deploy the app

# Update watcher config to use your Railway URL
# Edit ius-dashboard/watcher/.env:
# RAILWAY_URL=https://your-app.railway.app

# Restart watcher with Railway URL:
cd watcher
python main.py &
```

## Architecture

```
Local Files (ius/) → File Watcher → HTTP Upload → Railway Dashboard → Web UI
```

**Directory Structure:**
```
Projects/
├── ius/                          ← Your main project
│   ├── outputs/chunks/           ← Monitored
│   ├── outputs/summaries/        ← Monitored  
│   └── prompts/                  ← Monitored
└── ius-dashboard/                ← Dashboard system (sister directory)
    ├── watcher/                  ← File monitoring service
    └── railway-app/              ← Web dashboard
```

**Watched Directories** (relative to `ius/` project):
- `outputs/chunks/`
- `outputs/summaries/`
- `prompts/`

## Components

- **watcher/**: Local file monitoring and upload service
- **railway-app/**: Web dashboard hosted on Railway
- **railway-app/data/**: Storage location for uploaded files (Railway volume)

## Stopping the Watcher

To stop the background watcher:
```bash
# Find the process ID
ps aux | grep "python.*main.py" | grep -v grep

# Kill the process (replace XXXX with the actual PID)
kill XXXX
```

See `watch-server-plan.md` for detailed architecture and implementation plan.