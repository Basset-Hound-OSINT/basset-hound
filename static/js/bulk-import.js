/**
 * Bulk Import Module for Basset Hound
 *
 * Handles multi-step import process:
 * 1. File Upload/Paste - Upload CSV/JSON or paste data
 * 2. Preview & Field Mapping - Show data preview and configure field mappings
 * 3. Progress & Results - Show import progress and results
 */

let importState = {
    projectName: null,
    format: 'json',
    rawData: '',
    parsedData: [],
    fieldMapping: {},
    step: 1,
    importInProgress: false
};

/**
 * Initialize the bulk import module
 * Adds the Import button to the project header and sets up the modal
 */
export function initBulkImport(projectName) {
    importState.projectName = projectName;

    // Add Import button to the project header
    addImportButton();

    // Setup modal elements
    setupImportModal();

    // Setup event listeners
    setupEventListeners();
}

/**
 * Add Import button to the project header
 */
function addImportButton() {
    const projectInfo = document.querySelector('.project-info');
    if (!projectInfo) return;

    // Find the button group
    const downloadBtn = projectInfo.querySelector('#download-project-btn');
    if (!downloadBtn) return;

    // Create Import button
    const importBtn = document.createElement('button');
    importBtn.className = 'btn btn-sm btn-outline-success';
    importBtn.id = 'import-project-btn';
    importBtn.innerHTML = '<i class="fas fa-upload"></i> Import';
    importBtn.onclick = () => openBulkImportModal();

    // Insert before download button
    downloadBtn.parentElement.insertBefore(importBtn, downloadBtn);
}

/**
 * Create and setup the import modal structure in the DOM
 */
