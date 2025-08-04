# Watch Server Dashboard - MVP Plan

## Overview

Self-contained dashboard system that watches local directories and automatically uploads files to a Railway-hosted dashboard for 24/7 access.

## Architecture

```
Local Files → File Watcher → HTTP Upload → Railway Dashboard → Web UI
```

**Key Directories Watched:**
- `outputs/chunks/`
- `outputs/summaries/` 
- `prompts/`

## Directory Structure

```
dashboard/
├── watch-server-plan.md          # This plan
├── watcher/                       # Local file watcher
│   ├── main.py                   # Main watcher script
│   ├── config.py                 # Configuration
│   └── requirements.txt          # Dependencies
├── railway-app/                   # Railway dashboard app
│   ├── main.py                   # FastAPI app
│   ├── templates/                # HTML templates
│   │   └── dashboard.html        # Main dashboard UI
│   ├── static/                   # CSS/JS assets
│   │   ├── style.css
│   │   └── dashboard.js
│   ├── data/                     # Uploaded files storage
│   └── requirements.txt          # Dependencies
├── railway.toml                   # Railway config
└── README.md                     # Setup instructions
```

## Components

### 1. Local File Watcher (`watcher/`)

**Purpose:** Monitor directories and upload files to Railway

**Key Features:**
- Watch for file creation/modification in target directories
- Debounce rapid changes (2-second delay)
- Upload complete file content to Railway
- Handle JSON files and any other file types
- Configurable Railway URL endpoint

**Dependencies:**
- `watchdog` - File system monitoring
- `requests` - HTTP uploads
- `python-dotenv` - Environment config

**Configuration:**
```python
RAILWAY_URL = "https://your-app.railway.app"
WATCHED_DIRS = ["outputs/chunks", "outputs/summaries", "prompts"]
DEBOUNCE_SECONDS = 2
```

### 2. Railway Dashboard App (`railway-app/`)

**Purpose:** Receive uploads and serve web dashboard

**Key Features:**
- `POST /upload` - Receive file uploads from watcher
- `GET /` - Serve dashboard HTML
- `GET /api/files` - List all stored files (JSON API)
- `GET /api/content/{path}` - Serve file content
- Store files in persistent volume (`/data/`)

**Tech Stack:**
- FastAPI - Web framework
- Jinja2 - HTML templates
- Basic HTML/CSS/JS - Dashboard UI

**API Endpoints:**
```
POST /upload
  - multipart/form-data
  - file: file content
  - path: relative path from project root
  - collection: auto-detected from path

GET /api/files
  - Returns JSON tree of all stored files
  - Includes metadata (size, timestamp, collection)

GET /api/content/{path:path}
  - Returns raw file content
  - Auto-detects content-type

GET /
  - Dashboard web interface
```

### 3. Dashboard UI

**Layout:**
- Left panel: File tree (collapsible directories)
- Right panel: File content viewer
- Top bar: Search/filter controls

**Features:**
- JSON syntax highlighting
- Collapsible JSON objects (starts collapsed)
- File tree navigation
- Auto-refresh (poll for new files every 30 seconds)
- Search/filter by filename or collection

## Implementation Phases

### Phase 1: Basic Upload System
1. Create watcher that uploads files to Railway endpoint
2. Create Railway app that receives and stores files
3. Basic file listing API

### Phase 2: Web Dashboard
1. HTML dashboard with file tree
2. JSON viewer with syntax highlighting
3. Basic navigation between files

### Phase 3: Polish
1. Auto-refresh functionality
2. Search and filtering
3. Better JSON collapse/expand
4. Error handling and logging

## Setup Instructions

### Local Development
1. `cd dashboard/watcher`
2. `pip install -r requirements.txt`
3. Create `.env` with `RAILWAY_URL=http://localhost:8000`
4. Run railway app locally: `cd ../railway-app && uvicorn main:app --reload`
5. Run watcher: `python main.py`

### Production Deployment
1. Deploy railway-app to Railway
2. Update watcher `.env` with production Railway URL
3. Run watcher locally (monitors your local files)

## File Upload Format

**Watcher → Railway POST:**
```
POST /upload
Content-Type: multipart/form-data

file: [binary file content]
path: "outputs/summaries/bmds_fixed_size_8000_ASH03/items/ASH03.json"
timestamp: "2024-01-15T10:30:00Z"
```

**Railway Storage:**
```
/data/outputs/summaries/bmds_fixed_size_8000_ASH03/items/ASH03.json
```

## MVP Success Criteria

1. ✅ Watcher detects file changes in target directories
2. ✅ Files automatically uploaded to Railway  
3. ✅ Dashboard shows file tree of uploaded files
4. ✅ Click file to view JSON content with basic formatting
5. ✅ Dashboard accessible 24/7 via Railway URL
6. ✅ No manual intervention required

## Future Enhancements

- Real-time updates (WebSocket instead of polling)
- File deletion handling
- Bulk upload/download
- Authentication for private dashboards
- Charts/visualizations for summary data
- Export functionality
- File diff/comparison tools