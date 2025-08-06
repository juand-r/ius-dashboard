#!/usr/bin/env python3
"""
One-time upload script to upload all existing files to target(s).
"""

import argparse
import json
import requests
from pathlib import Path
from config import get_target_urls, PROJECT_ROOT, WATCHED_DIRS

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
        
        response = requests.post(f"{target_url}/upload", files=files, data=data)
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
    
    args = parser.parse_args()
    target_urls = get_target_urls(args.target)
    
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
        
        # Find all JSON and TXT files
        for file_path in list(watch_path.rglob("*.json")) + list(watch_path.rglob("*.txt")):
            total_files += 1
            relative_path = file_path.relative_to(PROJECT_ROOT)
            
            if upload_file(file_path, relative_path, target_urls):
                uploaded_files += 1
    
    print(f"\n🎉 Done! Uploaded {uploaded_files}/{total_files} files")
    print(f"🌐 Target(s): {', '.join(target_urls)}")

if __name__ == "__main__":
    main()