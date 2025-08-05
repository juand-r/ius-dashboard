# IUS Dashboard Enhancement Plan

## Overview

Transform the existing FastAPI dashboard to **exactly match the detective dashboard design** at [detective-dashboard-production.up.railway.app](https://detective-dashboard-production.up.railway.app/), while keeping the proven FastAPI + HTML/CSS/JS foundation.

**Focus:** Chunks contain most information needed - can reconstruct full documents by concatenating chunks.

**Target URL Structure:**
- `/` - Landing page with collection tiles (matching detective dashboard design exactly)
- `/{collection}` - Collection page with item tiles (matching detective stories list)
- `/{collection}/item/{item_id}` - Detailed item view with collapsible sections (matching story detail page)

**Design Reference:** [Detective Dashboard Landing](https://detective-dashboard-production.up.railway.app/), which is implemented in /Users/juandiego/Dev/sequential-summarization/detective-solutions-dashboard

## Phase 1: Backend Data Structure (Day 1)

### 1.1 Update FastAPI Routes
- [ ] Modify `/` route to serve landing page instead of current dashboard
- [ ] Add `/dataset/{collection}` route for dataset pages
- [ ] Add `/dataset/{collection}/item/{item_id}` route for item details
- [ ] Keep existing `/api/*` endpoints but enhance data grouping

### 1.2 Data Grouping Logic (Focus on Chunks)
- [ ] Create `get_collections()` function to match detective dashboard structure:
  - `chunks` → "Text Chunks" (primary collection - contains most data)
  - `prompts` → "Prompts & Templates" (secondary collection)
- [ ] Create `get_collection_items(collection_name)` to list items like detective stories
- [ ] Create `get_item_details(collection, item_id)` for detailed view:
  - **For chunks**: Full content, metadata, related chunks (if multi-part)
  - **For prompts**: Template content, parameters, usage examples
  - Document reconstruction (concatenate chunks back to full document)

### 1.3 Chunk-Centric Organization  
- [ ] Group related chunks by document/collection ID
- [ ] Extract meaningful document names from chunk file paths
- [ ] Generate document previews (first chunk + metadata)
- [ ] **QUESTION**: How are your chunks organized? By collection? By document? Need to understand file naming pattern.

**Files to modify:**
- `railway-app/main.py` - Add new routes and data functions

## Phase 2: Frontend Templates (Day 2)

### 2.1 Landing Page (EXACTLY match detective dashboard)
- [ ] Create `templates/landing.html` - **copy detective dashboard layout exactly**
- [ ] Header: "IUS Processing Dashboard" (matching detective dashboard header style)
- [ ] Collection cards with **exact same styling** as detective dashboard:
  - **Chunks Collection**: "Text Chunks - Processed document segments and analysis"
  - **Prompts Collection**: "Prompts & Templates - Processing instructions and methods"
- [ ] Card hover effects matching detective dashboard
- [ ] **QUESTION**: Do you want different collection names/descriptions?

### 2.2 Collection Page (match detective stories list)
- [ ] Create `templates/collection.html` - **copy detective stories list design exactly**  
- [ ] Header with collection name + back button
- [ ] Search bar (matching detective dashboard search)
- [ ] Item cards grid (same layout as detective stories)
- [ ] Each item card shows:
  - Document/item name (like story title)
  - Preview text (like plot summary)  
  - Metadata (file size, date, chunk count)
- [ ] **QUESTION**: What should item previews show? First chunk content?

### 2.3 Navigation Components
- [ ] Header with site title and navigation
- [ ] Breadcrumb component
- [ ] Back buttons
- [ ] Search functionality (Phase 3)

**Files to create:**
- `railway-app/templates/landing.html`
- `railway-app/templates/dataset.html`
- `railway-app/templates/base.html` (shared layout)

## Phase 3: Item Detail Page (Day 3)

### 3.1 Item Detail Page (EXACTLY match detective story detail)
- [ ] Create `templates/item_detail.html` - **copy detective story detail layout exactly**
- [ ] Header with item title + navigation (matching detective dashboard)
- [ ] Collapsible sections with **exact same styling** as detective dashboard:
  - **📄 Document Content** (expanded by default - reconstructed from chunks)
  - **🧩 Individual Chunks** (collapsed - show each chunk separately) 
  - **⚙️ Processing Information** (collapsed - prompts used, parameters)
  - **📊 Metadata** (collapsed - file info, timestamps, processing stats)
- [ ] **QUESTION**: Should we have additional sections? What other data do you want to display?

### 3.2 Content Display (match detective dashboard styling)
- [ ] **Copy detective dashboard CSS exactly** for collapsible sections
- [ ] JSON syntax highlighting (reuse existing code but match detective styling)
- [ ] Text formatting matching detective dashboard
- [ ] Section headers with same icons/styling as detective dashboard
- [ ] Spacing and typography exactly matching detective dashboard

### 3.3 JavaScript (copy detective dashboard behavior)
- [ ] Copy detective dashboard's `toggleSection()` function exactly
- [ ] Same expand/collapse animations as detective dashboard
- [ ] Same button styling and interactions
- [ ] **QUESTION**: Any different interactions needed beyond basic expand/collapse?

**Files to create:**
- `railway-app/templates/item_detail.html`

**Files to modify:**
- `railway-app/static/dashboard.js` - Add collapsible functionality

## Phase 4: Styling & Polish (Day 4)

### 4.1 CSS (COPY detective dashboard styles exactly)
- [ ] **Extract CSS from detective dashboard** - inspect element and copy styles
- [ ] Landing page cards - exact same styling as detective dashboard
- [ ] Collection page layout - exact same as detective stories list
- [ ] Collapsible sections - exact same styling as detective story detail
- [ ] Colors, fonts, spacing - **match detective dashboard exactly**
- [ ] Hover effects and transitions - **copy detective dashboard exactly**

### 4.2 UI Components
- [ ] Loading states
- [ ] Error handling
- [ ] Empty states
- [ ] Status indicators

### 4.3 Performance Optimizations
- [ ] Lazy loading for large content
- [ ] Caching for expensive data operations
- [ ] Optimized file tree building

**Files to modify:**
- `railway-app/static/style.css` - Major enhancements
- `railway-app/static/dashboard.js` - Performance improvements

## Phase 5: Basic Visualizations (Day 5 - Optional)

### 5.1 Matplotlib Integration
- [ ] Add `/api/visualize/{collection}/{item_id}` endpoint
- [ ] Basic plots:
  - File size distributions
  - Processing timestamps
  - Content length analysis
  - Word frequency (simple)

### 5.2 Visualization UI
- [ ] Add "📊 Visualizations" collapsible section
- [ ] Plot type selector buttons
- [ ] Loading states for plot generation
- [ ] Error handling for visualization failures

**Files to modify:**
- `railway-app/main.py` - Add visualization endpoint
- `railway-app/requirements.txt` - Add matplotlib
- `railway-app/templates/item_detail.html` - Add viz section

## Implementation Notes

### Watcher Configuration Updates
- [ ] Update `watcher/config.py` to focus on chunks:
```python
WATCHED_DIRS = [
    "outputs/chunks",  # Primary focus
    "prompts"          # Secondary
]
```
- [ ] **QUESTION**: Should we still watch summaries or just focus on chunks?

### Keep Unchanged  
- ✅ Railway deployment configuration  
- ✅ Core FastAPI application structure
- ✅ Existing API endpoints (enhance, don't replace)
- ✅ File watcher upload mechanism

### Key Principles
- **Progressive Enhancement**: Each phase adds features without breaking previous work
- **Fallback Compatibility**: Maintain API compatibility for file watcher
- **Simple First**: Start with basic functionality, add complexity gradually
- **Reuse Assets**: Leverage existing CSS, JS, and data processing code

### Testing Strategy
- [ ] Test file watcher still works with new backend
- [ ] Test navigation flows work correctly
- [ ] Test with real data from your `ius/` project
- [ ] Test Railway deployment

### Success Criteria
1. **Navigation**: 3-level hierarchy works smoothly
2. **Content Display**: All file types display correctly in collapsible sections
3. **Performance**: Page loads are fast (< 2 seconds)
4. **Mobile Friendly**: Works on mobile devices
5. **Data Integrity**: File watcher continues uploading correctly

## Quick Start Commands

```bash
# Development setup
cd railway-app
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Test file watcher still works
cd ../watcher
python main.py

# Create test data
cd ..
python test-system.py
```

## File Structure After Implementation

```
railway-app/
├── main.py                 # Enhanced with new routes
├── templates/
│   ├── base.html          # NEW - Shared layout
│   ├── landing.html       # NEW - Dataset tiles
│   ├── dataset.html       # NEW - Item list
│   ├── item_detail.html   # NEW - Detailed view
│   └── dashboard.html     # KEEP - Legacy compatibility
├── static/
│   ├── style.css          # ENHANCED - New layouts
│   └── dashboard.js       # ENHANCED - Collapsible sections
└── requirements.txt       # ENHANCED - Add matplotlib
```

## Key Questions (NEED ANSWERS to proceed effectively)

### 1. Chunk Organization
- **How are your chunks organized?** By document? By collection? By date?
- **File naming pattern?** E.g., `document-001-chunk-01.json` or different structure?
- **Can chunks be concatenated back to full documents?** How to identify related chunks?

### 2. Data Structure  
- **What's inside a chunk file?** JSON with text + metadata? What fields?
- **Should we still watch summaries or focus only on chunks?**
- **What metadata should item previews show?** First chunk content? Document title?

### 3. UI Customization
- **Collection names/descriptions:** Do you want "Text Chunks" and "Prompts" or different names?
- **Item preview content:** What should show in item cards? First chunk text?
- **Additional sections:** Any data beyond Document Content, Chunks, Processing Info, Metadata?
- **Different interactions:** Any features beyond basic expand/collapse?

### 4. Design Details
- **Site title:** "IUS Processing Dashboard" or something else?
- **Any design changes** from detective dashboard or copy exactly?

## Timeline
- **Day 1**: Backend routes and data grouping *(need answers to Questions 1-2)*
- **Day 2**: Landing and collection page templates *(need answers to Question 3)*
- **Day 3**: Item detail page with collapsible sections *(need answers to Question 4)*
- **Day 4**: Styling - copy detective dashboard exactly
- **Day 5**: Basic visualizations (optional)

**Total Effort**: 4-5 days for full implementation

## Next Steps
1. **FIRST**: Answer key questions above
2. Start with Phase 1 (backend changes)  
3. Test each phase before moving to the next
4. Deploy incrementally to Railway for testing