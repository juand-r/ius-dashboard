"""
Railway Dashboard App

Web dashboard that receives file uploads from the watcher and serves
a web interface for viewing files and their contents.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import aiofiles

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="File Dashboard", description="Automated file monitoring dashboard")

# Storage directory for uploaded files
DATA_DIR = Path("/data")  # Railway persistent volume
if not DATA_DIR.exists():
    # Fallback for local development
    DATA_DIR = Path(__file__).parent / "data"
    DATA_DIR.mkdir(exist_ok=True)

logger.info(f"Using data directory: {DATA_DIR}")

# Setup templates and static files
templates = Jinja2Templates(directory="templates")

# Create static directory if it doesn't exist
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint for the watcher to test connectivity."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    path: str = Form(...),
    collection: str = Form(...),
    timestamp: str = Form(...)
):
    """
    Receive file uploads from the watcher.
    
    Args:
        file: The uploaded file
        path: Relative path from project root
        collection: Collection name (auto-detected by watcher)
        timestamp: Upload timestamp
    """
    try:
        # Create target directory
        target_path = DATA_DIR / path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save file
        async with aiofiles.open(target_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        file_size = len(content)
        
        logger.info(f"Uploaded file: {path} ({file_size} bytes, collection: {collection})")
        
        return {
            "status": "success",
            "path": path,
            "size": file_size,
            "collection": collection,
            "timestamp": timestamp
        }
        
    except Exception as e:
        logger.error(f"Upload failed for {path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/files")
async def list_files():
    """
    Return a JSON tree of all stored files with metadata.
    """
    try:
        file_tree = build_file_tree(DATA_DIR)
        return JSONResponse(file_tree)
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list files")


@app.get("/api/content/{path:path}")
async def get_file_content(path: str):
    """
    Return the content of a specific file.
    """
    try:
        file_path = DATA_DIR / path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Read file content
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        # Try to parse as JSON for better formatting
        try:
            json_content = json.loads(content)
            return JSONResponse(json_content)
        except json.JSONDecodeError:
            # Return as plain text if not JSON
            return {"content": content, "type": "text"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file {path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to read file")


@app.delete("/api/files/{path:path}")
async def delete_file(path: str):
    """
    Delete a specific file from the dashboard storage.
    """
    try:
        file_path = DATA_DIR / path
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete the file
        file_path.unlink()
        
        # Also try to remove empty parent directories
        try:
            parent = file_path.parent
            while parent != DATA_DIR and parent.exists():
                # Only remove if directory is empty
                if not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
                else:
                    break
        except OSError:
            # Ignore errors when cleaning up directories
            pass
        
        logger.info(f"Deleted file: {path}")
        return {"status": "success", "path": path, "message": "File deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file {path}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete file")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Serve the main dashboard interface.
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


def build_file_tree(root_path: Path) -> Dict[str, Any]:
    """
    Build a nested dictionary representing the file tree.
    """
    tree = {
        "name": root_path.name,
        "type": "directory",
        "children": [],
        "path": ""
    }
    
    if not root_path.exists():
        return tree
    
    def scan_directory(dir_path: Path, relative_path: str = "") -> List[Dict[str, Any]]:
        items = []
        
        try:
            for item in sorted(dir_path.iterdir()):
                item_relative_path = str(Path(relative_path) / item.name) if relative_path else item.name
                
                if item.is_dir():
                    dir_info = {
                        "name": item.name,
                        "type": "directory",
                        "path": item_relative_path,
                        "children": scan_directory(item, item_relative_path)
                    }
                    items.append(dir_info)
                else:
                    # Get file stats
                    stat = item.stat()
                    file_info = {
                        "name": item.name,
                        "type": "file",
                        "path": item_relative_path,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": item.suffix.lower()
                    }
                    items.append(file_info)
        
        except PermissionError:
            logger.warning(f"Permission denied accessing {dir_path}")
        
        return items
    
    tree["children"] = scan_directory(root_path)
    return tree


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)