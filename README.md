# Dashboard System

Automated file watcher and web dashboard for monitoring outputs and prompts with HTTP Basic Auth protection for sensitive content.

## Quick Start

### 1. Setup Authentication (Required)
```bash
# Install Node.js dependencies first
npm install

# Generate password hash for protected content
node generate-password.js
# Enter your desired password when prompted
# Copy the generated environment variables

# Create .env file in project root with the generated values
echo "PROTECTED_CONTENT_USERNAME=researcher" > .env
echo "PROTECTED_CONTENT_PASSWORD_HASH=your-generated-hash" >> .env
echo "PROTECTED_DATASETS=detectiveqa,booookscore" >> .env
echo "FASTAPI_PORT=8000" >> .env
```

**Important:** Never commit the `.env` file to version control - it contains sensitive credentials.

### 2. Setup Local Development
```bash
# Install Python dependencies
cd railway-app && pip install -r requirements.txt && cd ..

# Start the dashboard and file watcher
cd watcher
./sync.sh local    # Starts Express proxy (port 3000), FastAPI (port 8000), and file watcher
```

**What this does:**
- Starts Express proxy server on `http://localhost:3000` (main dashboard access)
- Starts FastAPI backend on `http://localhost:8000` (internal, for debugging)
- Starts file watcher monitoring `~/Projects/ius/outputs/` and `~/Projects/ius/prompts/`
- All services stop when you press Ctrl+C

### 3. Test the System
```bash
# In another terminal, create a test file to trigger the watcher
mkdir -p outputs/summaries/test-collection
echo '{"test": "data", "timestamp": "2024-01-15"}' > outputs/summaries/test-collection/test.json

# Check watcher logs - should show file upload
# Visit http://localhost:3000 to see the file in dashboard
# DetectiveQA content will require authentication
```

### 4. Deploy to Railway
```bash
# Set environment variables in Railway dashboard under "Variables":
# PROTECTED_CONTENT_USERNAME=researcher
# PROTECTED_CONTENT_PASSWORD_HASH=your-bcrypt-hash-from-step-1
# PROTECTED_DATASETS=detectiveqa,booookscore

# Deploy the application
git add .
git commit -m "Deploy with authentication"
railway up

# Start syncing files to Railway (optional)
cd watcher
./sync.sh server    # Syncs files to Railway only
./sync.sh both      # Syncs to both local and Railway
```

## Architecture

```
Local Files → File Watcher → HTTP Upload → Express Proxy → FastAPI Dashboard → Web UI
                                            ↓
                                    HTTP Basic Auth
                                  (DetectiveQA only)
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

### Authentication System

The dashboard includes HTTP Basic Auth protection for sensitive content:

**Protected Content:**
- Configurable via `PROTECTED_DATASETS` environment variable
- Default: DetectiveQA data files (`/data/outputs/chunks/detectiveqa*`)
- Default: DetectiveQA summaries (`/data/outputs/summaries/detectiveqa*`)
- Default: DetectiveQA API endpoints (`/api/*detectiveqa*`)

**Authentication Flow:**
1. Visit protected content (dashboard loads normally)
2. When accessing protected data, browser shows auth dialog
3. Enter credentials once per session
4. All protected data loads normally afterward

**Local Development:**
- Dashboard runs on `http://localhost:3000` (Express proxy)
- FastAPI backend runs on `http://localhost:8000` (internal)
- Authentication required only for datasets in `PROTECTED_DATASETS`

**Adding More Protected Datasets:**
```bash
# Protect multiple datasets (comma-separated)
PROTECTED_DATASETS=detectiveqa,anotherdataset,thirddataset
```

### Sync Targets
The system supports flexible synchronization to multiple targets:
- **`--target local`**: Sync to local development (Express proxy on localhost:3000)
- **`--target server`**: Sync to Railway production server  
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

## Command Line Tools

The system includes several CLI tools for managing files and synchronization:

### File Watcher (`sync.sh`)
**Recommended way to start the system:**
```bash
cd watcher
./sync.sh local     # Local development (starts all services)
./sync.sh server    # Sync to Railway only (watcher only)
./sync.sh both      # Sync to both local and Railway
```

### Bulk Upload (`upload_all.py`)
**Upload existing files to dashboard:**
```bash
cd watcher
python upload_all.py --target local                    # Upload all files locally
python upload_all.py --target server --password pwd    # Upload to Railway with auth
python upload_all.py --target both                     # Upload to both targets
```

### Sync Deletions (`sync_deletions.py`)
**Clean up orphaned files on servers:**
```bash
cd watcher
python sync_deletions.py --target local --dry-run      # Preview deletions
python sync_deletions.py --target local                # Delete orphaned files
python sync_deletions.py --target both --password pwd  # Clean both targets
```

**Authentication Notes:**
- Password only required for **protected datasets** (`detectiveqa`, `booookscore`)
- Unprotected datasets (`bmds`, `squality`) work without authentication
- Scripts will prompt for password if needed and not provided via `--password`

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

## Authentication System

The dashboard uses HTTP Basic Auth to protect sensitive datasets containing copyrighted content.

### Protected Content
**Datasets requiring authentication:**
- `detectiveqa` - Detective fiction stories (copyrighted)
- `booookscore` - Additional protected dataset
- Any datasets listed in `PROTECTED_DATASETS` environment variable

**Unprotected content** (no authentication required):
- `bmds` - Public domain stories
- `squality` - Project Gutenberg stories  
- `prompts` - Research prompts and configurations

### How Authentication Works
1. **Dashboard Access**: Visit protected dataset pages (e.g., `/detectiveqa`)
2. **Browser Prompt**: Native HTTP Basic Auth dialog appears
3. **Enter Credentials**: Username `researcher` + your password
4. **Session Persists**: Navigate freely within protected areas
5. **Automatic Protection**: All protected data endpoints require authentication

### Managing Passwords
```bash
# Generate new password hash
node generate-password.js

# Update local environment
# Edit .env file with new PROTECTED_CONTENT_PASSWORD_HASH

# Update Railway environment
# Set new hash in Railway dashboard under "Variables"
```

### Adding More Protected Datasets
```bash
# Update environment variable (comma-separated)
PROTECTED_DATASETS=detectiveqa,booookscore,newdataset

# Restart services to apply changes
cd watcher && ./sync.sh local
```

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
- **Main Dashboard**: http://localhost:3000 (Express proxy with authentication)
- **Direct FastAPI**: http://localhost:8000 (Internal backend, for debugging only)
- **Legacy Interface**: http://localhost:3000/legacy (Original dashboard)

### Key Features
- **Landing Page**: Collection tiles for "Text Chunks" and "Prompts & Templates"
- **Collection Pages**: Item lists with search functionality  
- **Item Detail Pages**: Collapsible sections for content, metadata, and related files
- **Professional Design**: Matches detective dashboard aesthetic exactly

---

See `watch-server-plan.md` for detailed architecture and implementation plan.