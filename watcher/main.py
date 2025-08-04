"""
File Watcher Service

Monitors specified directories for file changes and automatically uploads
files to the Railway dashboard app.
"""

import os
import sys
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Set

import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

from config import (
    RAILWAY_URL, WATCHED_DIRS, DEBOUNCE_SECONDS, PROJECT_ROOT,
    WATCH_PATTERNS, IGNORE_PATTERNS, MAX_FILE_SIZE, LOG_LEVEL
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DebounceHandler:
    """Handles debouncing of file events to avoid multiple uploads for rapid changes."""
    
    def __init__(self, callback, delay: float):
        self.callback = callback
        self.delay = delay
        self.timers: Dict[str, threading.Timer] = {}
        self.lock = threading.Lock()
    
    def trigger(self, filepath: str):
        """Trigger callback after delay, canceling any previous timer for this file."""
        with self.lock:
            # Cancel existing timer for this file
            if filepath in self.timers:
                self.timers[filepath].cancel()
            
            # Create new timer
            timer = threading.Timer(self.delay, self.callback, args=[filepath])
            self.timers[filepath] = timer
            timer.start()
            
            logger.debug(f"Debounce timer set for {filepath} ({self.delay}s)")


class FileUploadHandler(FileSystemEventHandler):
    """Handles file system events and uploads files to Railway."""
    
    def __init__(self):
        super().__init__()
        self.debouncer = DebounceHandler(self.upload_file, DEBOUNCE_SECONDS)
        self.processed_files: Set[str] = set()
    
    def should_process_file(self, filepath: Path) -> bool:
        """Check if file should be processed based on patterns and filters."""
        # Check file size
        try:
            if filepath.stat().st_size > MAX_FILE_SIZE:
                logger.warning(f"File too large, skipping: {filepath} ({filepath.stat().st_size} bytes)")
                return False
        except OSError:
            return False
        
        # Check ignore patterns
        for pattern in IGNORE_PATTERNS:
            if filepath.match(pattern):
                logger.debug(f"File matches ignore pattern {pattern}, skipping: {filepath}")
                return False
        
        # Check watch patterns (if specified)
        if WATCH_PATTERNS:
            matches_pattern = any(filepath.match(pattern) for pattern in WATCH_PATTERNS)
            if not matches_pattern:
                logger.debug(f"File doesn't match watch patterns, skipping: {filepath}")
                return False
        
        return True
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            self.handle_file_event(event.src_path, "modified")
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self.handle_file_event(event.src_path, "created")
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            self.handle_delete_event(event.src_path)
    
    def handle_file_event(self, filepath: str, event_type: str):
        """Process a file event."""
        path_obj = Path(filepath)
        
        if not self.should_process_file(path_obj):
            return
        
        logger.info(f"File {event_type}: {filepath}")
        self.debouncer.trigger(filepath)
    
    def handle_delete_event(self, filepath: str):
        """Process a file deletion event."""
        relative_path = self.get_relative_path(filepath)
        logger.info(f"File deleted: {filepath}")
        
        # Use a small delay to ensure the file is actually deleted
        import threading
        timer = threading.Timer(1.0, self.delete_file, args=[filepath])
        timer.start()
    
    def get_relative_path(self, filepath: str) -> str:
        """Get path relative to project root."""
        try:
            return str(Path(filepath).relative_to(PROJECT_ROOT))
        except ValueError:
            # If file is not under PROJECT_ROOT, return absolute path
            return filepath
    
    def detect_collection(self, relative_path: str) -> str:
        """Extract collection name from path."""
        path_parts = Path(relative_path).parts
        
        # For outputs/summaries/collection_name/... -> collection_name
        if len(path_parts) >= 3 and path_parts[0] == "outputs":
            return path_parts[2]  # outputs/summaries/collection_name
        
        # For prompts/method_name/... -> method_name
        if len(path_parts) >= 2 and path_parts[0] == "prompts":
            return path_parts[1]
        
        # Default to directory name
        return path_parts[-2] if len(path_parts) > 1 else "unknown"
    
    def upload_file(self, filepath: str):
        """Upload file to Railway dashboard."""
        try:
            path_obj = Path(filepath)
            if not path_obj.exists():
                logger.warning(f"File no longer exists, skipping upload: {filepath}")
                return
            
            relative_path = self.get_relative_path(filepath)
            collection = self.detect_collection(relative_path)
            
            logger.info(f"Uploading file: {relative_path} (collection: {collection})")
            
            # Prepare upload data
            upload_data = {
                'path': relative_path,
                'collection': collection,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Read and upload file
            with open(filepath, 'rb') as file:
                files = {'file': file}
                response = requests.post(
                    f"{RAILWAY_URL}/upload",
                    files=files,
                    data=upload_data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully uploaded: {relative_path}")
                    self.processed_files.add(filepath)
                else:
                    logger.error(f"Upload failed for {relative_path}: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Error uploading {filepath}: {str(e)}")
    
    def delete_file(self, filepath: str):
        """Delete file from Railway dashboard."""
        try:
            relative_path = self.get_relative_path(filepath)
            
            logger.info(f"Deleting file from dashboard: {relative_path}")
            
            # Send DELETE request to dashboard
            response = requests.delete(
                f"{RAILWAY_URL}/api/files/{relative_path}",
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully deleted from dashboard: {relative_path}")
                # Remove from processed files set if it was there
                self.processed_files.discard(filepath)
            elif response.status_code == 404:
                logger.info(f"File not found in dashboard (already deleted): {relative_path}")
            else:
                logger.error(f"Delete failed for {relative_path}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Error deleting {filepath}: {str(e)}")


def setup_watchers() -> Observer:
    """Setup file system watchers for all configured directories."""
    observer = Observer()
    handler = FileUploadHandler()
    
    for watch_dir in WATCHED_DIRS:
        watch_path = PROJECT_ROOT / watch_dir
        
        if not watch_path.exists():
            logger.warning(f"Watch directory doesn't exist, creating: {watch_path}")
            watch_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Watching directory: {watch_path}")
        observer.schedule(handler, str(watch_path), recursive=True)
    
    return observer


def main():
    """Main entry point."""
    logger.info("Starting File Watcher Service")
    logger.info(f"Railway URL: {RAILWAY_URL}")
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info(f"Watched Directories: {WATCHED_DIRS}")
    
    # Test Railway connection
    try:
        response = requests.get(f"{RAILWAY_URL}/health", timeout=5)
        if response.status_code != 200:
            logger.warning(f"Railway app health check failed: {response.status_code}")
    except Exception as e:
        logger.error(f"Cannot connect to Railway app: {e}")
        logger.info("The watcher will still run, but uploads will fail until the Railway app is available")
    
    # Setup and start watchers
    observer = setup_watchers()
    observer.start()
    
    logger.info("File watcher started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping file watcher...")
        observer.stop()
    
    observer.join()
    logger.info("File watcher stopped.")


if __name__ == "__main__":
    main()