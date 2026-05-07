/**
 * Export Handler Module
 *
 * Provides functionality for exporting data in multiple formats:
 * - GraphML (for Gephi/Cytoscape)
 * - CSV/JSON (entities)
 * - GeoJSON (locations)
 * - Reports (DOCX, HTML, Markdown)
 * - Database dumps
 */

/**
 * Show notification to user
 * @param {string} message - The notification message
 * @param {string} type - Type: 'info', 'success', 'error', 'warning'
 */
function showNotification(message, type = 'info') {
    // Use browser's native notification API or simple alert
    if (typeof alert !== 'undefined') {
        // Simple fallback implementation
        const prefix = type.toUpperCase();
        console.log(`[${prefix}] ${message}`);

        // Try to show toast if available
        if (window.showToast) {
            window.showToast(message, type);
        }
    }
}

/**
 * Initialize export buttons and handlers
 * @param {string} projectSafeName - The URL-safe project identifier
 */
export function initExportHandlers(projectSafeName) {
    setupExportMenu(projectSafeName);
}

/**
 * Setup export menu with all export options
 * @param {string} projectSafeName - The URL-safe project identifier
 */
function setupExportMenu(projectSafeName) {
    const downloadBtn = document.getElementById('download-project-btn');
    if (!downloadBtn) return;

    // Create export dropdown menu if not already present
    let exportMenu = document.getElementById('export-menu');
    if (!exportMenu) {
        exportMenu = createExportMenu(projectSafeName);
        downloadBtn.parentElement.appendChild(exportMenu);
    }

    // Toggle menu on button click
    downloadBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const menu = document.getElementById('export-menu');
        if (menu) {
            menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
        }
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('#download-project-btn') && !e.target.closest('#export-menu')) {
            const menu = document.getElementById('export-menu');
            if (menu) {
                menu.style.display = 'none';
            }
        }
    });
}

/**
 * Create export menu HTML
 * @param {string} projectSafeName - The URL-safe project identifier
 * @returns {HTMLElement} - The menu element
 */
function createExportMenu(projectSafeName) {
    const menu = document.createElement('div');
    menu.id = 'export-menu';
    menu.className = 'export-menu';
    menu.style.cssText = `
        position: absolute;
        top: 100%;
        right: 0;
        background: white;
        border: 1px solid #ddd;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        z-index: 1000;
        min-width: 200px;
        margin-top: 5px;
        display: none;
    `;

    const items = [
        { label: 'Graph (GraphML)', id: 'export-graphml', icon: 'fa-project-diagram' },
        { label: 'Entities (CSV)', id: 'export-csv', icon: 'fa-table' },
        { label: 'Entities (JSON)', id: 'export-json', icon: 'fa-code' },
        { label: 'Locations (GeoJSON)', id: 'export-geojson', icon: 'fa-map-marker-alt' },
        { label: 'Report (HTML)', id: 'export-report-html', icon: 'fa-file-html5' },
        { label: 'Report (DOCX)', id: 'export-report-docx', icon: 'fa-file-word' },
        { label: 'Report (Markdown)', id: 'export-report-md', icon: 'fa-file' },
        { label: 'Database Dump', id: 'export-database', icon: 'fa-database' }
    ];

    items.forEach(item => {
        const button = document.createElement('button');
        button.className = 'export-menu-item';
        button.id = item.id;
        button.innerHTML = `<i class="fas ${item.icon}"></i> ${item.label}`;
        button.style.cssText = `
            display: block;
            width: 100%;
            padding: 10px 15px;
            border: none;
            background: none;
            text-align: left;
            cursor: pointer;
            font-size: 14px;
            border-bottom: 1px solid #f0f0f0;
        `;

        button.addEventListener('mouseover', () => {
            button.style.backgroundColor = '#f5f5f5';
        });

        button.addEventListener('mouseout', () => {
            button.style.backgroundColor = 'transparent';
        });

        button.addEventListener('click', (e) => {
            e.preventDefault();
            handleExport(projectSafeName, item.id);
            menu.style.display = 'none';
        });

        menu.appendChild(button);
    });

    return menu;
}

/**
 * Handle export action
 * @param {string} projectSafeName - The URL-safe project identifier
 * @param {string} exportType - Type of export
 */
