#!/usr/bin/env python3
"""
One-time upload script to upload all existing files to target(s).
"""

import argparse
import json
import requests
import os
from pathlib import Path
from config import get_target_urls, PROJECT_ROOT, WATCHED_DIRS, WATCH_PATTERNS
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

def upload_file_to_target(file_path: Path, relative_path: str, target_url: str):
    """Upload a single file to a specific target."""
    try:
        # Determine collection from path
        collection = "unknown"
        if "chunks" in str(relative_path):
            collection = "chunks"
        elif "prompts" in str(relative_path):
            collection = "prompts"
        elif "summaries" in str(relative_path):
            collection = "summaries"
        
        files = {'file': open(file_path, 'rb')}
        data = {
            'path': str(relative_path),
            'collection': collection,
            'timestamp': '2025-08-05T02:00:00'
        }
        
        # Get authentication if needed for protected content
        auth = get_auth_for_upload(target_url, relative_path)
        response = requests.post(f"{target_url}/upload", files=files, data=data, auth=auth)
        files['file'].close()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Uploaded to {target_url}: {relative_path} ({result['size']} bytes)")
            return True
        else:
            print(f"❌ Failed to upload to {target_url}: {relative_path} - {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error uploading {relative_path} to {target_url}: {e}")
        return False

def upload_file(file_path: Path, relative_path: str, target_urls: list):
    """Upload a single file to all specified targets."""
    success_count = 0
    for target_url in target_urls:
        if upload_file_to_target(file_path, relative_path, target_url):
            success_count += 1
    
    return success_count == len(target_urls)

def main():
    """Upload all existing files."""
    parser = argparse.ArgumentParser(description="Upload all existing files to target(s)")
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
    
    print(f"🚀 Uploading files to: {', '.join(target_urls)}")
    print(f"📁 Project root: {PROJECT_ROOT}")
    
    total_files = 0
    uploaded_files = 0
    
    for watch_dir in WATCHED_DIRS:
        watch_path = PROJECT_ROOT / watch_dir
        if not watch_path.exists():
            print(f"⚠️ Directory doesn't exist: {watch_path}")
            continue
            
        print(f"\n📂 Processing: {watch_path}")
        
        # Find all files matching watch patterns
        all_files = []
        for pattern in WATCH_PATTERNS:
            all_files.extend(watch_path.rglob(pattern))
        
        for file_path in all_files:
            total_files += 1
            relative_path = file_path.relative_to(PROJECT_ROOT)
            
            if upload_file(file_path, relative_path, target_urls):
                uploaded_files += 1
    
    print(f"\n🎉 Done! Uploaded {uploaded_files}/{total_files} files")
    print(f"🌐 Target(s): {', '.join(target_urls)}")

if __name__ == "__main__":
    main()