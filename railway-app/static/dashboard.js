// Dashboard JavaScript

let fileTree = null;
let selectedFile = null;
let autoRefreshInterval = null;

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadFiles();
    startAutoRefresh();
});

// Load files from API
async function loadFiles() {
    try {
        updateStatus('loading', 'Loading files...');
        
        const response = await fetch('/api/files');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        fileTree = await response.json();
        renderFileTree();
        updateStatus('online', `Loaded ${countFiles(fileTree)} files`);
        
    } catch (error) {
        console.error('Error loading files:', error);
        updateStatus('offline', 'Failed to load files');
        document.getElementById('file-tree').innerHTML = `
            <div class="error">
                <p>❌ Failed to load files</p>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Render file tree in the UI
function renderFileTree() {
    const container = document.getElementById('file-tree');
    
    if (!fileTree || !fileTree.children || fileTree.children.length === 0) {
        container.innerHTML = '<div class="loading">No files found</div>';
        return;
    }
    
    container.innerHTML = '';
    fileTree.children.forEach(child => {
        container.appendChild(createTreeNode(child));
    });
}

// Create a tree node element
function createTreeNode(node, level = 0) {
    const nodeElement = document.createElement('div');
    nodeElement.className = 'tree-node';
    
    const contentElement = document.createElement('div');
    contentElement.className = 'tree-node-content';
    
    // Icon
    const iconElement = document.createElement('span');
    iconElement.className = 'tree-node-icon';
    
    if (node.type === 'directory') {
        iconElement.textContent = node.children && node.children.length > 0 ? '📁' : '📂';
        contentElement.addEventListener('click', () => toggleDirectory(nodeElement, node));
    } else {
        iconElement.textContent = getFileIcon(node.extension);
        contentElement.addEventListener('click', () => selectFile(contentElement, node));
    }
    
    // Name
    const nameElement = document.createElement('span');
    nameElement.className = 'tree-node-name';
    nameElement.textContent = node.name;
    
    contentElement.appendChild(iconElement);
    contentElement.appendChild(nameElement);
    
    // Size for files
    if (node.type === 'file') {
        const sizeElement = document.createElement('span');
        sizeElement.className = 'tree-node-size';
        sizeElement.textContent = formatFileSize(node.size);
        contentElement.appendChild(sizeElement);
    }
    
    nodeElement.appendChild(contentElement);
    
    // Children for directories
    if (node.type === 'directory' && node.children) {
        const childrenElement = document.createElement('div');
        childrenElement.className = 'tree-children';
        
        node.children.forEach(child => {
            childrenElement.appendChild(createTreeNode(child, level + 1));
        });
        
        nodeElement.appendChild(childrenElement);
    }
    
    return nodeElement;
}

// Toggle directory expansion
function toggleDirectory(nodeElement, node) {
    const childrenElement = nodeElement.querySelector('.tree-children');
    const iconElement = nodeElement.querySelector('.tree-node-icon');
    
    if (childrenElement) {
        const isExpanded = childrenElement.classList.contains('expanded');
        
        if (isExpanded) {
            childrenElement.classList.remove('expanded');
            iconElement.textContent = '📁';
        } else {
            childrenElement.classList.add('expanded');
            iconElement.textContent = '📂';
        }
    }
}

// Select file and load content
async function selectFile(element, node) {
    // Update selection UI
    document.querySelectorAll('.tree-node-content').forEach(el => {
        el.classList.remove('selected');
    });
    element.classList.add('selected');
    
    selectedFile = node;
    
    // Update content panel
    document.getElementById('content-title').textContent = node.path;
    
    try {
        const response = await fetch(`/api/content/${encodeURIComponent(node.path)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const content = await response.json();
        displayFileContent(content, node);
        
    } catch (error) {
        console.error('Error loading file content:', error);
        document.getElementById('file-content').innerHTML = `
            <div class="error">
                <p>❌ Failed to load file content</p>
                <p>${error.message}</p>
            </div>
        `;
    }
}

// Display file content
function displayFileContent(content, node) {
    const container = document.getElementById('file-content');
    
    // Show/hide collapse/expand buttons
    const isJson = node.extension === '.json' || typeof content === 'object';
    document.getElementById('collapse-all').style.display = isJson ? 'inline-block' : 'none';
    document.getElementById('expand-all').style.display = isJson ? 'inline-block' : 'none';
    
    if (typeof content === 'object' && content !== null) {
        // JSON content
        container.innerHTML = '<div class="json-container"></div>';
        const jsonContainer = container.querySelector('.json-container');
        renderJson(jsonContainer, content, '', true);
    } else if (content.type === 'text') {
        // Plain text content
        container.innerHTML = `<pre>${escapeHtml(content.content)}</pre>`;
    } else {
        // Other content
        container.innerHTML = `<pre>${escapeHtml(JSON.stringify(content, null, 2))}</pre>`;
    }
}

// Render JSON with collapsible structure
function renderJson(container, obj, key = '', isRoot = false, collapsed = true) {
    if (obj === null) {
        container.appendChild(createJsonElement('null', 'json-null', 'null'));
        return;
    }
    
    if (typeof obj !== 'object') {
        const className = `json-${typeof obj}`;
        const value = typeof obj === 'string' ? `"${obj}"` : String(obj);
        container.appendChild(createJsonElement(value, className, value));
        return;
    }
    
    const isArray = Array.isArray(obj);
    const openBracket = isArray ? '[' : '{';
    const closeBracket = isArray ? ']' : '}';
    
    // Container for this object/array
    const objContainer = document.createElement('div');
    
    // Header with key and opening bracket
    const header = document.createElement('div');
    header.className = 'json-collapsible';
    
    if (key) {
        const keySpan = createJsonElement(`"${key}": `, 'json-key');
        header.appendChild(keySpan);
    }
    
    const toggleIcon = document.createElement('span');
    toggleIcon.textContent = collapsed ? '▶ ' : '▼ ';
    toggleIcon.style.color = '#6b7280';
    toggleIcon.style.fontSize = '12px';
    header.appendChild(toggleIcon);
    
    header.appendChild(createJsonElement(openBracket, 'json-bracket'));
    
    // Collapsed summary
    const summary = document.createElement('span');
    summary.className = 'json-collapsed';
    summary.style.display = collapsed ? 'inline' : 'none';
    
    const keys = Object.keys(obj);
    if (isArray) {
        summary.textContent = ` ${keys.length} items `;
    } else {
        summary.textContent = ` ${keys.length} keys `;
    }
    header.appendChild(summary);
    
    header.appendChild(createJsonElement(closeBracket, 'json-bracket'));
    
    // Content
    const content = document.createElement('div');
    content.style.marginLeft = '20px';
    content.style.display = collapsed ? 'none' : 'block';
    
    keys.forEach((k, index) => {
        const item = document.createElement('div');
        
        if (!isArray) {
            const keyElement = createJsonElement(`"${k}": `, 'json-key');
            item.appendChild(keyElement);
        }
        
        renderJson(item, obj[k], isArray ? '' : k, false, true);
        
        if (index < keys.length - 1) {
            item.appendChild(createJsonElement(',', 'json-punct'));
        }
        
        content.appendChild(item);
    });
    
    // Closing bracket
    const footer = document.createElement('div');
    footer.appendChild(createJsonElement(closeBracket, 'json-bracket'));
    footer.style.display = collapsed ? 'none' : 'block';
    
    // Toggle functionality
    header.addEventListener('click', () => {
        const isCurrentlyCollapsed = content.style.display === 'none';
        content.style.display = isCurrentlyCollapsed ? 'block' : 'none';
        footer.style.display = isCurrentlyCollapsed ? 'block' : 'none';
        summary.style.display = isCurrentlyCollapsed ? 'none' : 'inline';
        toggleIcon.textContent = isCurrentlyCollapsed ? '▼ ' : '▶ ';
    });
    
    objContainer.appendChild(header);
    objContainer.appendChild(content);
    objContainer.appendChild(footer);
    
    container.appendChild(objContainer);
}

// Create JSON element with styling
function createJsonElement(text, className, title = '') {
    const element = document.createElement('span');
    element.textContent = text;
    element.className = className;
    if (title) element.title = title;
    return element;
}

// Utility functions
function getFileIcon(extension) {
    const icons = {
        '.json': '📄',
        '.txt': '📝',
        '.md': '📋',
        '.py': '🐍',
        '.js': '🟨',
        '.html': '🌐',
        '.css': '🎨'
    };
    return icons[extension] || '📄';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function countFiles(tree) {
    if (!tree || !tree.children) return 0;
    
    let count = 0;
    tree.children.forEach(child => {
        if (child.type === 'file') {
            count++;
        } else if (child.type === 'directory') {
            count += countFiles(child);
        }
    });
    return count;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateStatus(status, text) {
    const indicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    
    indicator.className = `status-dot ${status}`;
    statusText.textContent = text;
}

// Control functions
function refreshFiles() {
    loadFiles();
}

function filterFiles() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    const treeNodes = document.querySelectorAll('.tree-node');
    
    treeNodes.forEach(node => {
        const nameElement = node.querySelector('.tree-node-name');
        if (nameElement) {
            const name = nameElement.textContent.toLowerCase();
            const matches = name.includes(searchTerm);
            node.style.display = matches || searchTerm === '' ? 'block' : 'none';
        }
    });
}

function collapseAll() {
    document.querySelectorAll('.json-collapsible').forEach(header => {
        const content = header.nextElementSibling;
        const footer = content ? content.nextElementSibling : null;
        const summary = header.querySelector('.json-collapsed');
        const toggleIcon = header.querySelector('span');
        
        if (content && content.style.display !== 'none') {
            content.style.display = 'none';
            if (footer) footer.style.display = 'none';
            if (summary) summary.style.display = 'inline';
            if (toggleIcon) toggleIcon.textContent = '▶ ';
        }
    });
}

function expandAll() {
    document.querySelectorAll('.json-collapsible').forEach(header => {
        const content = header.nextElementSibling;
        const footer = content ? content.nextElementSibling : null;
        const summary = header.querySelector('.json-collapsed');
        const toggleIcon = header.querySelector('span');
        
        if (content && content.style.display === 'none') {
            content.style.display = 'block';
            if (footer) footer.style.display = 'block';
            if (summary) summary.style.display = 'none';
            if (toggleIcon) toggleIcon.textContent = '▼ ';
        }
    });
}

function startAutoRefresh() {
    // Refresh every 30 seconds
    autoRefreshInterval = setInterval(() => {
        loadFiles();
    }, 30000);
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}