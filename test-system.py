#!/usr/bin/env python3
"""
Test script for the dashboard system.

Creates test files in the watched directories to verify the watcher
and dashboard are working correctly.
"""

import json
import time
from pathlib import Path
from datetime import datetime

# Test data templates
TEST_DATA = {
    "collection": {
        "name": "test-collection",
        "created": datetime.utcnow().isoformat() + "Z",
        "description": "Test collection for dashboard system",
        "total_items": 2
    },
    "summary": {
        "id": "test-summary-001",
        "text": "This is a test summary to verify the dashboard system is working correctly.",
        "metadata": {
            "method": "test-method",
            "model": "test-model",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        "chunks": [
            {"id": 1, "text": "First chunk of test data"},
            {"id": 2, "text": "Second chunk of test data"}
        ],
        "statistics": {
            "word_count": 15,
            "character_count": 89,
            "processing_time": 1.23
        }
    },
    "chunk": {
        "id": "test-chunk-001", 
        "content": "This is a test chunk created to verify the file watcher system.",
        "metadata": {
            "source": "test-document",
            "position": 0,
            "size": 67,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    },
    "prompt": {
        "name": "test-prompt",
        "template": "Test prompt template: {input_text}",
        "parameters": {
            "max_tokens": 100,
            "temperature": 0.7
        },
        "created": datetime.utcnow().isoformat() + "Z"
    }
}

def create_test_files():
    """Create test files in watched directories."""
    base_path = Path(__file__).parent.parent
    
    # Test directories and files to create
    test_files = [
        ("outputs/summaries/test-collection/collection.json", TEST_DATA["collection"]),
        ("outputs/summaries/test-collection/items/summary-001.json", TEST_DATA["summary"]),
        ("outputs/chunks/test-chunks/collection.json", {"name": "test-chunks", "total_items": 1}),
        ("outputs/chunks/test-chunks/items/chunk-001.json", TEST_DATA["chunk"]),
        ("prompts/test-method/prompt.json", TEST_DATA["prompt"]),
    ]
    
    print("🧪 Creating test files for dashboard system...")
    
    for file_path, data in test_files:
        full_path = base_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Created: {file_path}")
        time.sleep(0.5)  # Small delay to see individual uploads
    
    print("\n📊 Test files created! Check your dashboard and watcher logs.")
    print("🌐 Dashboard should be available at: http://localhost:8000")

def cleanup_test_files():
    """Remove test files."""
    base_path = Path(__file__).parent.parent
    
    test_dirs = [
        "outputs/summaries/test-collection",
        "outputs/chunks/test-chunks", 
        "prompts/test-method"
    ]
    
    print("🧹 Cleaning up test files...")
    
    for dir_path in test_dirs:
        full_path = base_path / dir_path
        if full_path.exists():
            import shutil
            shutil.rmtree(full_path)
            print(f"🗑️  Removed: {dir_path}")
    
    print("✨ Cleanup complete!")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cleanup":
        cleanup_test_files()
    else:
        create_test_files()
        print("\n💡 To cleanup test files later, run: python test-system.py cleanup")