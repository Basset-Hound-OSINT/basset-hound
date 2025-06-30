let currentPersonId = null;
let currentPath = '/';

export function openFileExplorer(personId) {
    currentPersonId = personId;
    currentPath = '/';
    document.getElementById('file-explorer-overlay').style.display = 'block';
    loadFolder('/');
}

document.getElementById('close-file-explorer').onclick = function() {
    document.getElementById('file-explorer-overlay').style.display = 'none';
    document.getElementById('markdown-viewer').style.display = 'none';
};

document.getElementById('upload-files-btn').onclick = function() {
    document.getElementById('file-upload-input').click();
};

document.getElementById('file-upload-input').onchange = async function(e) {
    const files = e.target.files;
    if (!files.length) return;
    const formData = new FormData();
    for (const file of files) formData.append('files', file);

    // If currentPath is "/" or "", upload to "files"
    let uploadPath = currentPath.replace(/\\/g, '/').replace(/^\//, '');
    if (uploadPath === '' || uploadPath === '/') uploadPath = 'files';

    await fetch(`/person/${currentPersonId}/upload?path=${encodeURIComponent(uploadPath)}`, {
        method: 'POST',
        body: formData
    });
    loadFolder(currentPath);
};

function showUploadButton(path) {
    // Only show if path starts with "files" or is exactly "files"
    const show = path === 'files' || path.startsWith('files/');
    document.getElementById('upload-files-btn').style.display = show ? 'inline-block' : 'none';
}

async function loadFolder(path) {
    const res = await fetch(`/person/${currentPersonId}/explore?path=${encodeURIComponent(path)}`);
    const data = await res.json();
    renderSidebar(data.tree, path);
    renderTable(data.entries, path);
    showUploadButton(path.replace(/\\/g, '/').replace(/^\//, ''));
}

function renderSidebar(tree, path) {
    const sidebar = document.getElementById('file-explorer-sidebar');
    sidebar.innerHTML = renderTree(tree, path);
    sidebar.querySelectorAll('.tree-folder').forEach(el => {
        el.onclick = e => {
            e.stopPropagation();
            loadFolder(el.dataset.path);
        };
    });
}

function renderTree(tree, path, depth=0) {
    let html = '<ul class="tree-list">';
    for (const node of tree) {
        if (node.type === 'folder') {
            html += `<li>
                <span class="tree-folder" data-path="${node.path}" style="margin-left:${depth*10}px;">
                    <i class="fas fa-folder${node.open ? '-open' : ''}"></i> ${node.name}
                </span>
                ${node.open && node.children ? renderTree(node.children, node.path, depth+1) : ''}
            </li>`;
        } else {
            html += `<li style="margin-left:${depth*10}px;">
                <a href="${node.url}" target="_blank">${node.name}</a>
            </li>`;
        }
    }
    html += '</ul>';
    return html;
}

function renderTable(entries, path) {
    const tbody = document.getElementById('file-explorer-table').querySelector('tbody');
    tbody.innerHTML = '';
    const normalizedPath = path.replace(/\\/g, '/').replace(/^\//, '');

    for (const entry of entries) {
        const tr = document.createElement('tr');
        if (entry.type === 'folder') {
            tr.innerHTML = `<td><a href="#" class="folder-link" data-path="${entry.path}"><i class="fas fa-folder"></i> ${entry.name}</a></td>
                <td></td><td></td>`;
        } else {
            tr.innerHTML = `<td><a href="${entry.url}" target="_blank">${entry.name}</a></td>
                <td>${entry.id || ''}</td>
                <td>${entry.date || ''}</td>`;
        }
        tbody.appendChild(tr);
    }
    tbody.querySelectorAll('.folder-link').forEach(link => {
        link.onclick = e => {
            e.preventDefault();
            loadFolder(link.dataset.path);
        };
    });

    // Only allow markdown preview in "reports" folder
    if (normalizedPath === 'reports' || normalizedPath.startsWith('reports/')) {
        tbody.querySelectorAll('a').forEach(link => {
            if (link.href.endsWith('.md')) {
                link.onclick = async e => {
                    e.preventDefault();
                    const res = await fetch(link.href);
                    const text = await res.text();
                    showMarkdownViewer(link.textContent, text, link.href);
                };
            }
        });
    }
}

function showMarkdownViewer(filename, content, url) {
    document.getElementById('markdown-viewer').style.display = 'block';
    document.getElementById('markdown-filename').textContent = filename;
    document.getElementById('markdown-content').innerHTML = marked.parse(content);
    document.getElementById('markdown-editor').style.display = 'none';
    document.getElementById('save-markdown-btn').style.display = 'none';

    // Only show edit for .md files
    if (filename.endsWith('.md')) {
        document.getElementById('edit-markdown-btn').style.display = 'inline-block';
        document.getElementById('edit-markdown-btn').onclick = function() {
            document.getElementById('markdown-editor').value = content;
            document.getElementById('markdown-content').style.display = 'none';
            document.getElementById('markdown-editor').style.display = 'block';
            document.getElementById('save-markdown-btn').style.display = 'inline-block';
        };
        document.getElementById('save-markdown-btn').onclick = async function() {
            const newContent = document.getElementById('markdown-editor').value;
            await fetch(url, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content: newContent})
            });
            document.getElementById('markdown-content').style.display = 'block';
            document.getElementById('markdown-editor').style.display = 'none';
            document.getElementById('save-markdown-btn').style.display = 'none';
            document.getElementById('markdown-content').innerHTML = marked.parse(newContent);
        };
    } else {
        document.getElementById('edit-markdown-btn').style.display = 'none';
    }
}