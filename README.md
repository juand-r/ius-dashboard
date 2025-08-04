# Dashboard System

Automated file watcher and web dashboard for monitoring outputs and prompts.

## Quick Start

### 1. Setup Railway App (Local Testing)
```bash
cd dashboard/railway-app
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Setup Local Watcher
```bash
cd dashboard/watcher
pip install -r requirements.txt
cp env-template .env
# Edit .env if needed (default uses localhost:8000)
python main.py
```

### 3. Test the System
```bash
# In another terminal, create a test file to trigger the watcher
mkdir -p outputs/summaries/test-collection
echo '{"test": "data", "timestamp": "2024-01-15"}' > outputs/summaries/test-collection/test.json

# Check watcher logs - should show file upload
# Visit http://localhost:8000 to see the file in dashboard
```

### 4. Deploy to Railway
```bash
# From the dashboard/ directory
railway link    # Link to your Railway project
railway up      # Deploy the app

# Update watcher config with your Railway URL
# Edit dashboard/watcher/.env:
# RAILWAY_URL=https://your-app.railway.app
```

## Architecture

```
Local Files → File Watcher → HTTP Upload → Railway Dashboard → Web UI
```

**Watched Directories:**
- `outputs/chunks/`
- `outputs/summaries/`
- `prompts/`

## Components

- **watcher/**: Local file monitoring and upload service
- **railway-app/**: Web dashboard hosted on Railway
- **data/**: Storage location for uploaded files (Railway volume)

See `watch-server-plan.md` for detailed architecture and implementation plan.