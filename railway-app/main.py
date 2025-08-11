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

@app.delete("/clear-data")
async def clear_data():
    """Clear all data from the dashboard (for testing)."""
    import shutil
    try:
        if DATA_DIR.exists():
            shutil.rmtree(DATA_DIR)
            DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("All data cleared from dashboard")
        return {"status": "success", "message": "All data cleared"}
    except Exception as e:
        logger.error(f"Error clearing data: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/debug/{dataset}/{subcollection}/item/{item_id}")
async def debug_item(dataset: str, subcollection: str, item_id: str):
    """Debug endpoint to check summary data."""
    try:
        item_data = await get_item_details(dataset, subcollection, item_id)
        summary_info = {
            "has_summary_data": item_data.get("summary_data") is not None and len(item_data.get("summary_data", [])) > 0,
            "num_collections": len(item_data.get("summary_data", [])),
            "collections": []
        }
        
        if item_data.get("summary_data"):
            for i, collection in enumerate(item_data["summary_data"]):
                collection_info = {
                    "collection_name": collection["collection_name"],
                    "strategy_name": collection["strategy_name"],
                    "num_summaries": collection["num_summaries"]
                }
                summary_info["collections"].append(collection_info)
        
        return summary_info
    except Exception as e:
        return {"error": str(e)}

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

@app.get("/api/prompts/{prompt_name}")
async def get_prompts(prompt_name: str):
    """Get prompt files for a given prompt name."""
    prompts_dir = DATA_DIR / "prompts" / "summarization" / prompt_name
    
    if not prompts_dir.exists() or not prompts_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Prompt directory '{prompt_name}' not found")
    
    try:
        prompts = []
        # Look for .txt files in the prompt directory
        for prompt_file in prompts_dir.glob("*.txt"):
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            prompts.append({
                "filename": prompt_file.name,
                "content": content
            })
        
        if not prompts:
            return {"prompt_name": prompt_name, "prompts": [], "message": "No .txt files found"}
        
        return {
            "prompt_name": prompt_name,
            "prompts": prompts
        }
        
    except Exception as e:
        logger.error(f"Error reading prompts for {prompt_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading prompts: {e}")


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """
    Landing page showing available collections (like detective dashboard).
    """
    collections = await get_collections()
    return templates.TemplateResponse("landing.html", {
        "request": request,
        "collections": collections
    })

@app.get("/{dataset}", response_class=HTMLResponse)
async def dataset_page(request: Request, dataset: str):
    """
    Dataset page showing subcollections/approaches (bmds_fixed_size_8000, etc).
    """
    subcollections = await get_dataset_subcollections(dataset)
    dataset_info = await get_collection_info(dataset)
    
    return templates.TemplateResponse("dataset.html", {
        "request": request,
        "dataset": dataset,
        "dataset_info": dataset_info,
        "subcollections": subcollections
    })

@app.get("/{dataset}/{subcollection}", response_class=HTMLResponse)
async def subcollection_page(request: Request, dataset: str, subcollection: str):
    """
    Subcollection page showing stories/items within a specific approach.
    """
    items = await get_collection_items(dataset, subcollection)
    dataset_info = await get_collection_info(dataset)
    
    return templates.TemplateResponse("collection.html", {
        "request": request,
        "dataset": dataset,
        "subcollection": subcollection,
        "collection_info": dataset_info,
        "items": items
    })

@app.get("/{dataset}/{subcollection}/item/{item_id}", response_class=HTMLResponse)
async def item_detail(request: Request, dataset: str, subcollection: str, item_id: str):
    """
    Item detail page with collapsible sections (like detective story detail).
    """
    item_data = await get_item_details(dataset, subcollection, item_id)
    
    return templates.TemplateResponse("item_detail.html", {
        "request": request,
        "dataset": dataset,
        "subcollection": subcollection,
        "item": item_data
    })