async function handleExport(projectSafeName, exportType) {
    try {
        showNotification(`Starting ${exportType} export...`, 'info');

        let url;
        const timestamp = new Date().toISOString().slice(0, 10);

        switch (exportType) {
            case 'export-graphml':
                url = `/api/v1/projects/${projectSafeName}/export/graphml`;
                break;

            case 'export-csv':
                url = `/api/v1/projects/${projectSafeName}/export/entities/csv`;
                break;

            case 'export-json':
                url = `/api/v1/projects/${projectSafeName}/export/entities/json`;
                break;

            case 'export-geojson':
                url = `/api/v1/projects/${projectSafeName}/export/locations/geojson`;
                break;

            case 'export-report-html':
                const htmlReport = await generateReport('html');
                if (htmlReport) {
                    downloadReport(projectSafeName, 'html', htmlReport);
                    showNotification('HTML report exported successfully', 'success');
                }
                return;

            case 'export-report-docx':
                const docxReport = await generateReport('docx');
                if (docxReport) {
                    downloadReport(projectSafeName, 'docx', docxReport);
                    showNotification('DOCX report exported successfully', 'success');
                }
                return;

            case 'export-report-md':
                const mdReport = await generateReport('markdown');
                if (mdReport) {
                    downloadReport(projectSafeName, 'markdown', mdReport);
                    showNotification('Markdown report exported successfully', 'success');
                }
                return;

            case 'export-database':
                url = `/api/v1/projects/${projectSafeName}/export/database-dump`;
                break;

            default:
                showNotification(`Unknown export type: ${exportType}`, 'error');
                return;
        }

        // Download file from URL
        if (url) {
            downloadFile(url);
            showNotification('Export completed successfully', 'success');
        }

    } catch (error) {
        console.error('Export failed:', error);
        showNotification(`Export failed: ${error.message}`, 'error');
    }
}

/**
 * Download file from URL
 * @param {string} url - The URL to download from
 */
function downloadFile(url) {
    const link = document.createElement('a');
    link.href = url;
    link.click();
}

/**
 * Generate a report
 * @param {string} format - Report format (html, docx, markdown)
 * @returns {Promise<Object>} - Report data or null
 */
async function generateReport(format) {
    try {
        const title = prompt('Enter report title:', 'Investigation Report');
        if (!title) return null;

        const sections = [
            {
                title: 'Executive Summary',
                content: 'Investigation summary and key findings.'
            },
            {
                title: 'Entities',
                content: 'List of entities in this investigation.'
            },
            {
                title: 'Relationships',
                content: 'Connections between entities.'
            }
        ];

        return {
            title,
            format,
            sections,
            include_author: true,
            author: 'Analyst'
        };

    } catch (error) {
        console.error('Error generating report:', error);
        return null;
    }
}

/**
 * Download report
 * @param {string} projectSafeName - The URL-safe project identifier
 * @param {string} format - Report format
 * @param {Object} reportData - Report data
 */
async function downloadReport(projectSafeName, format, reportData) {
    try {
        const response = await fetch(
            `/api/v1/projects/${projectSafeName}/export/report-formats`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(reportData)
            }
        );

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${reportData.title.replace(/\s+/g, '_')}.${format === 'markdown' ? 'md' : format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

    } catch (error) {
        console.error('Failed to download report:', error);
        throw error;
    }
}

/**
 * Export with filters (for advanced export)
 * @param {string} projectSafeName - The URL-safe project identifier
 * @param {Object} filters - Export filters
 */
export async function exportWithFilters(projectSafeName, filters) {
    try {
        const params = new URLSearchParams();
        if (filters.entity_types) {
            params.append('entity_types', filters.entity_types.join(','));
        }
        if (filters.limit) {
            params.append('limit', filters.limit);
        }
        if (filters.offset) {
            params.append('offset', filters.offset);
        }

        const url = `/api/v1/projects/${projectSafeName}/export/entities/csv?${params.toString()}`;
        downloadFile(url);
        showNotification('Filtered export completed', 'success');

    } catch (error) {
        console.error('Filtered export failed:', error);
        showNotification(`Export failed: ${error.message}`, 'error');
    }
}
