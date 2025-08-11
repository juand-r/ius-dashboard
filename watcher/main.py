"""
File Watcher Service

Monitors specified directories for file changes and automatically uploads
files to target dashboard(s).
"""

import os
import sys
import time
import logging
import threading
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Set, List

import requests
from requests.auth import HTTPBasicAuth
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env vars

from config import (
    get_target_urls, WATCHED_DIRS, DEBOUNCE_SECONDS, PROJECT_ROOT,
    WATCH_PATTERNS, IGNORE_PATTERNS, MAX_FILE_SIZE, LOG_LEVEL
)

# Authentication credentials
AUTH_USERNAME = os.getenv('PROTECTED_CONTENT_USERNAME', 'researcher')
PROTECTED_DATASETS = (os.getenv('PROTECTED_DATASETS', 'detectiveqa')).split(',')

# Global password storage
_auth_password = None

def is_protected_path(file_path):
    """Check if a file path contains protected dataset content."""
    return any(dataset.strip() in str(file_path) for dataset in PROTECTED_DATASETS)

def get_auth_for_upload(target_url, file_path):
    """Get authentication for protected content uploads."""
    global _auth_password
    
    # Only require auth for proxy servers AND protected content
    needs_proxy_auth = ('localhost:3000' in target_url or 'railway.app' in target_url)
    
    if not needs_proxy_auth or not is_protected_path(file_path):
        return None
    
    # Get password if we don't have it
    if not _auth_password:
        print(f"⚠️  Authentication required for protected content upload to {target_url}")
        _auth_password = input("Enter password: ").strip()
        if not _auth_password:
            return None
    
    return HTTPBasicAuth(AUTH_USERNAME, _auth_password)

def set_auth_password(password):
    """Set the authentication password globally."""
    global _auth_password
    _auth_password = password

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
    """Handles file system events and uploads files to target dashboard(s)."""
    
    def __init__(self, target_urls: List[str]):
        super().__init__()
        self.target_urls = target_urls
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
            logger.debug(f"Skipping file (doesn't match criteria): {filepath}")
            return
        
        logger.info(f"File {event_type}: {filepath}")
        logger.debug(f"Processing file: {filepath}")
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
    
    def upload_file_to_target(self, filepath: str, target_url: str):
        """Upload file to a specific target."""
        try:
            path_obj = Path(filepath)
            if not path_obj.exists():
                logger.warning(f"File no longer exists, skipping upload: {filepath}")
                return False
            
            relative_path = self.get_relative_path(filepath)
            collection = self.detect_collection(relative_path)
            
            logger.info(f"Uploading file to {target_url}: {relative_path} (collection: {collection})")
            
            # Prepare upload data
            upload_data = {
                'path': relative_path,
                'collection': collection,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Read and upload file
            with open(filepath, 'rb') as file:
                files = {'file': file}
                auth = get_auth_for_upload(target_url, relative_path)
                response = requests.post(
                    f"{target_url}/upload",
                    files=files,
                    data=upload_data,
                    auth=auth,
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully uploaded to {target_url}: {relative_path}")
                    return True
                else:
                    logger.error(f"Upload failed to {target_url} for {relative_path}: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error uploading {filepath} to {target_url}: {str(e)}")
            return False

    def upload_file(self, filepath: str):
        """Upload file to all target dashboards."""
        success_count = 0
        for target_url in self.target_urls:
            if self.upload_file_to_target(filepath, target_url):
                success_count += 1
        
        if success_count == len(self.target_urls):
            self.processed_files.add(filepath)
            logger.info(f"Successfully uploaded to all targets: {filepath}")
        else:
            logger.error(f"Failed to upload to some targets: {filepath} ({success_count}/{len(self.target_urls)} succeeded)")
    
    def delete_file(self, filepath: str):
        """Delete file from all target dashboards."""
        relative_path = self.get_relative_path(filepath)
        success_count = 0
        
        for target_url in self.target_urls:
            try:
                logger.info(f"Deleting file from {target_url}: {relative_path}")
                
                # Send DELETE request to dashboard
                response = requests.delete(
                    f"{target_url}/api/files/{relative_path}",
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully deleted from {target_url}: {relative_path}")
                    success_count += 1
                elif response.status_code == 404:
                    logger.info(f"File not found in {target_url} (already deleted): {relative_path}")
                    success_count += 1  # Count 404 as success
                else:
                    logger.error(f"Delete failed from {target_url} for {relative_path}: {response.status_code} - {response.text}")
                    
            except Exception as e:
                logger.error(f"Error deleting {filepath} from {target_url}: {str(e)}")
        
        if success_count == len(self.target_urls):
            # Remove from processed files set if it was there
            self.processed_files.discard(filepath)
            logger.info(f"Successfully deleted from all targets: {filepath}")
        else:
            logger.error(f"Failed to delete from some targets: {filepath} ({success_count}/{len(self.target_urls)} succeeded)")


def setup_watchers(target_urls: List[str]) -> Observer:
    """Setup file system watchers for all configured directories."""
    observer = Observer()
    handler = FileUploadHandler(target_urls)
    
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
    parser = argparse.ArgumentParser(description="File watcher service for dashboard synchronization")
    parser.add_argument(
        "--target", 
        required=True,
        choices=["local", "server", "both"],
        help="Target to upload to: 'local' (localhost:8000), 'server' (Railway), or 'both'"
    )
    parser.add_argument(
        "--password",
        help="Password for protected content authentication (will prompt if not provided)"
    )
    
    args = parser.parse_args()
    target_urls = get_target_urls(args.target)
    
    # Set password if provided
    if args.password:
        set_auth_password(args.password)
    
    logger.info("Starting File Watcher Service")
    logger.info(f"Target URLs: {', '.join(target_urls)}")
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info(f"Watched Directories: {WATCHED_DIRS}")
    
    # Test connection to all targets
    for target_url in target_urls:
        try:
            response = requests.get(f"{target_url}/health", timeout=5)
            if response.status_code != 200:
                logger.warning(f"Target health check failed for {target_url}: {response.status_code}")
            else:
                logger.info(f"Successfully connected to {target_url}")
        except Exception as e:
            logger.error(f"Cannot connect to {target_url}: {e}")
            logger.info("The watcher will still run, but uploads to this target will fail until it's available")
    
    # Setup and start watchers
    observer = setup_watchers(target_urls)
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