function setupImportModal() {
    // Check if modal already exists
    if (document.getElementById('bulk-import-overlay')) {
        return;
    }

    const html = `
        <div id="bulk-import-overlay" class="bulk-import-overlay" style="display:none;">
            <div class="bulk-import-modal">
                <div class="bulk-import-header">
                    <h5 id="bulk-import-title">Bulk Import</h5>
                    <button id="close-bulk-import" class="btn btn-sm btn-outline-secondary">&times;</button>
                </div>

                <div class="bulk-import-body">
                    <!-- Step 1: File Upload -->
                    <div id="step-1-upload" class="bulk-import-step" style="display:block;">
                        <h6 class="mb-3">Step 1: Upload or Paste Data</h6>

                        <div class="mb-3">
                            <label class="form-label">Format</label>
                            <select id="format-selector" class="form-control">
                                <option value="json">JSON</option>
                                <option value="csv">CSV</option>
                                <option value="neo4j">Neo4j Export (JSON)</option>
                            </select>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Upload File or Paste Data</label>
                            <div class="input-group">
                                <input type="file" id="import-file-input" class="form-control" accept=".json,.csv,.txt">
                                <button class="btn btn-outline-secondary" type="button" id="clear-file-btn">Clear</button>
                            </div>
                            <small class="form-text text-muted">Accept .json, .csv, or .txt files</small>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Or Paste Data Here</label>
                            <textarea id="import-data-textarea" class="form-control" rows="8" placeholder="Paste JSON or CSV data here..."></textarea>
                        </div>

                        <div id="upload-error" class="alert alert-danger" style="display:none;"></div>
                    </div>

                    <!-- Step 2: Preview & Field Mapping -->
                    <div id="step-2-mapping" class="bulk-import-step" style="display:none;">
                        <h6 class="mb-3">Step 2: Preview Data & Map Fields</h6>

                        <div class="mb-3">
                            <h6>Data Preview (First 10 rows)</h6>
                            <div id="preview-table-container" style="overflow-x: auto; max-height: 250px; border: 1px solid #ddd; border-radius: 4px;">
                                <table id="preview-table" class="table table-sm table-striped" style="margin-bottom: 0;">
                                    <thead style="position: sticky; top: 0; background-color: #f8f9fa;"></thead>
                                    <tbody></tbody>
                                </table>
                            </div>
                        </div>

                        <div class="mb-3">
                            <h6>Field Mapping</h6>
                            <p class="text-muted small">Map each column to an entity field. Leave unmapped columns blank to skip them.</p>
                            <div id="field-mapping-container"></div>
                        </div>

                        <div id="mapping-error" class="alert alert-danger" style="display:none;"></div>
                    </div>

                    <!-- Step 3: Progress & Results -->
                    <div id="step-3-results" class="bulk-import-step" style="display:none;">
                        <h6 class="mb-3">Step 3: Import Progress</h6>

                        <div class="mb-3">
                            <div id="progress-status" class="text-center mb-2">
                                <p>Preparing import...</p>
                            </div>
                            <div class="progress" style="height: 25px;">
                                <div id="progress-bar" class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 0%;">
                                    <span id="progress-percent">0%</span>
                                </div>
                            </div>
                        </div>

                        <div id="import-results" style="display:none;">
                            <div class="alert alert-info" id="import-summary"></div>

                            <div id="error-section" style="display:none;">
                                <h6>Errors</h6>
                                <div id="error-list" style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px; padding: 10px; background-color: #fff5f5;"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="bulk-import-footer">
                    <button id="bulk-import-back-btn" class="btn btn-secondary" style="display:none;">Back</button>
                    <button id="bulk-import-next-btn" class="btn btn-primary">Next</button>
                    <button id="bulk-import-import-btn" class="btn btn-success" style="display:none;">Import</button>
                    <button id="bulk-import-close-btn" class="btn btn-secondary" style="display:none;">Close</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', html);
}

/**
 * Setup event listeners for the import modal
 */
function setupEventListeners() {
    // Close button
    document.getElementById('close-bulk-import').addEventListener('click', closeBulkImportModal);
    document.getElementById('bulk-import-close-btn').addEventListener('click', closeBulkImportModal);

    // File input
    document.getElementById('import-file-input').addEventListener('change', handleFileSelect);
    document.getElementById('clear-file-btn').addEventListener('click', clearFileInput);

    // Format selector
    document.getElementById('format-selector').addEventListener('change', (e) => {
        importState.format = e.target.value;
    });

    // Navigation buttons
    document.getElementById('bulk-import-next-btn').addEventListener('click', handleNext);
    document.getElementById('bulk-import-back-btn').addEventListener('click', handleBack);
    document.getElementById('bulk-import-import-btn').addEventListener('click', handleImport);
}

/**
 * Open the bulk import modal
 */
function openBulkImportModal() {
    importState.step = 1;
    importState.rawData = '';
    importState.parsedData = [];
    importState.fieldMapping = {};
    importState.importInProgress = false;

    // Show overlay and reset to step 1
    const overlay = document.getElementById('bulk-import-overlay');
    overlay.style.display = 'block';

    document.getElementById('step-1-upload').style.display = 'block';
    document.getElementById('step-2-mapping').style.display = 'none';
    document.getElementById('step-3-results').style.display = 'none';

    document.getElementById('import-file-input').value = '';
    document.getElementById('import-data-textarea').value = '';
    document.getElementById('upload-error').style.display = 'none';

    updateNavigationButtons();
}

/**
 * Close the bulk import modal
 */
function closeBulkImportModal() {
    document.getElementById('bulk-import-overlay').style.display = 'none';
}

/**
 * Handle file selection
 */
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
        importState.rawData = event.target.result;
        document.getElementById('import-data-textarea').value = importState.rawData;
    };
    reader.readAsText(file);
}

/**
 * Clear file input
 */
function clearFileInput() {
    document.getElementById('import-file-input').value = '';
    document.getElementById('import-data-textarea').value = '';
    importState.rawData = '';
}

/**
 * Handle Next button - validate and move to next step
 */
async function handleNext() {
    if (importState.step === 1) {
        await proceedToStep2();
    } else if (importState.step === 2) {
        proceedToStep3();
    }
}

/**
 * Proceed from Step 1 to Step 2
 */
async function proceedToStep2() {
    const errorDiv = document.getElementById('upload-error');
    errorDiv.style.display = 'none';

    // Get data from textarea or file
    const dataText = document.getElementById('import-data-textarea').value.trim();
    if (!dataText) {
        errorDiv.textContent = 'Please upload a file or paste data.';
        errorDiv.style.display = 'block';
        return;
    }

    importState.rawData = dataText;
    importState.format = document.getElementById('format-selector').value;

    try {
        // Parse the data
        await parseAndValidateData(importState.rawData, importState.format);

        if (importState.parsedData.length === 0) {
            throw new Error('No valid data found in the input.');
        }

        // Move to step 2
        importState.step = 2;
        document.getElementById('step-1-upload').style.display = 'none';
        document.getElementById('step-2-mapping').style.display = 'block';

        // Show preview and field mapping
        showPreviewAndMapping();
        updateNavigationButtons();
    } catch (error) {
        errorDiv.textContent = 'Error parsing data: ' + error.message;
        errorDiv.style.display = 'block';
    }
}

/**
 * Parse and validate data based on format
 */
async function parseAndValidateData(dataText, format) {
    importState.parsedData = [];
    importState.fieldMapping = {};

    if (format === 'json' || format === 'neo4j') {
        // Parse JSON
        const json = JSON.parse(dataText);

        // Handle Neo4j export format (extract nodes array)
        if (format === 'neo4j') {
            if (json.results && json.results[0] && json.results[0].data) {
                // Neo4j Cypher result format
                importState.parsedData = json.results[0].data.map(row => row.row[0].properties || row.row[0]);
            } else if (Array.isArray(json)) {
                importState.parsedData = json;
            } else if (json.nodes) {
                importState.parsedData = json.nodes.map(node => node.properties || node);
            } else {
                importState.parsedData = [json];
            }
        } else {
            // Standard JSON - expect array
            importState.parsedData = Array.isArray(json) ? json : [json];
        }
    } else if (format === 'csv') {
        // Parse CSV
        const lines = dataText.split('\n').filter(line => line.trim());
        if (lines.length < 2) {
            throw new Error('CSV must have at least a header row and one data row.');
        }

        // Parse header
        const headers = parseCSVLine(lines[0]);

        // Parse rows
        importState.parsedData = lines.slice(1).map(line => {
            const values = parseCSVLine(line);
            const row = {};
            headers.forEach((header, index) => {
                row[header] = values[index] || '';
            });
            return row;
        });

        // Initialize field mapping for CSV (map headers to empty first)
        headers.forEach(header => {
            importState.fieldMapping[header] = '';
        });
    }

    // Limit preview to first 100 rows
    if (importState.parsedData.length > 100) {
        importState.parsedData = importState.parsedData.slice(0, 100);
    }
}

/**
 * Simple CSV line parser
 */
function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];

        if (char === '"') {
            if (inQuotes && line[i + 1] === '"') {
                // Escaped quote
                current += '"';
                i++;
            } else {
                // Toggle quote mode
                inQuotes = !inQuotes;
            }
        } else if (char === ',' && !inQuotes) {
            result.push(current.trim());
            current = '';
        } else {
            current += char;
        }
    }

    result.push(current.trim());
    return result;
}

/**
 * Show preview table and field mapping UI
 */
function showPreviewAndMapping() {
    // Show preview table
    const headers = Object.keys(importState.parsedData[0] || {});
    const previewTableHead = document.querySelector('#preview-table thead');
    const previewTableBody = document.querySelector('#preview-table tbody');

    previewTableHead.innerHTML = '<tr>' +
        headers.map(h => `<th>${escapeHtml(h)}</th>`).join('') +
        '</tr>';

    previewTableBody.innerHTML = importState.parsedData.slice(0, 10).map(row =>
        '<tr>' + headers.map(h =>
            `<td>${escapeHtml(String(row[h] || ''))}</td>`
        ).join('') + '</tr>'
    ).join('');

    // Show field mapping UI
    const mappingContainer = document.getElementById('field-mapping-container');
    mappingContainer.innerHTML = '';

    // Get available entity fields from config
    const availableFields = getAvailableEntityFields();

    headers.forEach(header => {
        const div = document.createElement('div');
        div.className = 'mb-2';

        const label = document.createElement('label');
        label.className = 'form-label';
        label.textContent = header;

        const select = document.createElement('select');
        select.className = 'form-control form-control-sm';
        select.id = `mapping-${header}`;
        select.dataset.column = header;

        // Add empty option
        const emptyOption = document.createElement('option');
        emptyOption.value = '';
        emptyOption.textContent = '(Skip)';
        select.appendChild(emptyOption);

        // Add available fields
        availableFields.forEach(field => {
            const option = document.createElement('option');
            option.value = field.path;
            option.textContent = field.label;
            select.appendChild(option);
        });

        select.addEventListener('change', (e) => {
            importState.fieldMapping[header] = e.target.value;
        });

        div.appendChild(label);
        div.appendChild(select);

        // Add sample data
        const sample = document.createElement('small');
        sample.className = 'form-text text-muted d-block';
        sample.textContent = `Sample: "${escapeHtml(String(importState.parsedData[0][header] || ''))}"`;
        div.appendChild(sample);

        mappingContainer.appendChild(div);
    });
}

/**
 * Get available entity fields from config
 */
function getAvailableEntityFields() {
    const fields = [];

    if (!window.appConfig || !window.appConfig.sections) {
        return fields;
    }

    window.appConfig.sections.forEach(section => {
        section.fields.forEach(field => {
            const label = field.label || field.id;
            const sectionName = section.name || section.id;

            fields.push({
                path: `profile.${section.id}.${field.id}`,
                label: `${sectionName} > ${label}`,
                type: field.type
            });
        });
    });

    return fields;
}

/**
 * Proceed from Step 2 to Step 3
 */
function proceedToStep3() {
    const errorDiv = document.getElementById('mapping-error');
    errorDiv.style.display = 'none';

    // Validate that at least one field is mapped
    const mappedCount = Object.values(importState.fieldMapping).filter(v => v).length;
    if (mappedCount === 0) {
        errorDiv.textContent = 'Please map at least one field.';
        errorDiv.style.display = 'block';
        return;
    }

    // Move to step 3
    importState.step = 3;
    document.getElementById('step-2-mapping').style.display = 'none';
    document.getElementById('step-3-results').style.display = 'block';
    document.getElementById('import-results').style.display = 'none';

    updateNavigationButtons();
}

/**
 * Handle Back button
 */
function handleBack() {
    if (importState.step === 2) {
        importState.step = 1;
        document.getElementById('step-1-upload').style.display = 'block';
        document.getElementById('step-2-mapping').style.display = 'none';
    } else if (importState.step === 3 && !importState.importInProgress) {
        importState.step = 2;
        document.getElementById('step-2-mapping').style.display = 'block';
        document.getElementById('step-3-results').style.display = 'none';
    }

    updateNavigationButtons();
}

/**
 * Update navigation buttons based on current step
 */
function updateNavigationButtons() {
    const backBtn = document.getElementById('bulk-import-back-btn');
    const nextBtn = document.getElementById('bulk-import-next-btn');
    const importBtn = document.getElementById('bulk-import-import-btn');
    const closeBtn = document.getElementById('bulk-import-close-btn');

    if (importState.step === 1) {
        backBtn.style.display = 'none';
        nextBtn.style.display = 'block';
        nextBtn.textContent = 'Next';
        importBtn.style.display = 'none';
        closeBtn.style.display = 'none';
    } else if (importState.step === 2) {
        backBtn.style.display = 'block';
        nextBtn.style.display = 'block';
        nextBtn.textContent = 'Next';
        importBtn.style.display = 'none';
        closeBtn.style.display = 'none';
    } else if (importState.step === 3) {
        backBtn.style.display = importState.importInProgress ? 'none' : 'block';
        nextBtn.style.display = 'none';
        importBtn.style.display = importState.importInProgress ? 'none' : 'block';
        closeBtn.style.display = importState.importInProgress ? 'none' : 'block';
    }
}

/**
 * Handle Import button - start the import process
 */
async function handleImport() {
    importState.importInProgress = true;
    updateNavigationButtons();

    try {
        // Build entities from parsed data
        const entities = buildEntitiesFromData();

        // Call import API
        const response = await fetch(
            `/api/v1/projects/${importState.projectName}/bulk/import`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    entities: entities,
                    update_existing: false
                })
            }
        );

        if (!response.ok) {
            throw new Error(await response.text());
        }

        const result = await response.json();

        // Show results
        showImportResults(result);
    } catch (error) {
        console.error('Import error:', error);
        showImportError(error.message);
    } finally {
        importState.importInProgress = false;
    }
}

/**
 * Build entity objects from parsed data using field mapping
 */
function buildEntitiesFromData() {
    const entities = [];

    importState.parsedData.forEach((row, rowIndex) => {
        const entity = {
            profile: {}
        };

        // Group fields by section
        const sectionMap = {};

        Object.entries(importState.fieldMapping).forEach(([column, fieldPath]) => {
            if (!fieldPath || !row[column]) return;

            // Parse field path: profile.{section}.{field}
            const parts = fieldPath.split('.');
            if (parts.length < 3) return;

            const section = parts[1];
            const field = parts[2];
            const value = row[column];

            if (!sectionMap[section]) {
                sectionMap[section] = {};
            }

            sectionMap[section][field] = [value];
        });

        entity.profile = sectionMap;

        if (Object.keys(sectionMap).length > 0) {
            entities.push(entity);
        }
    });

    return entities;
}

/**
 * Show import results
 */
function showImportResults(result) {
    document.getElementById('import-results').style.display = 'block';

    const summary = document.getElementById('import-summary');
    summary.innerHTML = `
        <strong>Import Complete!</strong><br>
        Total: ${result.total} | Successful: ${result.successful} | Failed: ${result.failed}
    `;

    // Show errors if any
    if (result.errors && result.errors.length > 0) {
        document.getElementById('error-section').style.display = 'block';
        const errorList = document.getElementById('error-list');
        errorList.innerHTML = result.errors.map(err =>
            `<div class="mb-2"><strong>Row ${err.index || 'N/A'}:</strong> ${escapeHtml(err.error)}</div>`
        ).join('');
    } else {
        document.getElementById('error-section').style.display = 'none';
    }

    importState.importInProgress = false;
    updateNavigationButtons();
}

/**
 * Show import error
 */
function showImportError(errorMessage) {
    document.getElementById('import-results').style.display = 'block';

    const summary = document.getElementById('import-summary');
    summary.className = 'alert alert-danger';
    summary.innerHTML = `<strong>Import Failed:</strong> ${escapeHtml(errorMessage)}`;

    importState.importInProgress = false;
    updateNavigationButtons();
}

/**
 * Utility function to escape HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
