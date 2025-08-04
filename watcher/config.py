"""Configuration for the file watcher."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Railway app URL - change this to your deployed Railway URL
RAILWAY_URL = os.getenv("RAILWAY_URL", "http://localhost:8000")

# Directories to watch (relative to project root)
WATCHED_DIRS = [
    "outputs/chunks",
    "outputs/summaries", 
    "prompts"
]

# Debounce time to wait after file changes before uploading (seconds)
DEBOUNCE_SECONDS = 2

# Project root directory (sister directory to ius-dashboard/)
PROJECT_ROOT = Path(__file__).parent.parent.parent / "ius"

# File patterns to watch (empty list means all files)
# You can add patterns like ["*.json", "*.txt"] to limit file types
WATCH_PATTERNS = []

# File patterns to ignore
IGNORE_PATTERNS = [
    "*.tmp",
    "*.temp", 
    ".DS_Store",
    "*.swp",
    "*.lock"
]

# Maximum file size to upload (in bytes) - 50MB default
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")