@app.get("/legacy", response_class=HTMLResponse)
async def legacy_dashboard(request: Request):
    """
    Legacy dashboard interface (keep for compatibility).
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


async def get_collections():
    """Get available datasets for landing page (organized by dataset name)."""
    datasets = {}
    
    # Extract datasets from chunk directories
    chunks_dir = DATA_DIR / "outputs" / "chunks"
    if not chunks_dir.exists():
        return []
        
    try:
        for collection_dir in chunks_dir.iterdir():
            if collection_dir.is_dir():
                # Extract dataset name (everything before first underscore)
                dataset_name = collection_dir.name.split('_')[0]
                
                if dataset_name not in datasets:
                    datasets[dataset_name] = {
                        "name": dataset_name,
                        "display_name": dataset_name.upper(),
                        "description": f"{dataset_name.upper()} dataset stories and analysis",
                        "count": 0,
                        "path": f"/{dataset_name}"
                    }
                
                # Count items in this collection
                items_dir = collection_dir / "items"
                if items_dir.exists():
                    item_count = len(list(items_dir.glob("*.json")))
                    datasets[dataset_name]["count"] += item_count
    except OSError as e:
        logger.error(f"Error reading chunks directory: {e}")
        return []
    
    return list(datasets.values())

async def get_collection_info(dataset: str):
    """Get dataset metadata."""
    return {
        "name": dataset,
        "display_name": dataset.upper(),
        "description": f"{dataset.upper()} dataset stories and analysis"
    }

async def get_dataset_subcollections(dataset: str):
    """Get subcollections (approaches) within a dataset."""
    subcollections = []
    
    chunks_dir = DATA_DIR / "outputs" / "chunks"
    if not chunks_dir.exists():
        return []
        
    try:
        for collection_dir in chunks_dir.iterdir():
            if collection_dir.is_dir() and collection_dir.name.startswith(f"{dataset}_"):
                # Count items in this subcollection
                items_dir = collection_dir / "items"
                item_count = 0
                if items_dir.exists():
                    item_count = len(list(items_dir.glob("*.json")))
                
                # Create display name from collection name
                display_name = collection_dir.name.replace("_", " ").title()
                
                subcollections.append({
                    "name": collection_dir.name,
                    "display_name": display_name,
                    "description": f"{display_name} approach",
                    "count": item_count,
                    "path": f"/{dataset}/{collection_dir.name}"
                })
    except OSError as e:
        logger.error(f"Error reading dataset subcollections for {dataset}: {e}")
        return []
    
    return sorted(subcollections, key=lambda x: x["name"])

async def get_collection_items(dataset: str, subcollection: str = None):
    """Get items (stories) in a specific subcollection or all subcollections in a dataset."""
    items = []
    
    chunks_dir = DATA_DIR / "outputs" / "chunks"
    if not chunks_dir.exists():
        return []
        
    try:
        # If subcollection is specified, only get items from that collection
        if subcollection:
            collection_dir = chunks_dir / subcollection
            if collection_dir.exists() and collection_dir.is_dir():
                items_dir = collection_dir / "items"
                if items_dir.exists():
                    for item_file in items_dir.glob("*.json"):
                        try:
                            # Read file content for preview
                            with open(item_file, 'r') as f:
                                content = json.load(f)
                            
                            # Extract preview content (first 200 chars)
                            preview = content.get("content", "")[:200] + "..." if len(content.get("content", "")) > 200 else content.get("content", "")
                            
                            items.append({
                                "id": item_file.stem,
                                "name": content.get("id", item_file.stem),
                                "preview": preview,
                                "collection_name": collection_dir.name,
                                "size": item_file.stat().st_size,
                                "modified": datetime.fromtimestamp(item_file.stat().st_mtime).isoformat(),
                                "metadata": content.get("metadata", {}),
                                "dataset": dataset,
                                "subcollection": subcollection
                            })
                        except Exception as e:
                            logger.error(f"Error reading chunk file {item_file}: {e}")
                            continue
        else:
            # Get items from all subcollections in the dataset (fallback)
            for collection_dir in chunks_dir.iterdir():
                if collection_dir.is_dir() and collection_dir.name.startswith(f"{dataset}_"):
                    items_dir = collection_dir / "items"
                    if items_dir.exists():
                        for item_file in items_dir.glob("*.json"):
                            try:
                                # Read file content for preview
                                with open(item_file, 'r') as f:
                                    content = json.load(f)
                                
                                # Extract preview content (first 200 chars)
                                preview = content.get("content", "")[:200] + "..." if len(content.get("content", "")) > 200 else content.get("content", "")
                                
                                items.append({
                                    "id": item_file.stem,
                                    "name": content.get("id", item_file.stem),
                                    "preview": preview,
                                    "collection_name": collection_dir.name,
                                    "size": item_file.stat().st_size,
                                    "modified": datetime.fromtimestamp(item_file.stat().st_mtime).isoformat(),
                                    "metadata": content.get("metadata", {}),
                                    "dataset": dataset
                                })
                            except Exception as e:
                                logger.error(f"Error reading chunk file {item_file}: {e}")
                                continue
    except OSError as e:
        logger.error(f"Error reading collection items for {dataset}/{subcollection}: {e}")
        return []
    
    return items

async def get_item_details(dataset: str, subcollection: str, item_id: str):
    """Get detailed item data for item detail page."""
    # Find the item in the specific subcollection
    chunks_dir = DATA_DIR / "outputs" / "chunks"
    if not chunks_dir.exists():
        raise HTTPException(status_code=404, detail="Data directory not found")
        
    # Look specifically in the requested subcollection
    collection_dir = chunks_dir / subcollection
    if not collection_dir.exists() or not collection_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Collection {subcollection} not found")
        
    items_dir = collection_dir / "items"
    item_file = items_dir / f"{item_id}.json"
    
    if not item_file.exists():
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found in {subcollection}")
        
    try:
        with open(item_file, 'r') as f:
            content = json.load(f)
        
        # Extract chunk metadata (universal for all datasets)  
        item_meta = content.get("item_metadata", {})
        doc_metadata = content.get("documents", [{}])[0].get("metadata", {}) if content.get("documents") else {}
        chunk_metadata = {
            "chunking_method": item_meta.get("chunking_method", "unknown"),
            "chunking_timestamp": item_meta.get("chunking_timestamp", ""),
            "chunking_params": item_meta.get("chunking_params", {}),
            "chunking_stats": doc_metadata.get("chunking_stats", {})
        }
        
        # Extract crimes/clues metadata (BMDS-specific)
        crimes_metadata = {}
        if dataset == "bmds":
            doc_meta = content.get("documents", [{}])[0].get("metadata", {}).get("original_metadata", {}).get("original_metadata", {}) if content.get("documents") else {}
            story_annotations = doc_meta.get("story_annotations", {})
            
            # Extract victim/culprit counts with assertion
            victims_male = int(story_annotations.get("Number of victims of gender Male", 0))
            victims_female = int(story_annotations.get("Number of victims of gender Female", 0))
            victims_unknown = int(story_annotations.get("Number of victims of gender Unknown", 0))
            victims_nonbinary = int(story_annotations.get("Number of victims of gender Non-binary", 0))
            
            culprits_male = int(story_annotations.get("Number of culprits of gender Male", 0))
            culprits_female = int(story_annotations.get("Number of culprits of gender Female", 0))
            culprits_unknown = int(story_annotations.get("Number of culprits of gender Unknown", 0))
            culprits_nonbinary = int(story_annotations.get("Number of culprits of gender Non-binary", 0))
            
            # Include unknown/non-binary in totals if they exist
            
            # Extract author information
            author_meta = doc_meta.get("author_metadata", {})
            given_names = author_meta.get("Given Name(s)", "")
            surname = author_meta.get("Surname(s)", "")
            author_name = f"{given_names} {surname}".strip() if given_names or surname else ""
            
            # Extract publication year
            pub_date = story_annotations.get("Date of First Publication (YYYY-MM-DD)", "")
            pub_year = ""
            if pub_date and len(pub_date) >= 4:
                pub_year = f"({pub_date[:4]})"
            
            crimes_metadata = {
                "victims_male": victims_male,
                "victims_female": victims_female,
                "victims_unknown": victims_unknown,
                "victims_nonbinary": victims_nonbinary,
                "culprits_male": culprits_male,
                "culprits_female": culprits_female,
                "culprits_unknown": culprits_unknown,
                "culprits_nonbinary": culprits_nonbinary,
                "types_of_qrimes": story_annotations.get("Types of qrimes", "") or "None",
                "crime_trajectory": story_annotations.get("Crime trajectory", "") or "None",
                "motives": story_annotations.get("Motives", "") or "None",
                "means_murder": story_annotations.get("Means (murder only)", "") or "None",
                "essential_clue": story_annotations.get("Essential clue", "") or "None",
                "most_salient_clue": story_annotations.get("Most salient clue", "") or "None",
                "correct_annotator_guess": story_annotations.get("Correct annotator guess?", "") or "None",
                "recommend_to_friend": story_annotations.get("Recommend to friend?", "") or "None",
                "planted_evidence": story_annotations.get("Presence of planted or fabricated evidence", "") or "None"
            }
            
            # Extract story information
            story_info = {
                "title": story_annotations.get("Story Title", ""),
                "plot_summary": story_annotations.get("Plot Summary", ""),
                "author": author_name,
                "publication_year": pub_year
            }
        
        # Try to load summary data from all matching collections
        summary_data = []
        summaries_dir = DATA_DIR / "outputs" / "summaries"
        if summaries_dir.exists():
            # Look for all summary collections that match this subcollection pattern and have "_all_"
            # e.g., bmds_fixed_size_8000_all_iterative_incremental_intermediate
            summary_collections = []
            for summary_collection in summaries_dir.iterdir():
                if (summary_collection.is_dir() and 
                    subcollection in summary_collection.name and 
                    "_all_" in summary_collection.name):
                    summary_collections.append(summary_collection)
            
            # Sort collections by name for consistent ordering
            summary_collections.sort(key=lambda x: x.name)
            
            for summary_collection in summary_collections:
                summary_items_dir = summary_collection / "items"
                summary_file = summary_items_dir / f"{item_id}.json"
                
                if summary_file.exists():
                    try:
                        with open(summary_file, 'r') as f:
                            summary_content = json.load(f)
                        
                        # Extract summaries array
                        doc_summaries = summary_content.get("documents", [{}])[0] if summary_content.get("documents") else {}
                        summaries_list = doc_summaries.get("summaries", [])
                        
                        # Extract strategy name from collection name
                        # e.g., "bmds_fixed_size_8000_all_concat_default-concat-prompt_intermediate" -> "concat_default-concat-prompt"
                        parts = summary_collection.name.split("_all_")
                        if len(parts) > 1:
                            strategy_part = parts[1]
                            # Remove "_intermediate" or "_final" suffix
                            strategy_name = strategy_part.replace("_intermediate", "").replace("_final", "")
                        else:
                            strategy_name = summary_collection.name
                        
                        # Load collection.json for config metadata
                        config_metadata = {}
                        collection_json_path = summary_collection / "collection.json"
                        if collection_json_path.exists():
                            try:
                                with open(collection_json_path, 'r') as f:
                                    collection_json = json.load(f)
                                    
                                collection_meta = collection_json.get("summarization_info", {}).get("collection_metadata", {})
                                hash_params = collection_meta.get("hash_parameters", {})
                                
                                # Map length constraint to display format
                                length_constraint_raw = collection_meta.get("optional_summary_length", "")
                                length_constraint_display = ""
                                if length_constraint_raw == "summary":
                                    length_constraint_display = ""
                                elif length_constraint_raw == "summary in less than 200 words":
                                    length_constraint_display = "(<200 words)"
                                elif length_constraint_raw == "summary in less than 500 words":
                                    length_constraint_display = "(<500 words)"
                                elif length_constraint_raw == "and very long summary (as long as you can make it, try to reach 5000 words if possible)":
                                    length_constraint_display = "(very long)"
                                else:
                                    length_constraint_display = f"({length_constraint_raw})" if length_constraint_raw else ""
                                
                                config_metadata = {
                                    "strategy": collection_meta.get("strategy_function", ""),
                                    "inputs": collection_meta.get("step_k_inputs", ""),
                                    "output": collection_meta.get("summary_content_type", ""),
                                    "model": collection_meta.get("model", ""),
                                    "prompts": collection_meta.get("prompt_name", ""),
                                    "length_constraint": length_constraint_raw,
                                    "length_constraint_display": length_constraint_display,
                                    "is_500_words": length_constraint_raw == "summary in less than 500 words",
                                    "final_only": collection_meta.get("final_only", "")
                                }
                            except Exception as e:
                                logger.error(f"Error reading collection.json for {summary_collection.name}: {e}")
                        
                        collection_data = {
                            "collection_name": summary_collection.name,
                            "strategy_name": strategy_name,
                            "summaries": summaries_list,
                            "num_summaries": len(summaries_list),
                            "config_metadata": config_metadata
                        }
                        summary_data.append(collection_data)
                        logger.info(f"Loaded {len(summaries_list)} summaries for {item_id} from {summary_collection.name} (strategy: {strategy_name})")
                        
                    except Exception as e:
                        logger.error(f"Error reading summary file {summary_file}: {e}")
                        continue

        # Sort summary collections by length constraint priority
        def get_sort_priority(collection):
            length_constraint = collection.get("config_metadata", {}).get("length_constraint", "")
            if length_constraint == "summary in less than 500 words":
                return 1  # <500 words first
            elif length_constraint == "summary":
                return 2  # None (empty string) second
            elif length_constraint == "summary in less than 200 words":
                return 3  # <200 words third
            elif length_constraint == "and very long summary (as long as you can make it, try to reach 5000 words if possible)":
                return 4  # very long last
            else:
                return 5  # any other constraint at the end
        
        summary_data.sort(key=get_sort_priority)

        return {
            "id": item_id,
            "name": content.get("id", item_id),
            "dataset": dataset,
            "collection_name": collection_dir.name,
            "content": content.get("content", ""),
            "chunk_metadata": chunk_metadata,
            "crimes_metadata": crimes_metadata,
            "story_info": story_info if dataset == "bmds" else {},
            "full_content": content,
            "summary_data": summary_data,  # New field for summaries
            "file_size": item_file.stat().st_size,
            "modified": datetime.fromtimestamp(item_file.stat().st_mtime).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error reading chunk details {item_file}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing item {item_id}: {e}")

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