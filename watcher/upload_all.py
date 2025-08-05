#!/usr/bin/env python3
"""
One-time upload script to upload all existing files to Railway.
"""

import json
import requests
from pathlib import Path
from config import RAILWAY_URL, PROJECT_ROOT, WATCHED_DIRS

def upload_file(file_path: Path, relative_path: str):
    """Upload a single file to Railway."""
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
        
        response = requests.post(f"{RAILWAY_URL}/upload", files=files, data=data)
        files['file'].close()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Uploaded: {relative_path} ({result['size']} bytes)")
            return True
        else:
            print(f"❌ Failed: {relative_path} - {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error uploading {relative_path}: {e}")
        return False

def main():
    """Upload all existing files."""
    print(f"🚀 Uploading files to: {RAILWAY_URL}")
    print(f"📁 Project root: {PROJECT_ROOT}")
    
    total_files = 0
    uploaded_files = 0
    
    for watch_dir in WATCHED_DIRS:
        watch_path = PROJECT_ROOT / watch_dir
        if not watch_path.exists():
            print(f"⚠️ Directory doesn't exist: {watch_path}")
            continue
            
        print(f"\n📂 Processing: {watch_path}")
        
        # Find all JSON files
        for file_path in watch_path.rglob("*.json"):
            total_files += 1
            relative_path = file_path.relative_to(PROJECT_ROOT)
            
            if upload_file(file_path, relative_path):
                uploaded_files += 1
    
    print(f"\n🎉 Done! Uploaded {uploaded_files}/{total_files} files")
    print(f"🌐 Check your dashboard: {RAILWAY_URL}")

if __name__ == "__main__":
    main()