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

# Start watcher with target specification (required)
python main.py --target local    # For local development
python main.py --target server   # For Railway production
python main.py --target both     # For both targets
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
Local Files → File Watcher → HTTP Upload → Dashboard(s) → Web UI
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

### Sync Targets
The system now supports flexible synchronization to multiple targets:
- **`--target local`**: Sync only to local development server (localhost:8000)
- **`--target server`**: Sync only to Railway production server
- **`--target both`**: Sync to both local and production (keeps everything in sync)

This allows you to:
- Develop locally without affecting production
- Push directly to production when needed
- Keep both environments synchronized during development

**Watched Directories:**
- `outputs/chunks/`
- `outputs/summaries/`
- `prompts/`

## Components

- **watcher/**: Local file monitoring and upload service
- **railway-app/**: Web dashboard hosted on Railway
- **data/**: Storage location for uploaded files (Railway volume)

## Detective-Style Dashboard (New Interface)

The dashboard now features a modern, detective-style interface with 3-level navigation matching the detective dashboard design.

### Start Detective Dashboard
```bash
source ~/Projects/ius/venv/bin/activate && cd ~/Projects/ius-dashboard/railway-app && uvicorn main:app --reload --port 8000
```

### Start File Watcher (Multiple Target Options)
```bash
source ~/Projects/ius/venv/bin/activate && cd ~/Projects/ius-dashboard/watcher

# Sync to local dashboard only (for development)
python main.py --target local

# Sync to Railway production only
python main.py --target server

# Sync to both local and Railway (keep everything in sync)
python main.py --target both
```

### Bulk Upload Existing Files
If you need to upload all existing files (useful for initial setup or after changes):
```bash
source ~/Projects/ius/venv/bin/activate && cd ~/Projects/ius-dashboard/watcher

# Upload all files to local dashboard only
python upload_all.py --target local

# Upload all files to Railway production only  
python upload_all.py --target server

# Upload all files to both targets
python upload_all.py --target both
```

### Sync Deletions (Clean Up Orphaned Files)
If you've deleted files from your source directories but they still exist on the dashboard servers, use this script to clean them up:
```bash
source ~/Projects/ius/venv/bin/activate && cd ~/Projects/ius-dashboard/watcher

# Preview what would be deleted (safe dry-run)
python sync_deletions.py --target both --dry-run

# Actually delete orphaned files from local dashboard only
python sync_deletions.py --target local

# Actually delete orphaned files from Railway production only
python sync_deletions.py --target server

# Actually delete orphaned files from both dashboards
python sync_deletions.py --target both
```

**How it works:**
- Compares files in your source directories (`~/Projects/ius/outputs/`) with what's on the dashboard servers
- Identifies "orphaned" files that exist on servers but not in your source
- Safely removes these orphaned files via the dashboard's delete API
- **Never touches your source files** - they are read-only for comparison
- Perfect for cleaning up after you delete collections locally (e.g., removing test datasets)

**Always run with `--dry-run` first** to preview what will be deleted!

## Process Management

### Stopping the Watcher

To stop the background watcher:
```bash
# Find the process ID
ps aux | grep "python.*main.py" | grep -v grep

# Kill the process (replace XXXX with the actual PID)
kill XXXX
```

### Access Your Dashboard
- **New Interface**: http://localhost:8000 (Detective-style with collection tiles)
- **Legacy Interface**: http://localhost:8000/legacy (Original dashboard)

### Key Features
- **Landing Page**: Collection tiles for "Text Chunks" and "Prompts & Templates"
- **Collection Pages**: Item lists with search functionality  
- **Item Detail Pages**: Collapsible sections for content, metadata, and related files
- **Professional Design**: Matches detective dashboard aesthetic exactly

---

See `watch-server-plan.md` for detailed architecture and implementation plan.