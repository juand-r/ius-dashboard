#!/usr/bin/env python3
"""
Sync deletions between local filesystem and dashboard servers.
This script finds files that exist on the server but not locally and removes them.
"""

import argparse
import requests
import logging
import os
from pathlib import Path
from config import get_target_urls, PROJECT_ROOT, WATCHED_DIRS
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# For local development, files are actually stored in railway-app/data/
DASHBOARD_ROOT = Path(__file__).parent.parent
LOCAL_DATA_DIR = DASHBOARD_ROOT / "railway-app" / "data"

# Authentication credentials
AUTH_USERNAME = os.getenv('PROTECTED_CONTENT_USERNAME', 'researcher')
AUTH_PASSWORD_HASH = os.getenv('PROTECTED_CONTENT_PASSWORD_HASH')
PROTECTED_DATASETS = (os.getenv('PROTECTED_DATASETS', 'detectiveqa')).split(',')

# Global password storage
_auth_password = None
_auth_failed = False

def is_protected_path(file_path):
    """Check if a file path contains protected dataset content."""
    return any(dataset.strip() in file_path for dataset in PROTECTED_DATASETS)

def get_auth_for_url(target_url, file_path=None):
    """Get authentication for protected content requests."""
    global _auth_password, _auth_failed
    
    # Only require auth for proxy servers (localhost:3000 or railway.app) AND protected content
    needs_auth = ('localhost:3000' in target_url or 'railway.app' in target_url)
    
    if not needs_auth:
        return None
    
    # If we have a file path, check if it's protected content
    if file_path and not is_protected_path(file_path):
        return None
    
    # If we previously failed auth, don't keep trying
    if _auth_failed:
        return None
    
    # Get password if we don't have it
    if not _auth_password:
        print(f"⚠️  Authentication required for protected content on {target_url}")
        _auth_password = input("Enter password: ").strip()
        if not _auth_password:
            _auth_failed = True
            return None
    
    return HTTPBasicAuth(AUTH_USERNAME, _auth_password)

def set_auth_password(password):
    """Set the authentication password globally."""
    global _auth_password
    _auth_password = password


def get_local_files():
    """Get set of all local files that should be tracked (ONLY from source directories)."""
    local_files = set()
    
    # Only check the original source directories (NOT the local dashboard data)
    for watch_dir in WATCHED_DIRS:
        watch_path = PROJECT_ROOT / watch_dir
        if watch_path.exists():
            # Find all .json and .txt files
            for pattern in ["**/*.json", "**/*.txt"]:
                for file_path in watch_path.glob(pattern):
                    if file_path.is_file():
                        relative_path = str(file_path.relative_to(PROJECT_ROOT))
                        local_files.add(relative_path)
    
    return local_files


def get_server_files(target_url):
    """Get set of all files on the server."""
    try:
        logger.info(f"Fetching file list from {target_url}")
        # /api/files endpoint doesn't need auth (it just lists files, doesn't serve content)
        response = requests.get(f"{target_url}/api/files", timeout=30)
        
        # If we get 401, try with auth (in case the server requires it)
        if response.status_code == 401:
            logger.info("File listing requires authentication, trying with credentials...")
            auth = get_auth_for_url(target_url)
            response = requests.get(f"{target_url}/api/files", timeout=30, auth=auth)
        
        if response.status_code != 200:
            logger.error(f"Failed to get file list from {target_url}: {response.status_code}")
            return set()
        
        data = response.json()
        server_files = set()
        
        def extract_files(node, current_path=""):
            """Recursively extract file paths from the tree structure."""
            if node.get("type") == "file":
                # Add the full path
                full_path = f"{current_path}/{node['name']}" if current_path else node['name']
                server_files.add(full_path)
            elif node.get("type") == "directory":
                # Recurse into children
                dir_path = f"{current_path}/{node['name']}" if current_path else node['name']
                for child in node.get("children", []):
                    extract_files(child, dir_path)
        
        # The response is a single root object, not an array
        if isinstance(data, dict):
            # Process the children of the root directory
            for item in data.get("children", []):
                extract_files(item)
        else:
            logger.error(f"Unexpected response format from {target_url}: {type(data)}")
            return set()
        
        logger.info(f"Found {len(server_files)} files on {target_url}")
        return server_files
        
    except Exception as e:
        logger.error(f"Error fetching file list from {target_url}: {e}")
        return set()


def delete_file_from_server(target_url, file_path):
    """Delete a single file from the server."""
    try:
        logger.info(f"Deleting {file_path} from {target_url}")
        # Check if this specific file needs authentication
        auth = get_auth_for_url(target_url, file_path)
        response = requests.delete(f"{target_url}/api/files/{file_path}", timeout=30, auth=auth)
        
        if response.status_code == 200:
            logger.info(f"✅ Successfully deleted: {file_path}")
            return True
        elif response.status_code == 404:
            logger.info(f"ℹ️  File not found (already deleted): {file_path}")
            return True
        else:
            logger.error(f"❌ Delete failed: {file_path} - {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error deleting {file_path}: {e}")
        return False


def sync_deletions(target_urls, dry_run=False):
    """Sync deletions for all target URLs."""
    local_files = get_local_files()
    logger.info(f"Found {len(local_files)} local files")
    
    for target_url in target_urls:
        logger.info(f"\n🎯 Processing {target_url}")
        
        # Get files on server
        server_files = get_server_files(target_url)
        if not server_files:
            logger.warning(f"No files found on {target_url}, skipping...")
            continue
        
        # Find files to delete (on server but not local)
        files_to_delete = server_files - local_files
        
        if not files_to_delete:
            logger.info(f"✅ {target_url} is already in sync (no files to delete)")
            continue
        
        logger.info(f"📋 Found {len(files_to_delete)} files to delete from {target_url}:")
        for file_path in sorted(files_to_delete):
            logger.info(f"  - {file_path}")
        
        if dry_run:
            logger.info(f"🔍 DRY RUN: Would delete {len(files_to_delete)} files from {target_url}")
            continue
        
        # Confirm deletion
        if len(files_to_delete) > 0:
            print(f"\n⚠️  About to delete {len(files_to_delete)} files from {target_url}")
            print("Files to delete:")
            for file_path in sorted(list(files_to_delete)[:10]):  # Show first 10
                print(f"  - {file_path}")
            if len(files_to_delete) > 10:
                print(f"  ... and {len(files_to_delete) - 10} more")
            
            confirm = input(f"\nProceed with deletion? [y/N]: ").strip().lower()
            if confirm != 'y':
                logger.info("❌ Deletion cancelled by user")
                continue
        
        # Delete files
        success_count = 0
        for file_path in files_to_delete:
            if delete_file_from_server(target_url, file_path):
                success_count += 1
        
        logger.info(f"🎉 Deleted {success_count}/{len(files_to_delete)} files from {target_url}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sync file deletions between local and server")
    parser.add_argument(
        "--target", 
        required=True,
        choices=["local", "server", "both"],
        help="Target to sync deletions with: 'local' (localhost:8000), 'server' (Railway), or 'both'"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting anything"
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
    
    logger.info("🧹 Starting deletion sync")
    logger.info(f"Target URLs: {', '.join(target_urls)}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Project Root: {PROJECT_ROOT}")
    logger.info(f"Watched Directories: {WATCHED_DIRS}")
    
    sync_deletions(target_urls, args.dry_run)
    
    logger.info("✅ Deletion sync completed")


if __name__ == "__main__":
    main()