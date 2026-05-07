/**
 * PDF Report Handler - LaTeX-based PDF generation and download functionality
 *
 * Provides functions for generating and downloading PDF reports from the backend
 * LaTeX reporting service.
 */

/**
 * Download a PDF report for a single entity
 * @param {string} entityId - The entity ID
 * @param {string} projectName - The project name (optional)
 */
export async function downloadEntityPdfReport(entityId, projectName = null) {
    try {
        const project = projectName || window.currentProjectId || 'default';

        const response = await fetch(
            `/api/v1/projects/${project}/reports/pdf/entity/${entityId}`,
            { method: 'POST' }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const blob = await response.blob();
        downloadBlob(blob, `${entityId}_profile.pdf`);
    } catch (error) {
        console.error('Error downloading entity PDF:', error);
        alert(`Failed to download PDF: ${error.message}`);
    }
}

/**
 * Download a PDF report for multiple entities (investigation summary)
 * @param {string[]} entityIds - Array of entity IDs
 * @param {string} projectName - The project name (optional)
 */
export async function downloadInvestigationPdfReport(entityIds, projectName = null) {
    try {
        if (!entityIds || entityIds.length === 0) {
            throw new Error('No entities selected');
        }

        const project = projectName || window.currentProjectId || 'default';
        const queryString = entityIds.map(id => `entity_ids=${encodeURIComponent(id)}`).join('&');

        const response = await fetch(
            `/api/v1/projects/${project}/reports/pdf/investigation?${queryString}`,
            { method: 'POST' }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const blob = await response.blob();
        downloadBlob(blob, `investigation_${project}.pdf`);
    } catch (error) {
        console.error('Error downloading investigation PDF:', error);
        alert(`Failed to download PDF: ${error.message}`);
    }
}

/**
 * Download a PDF report showing relationships for an entity
 * @param {string} entityId - The entity ID
 * @param {number} depth - Relationship depth (1-5, default 2)
 * @param {string} projectName - The project name (optional)
 */
export async function downloadRelationshipPdfReport(entityId, depth = 2, projectName = null) {
    try {
        const project = projectName || window.currentProjectId || 'default';

        const response = await fetch(
            `/api/v1/projects/${project}/reports/pdf/relationship/${entityId}?depth=${depth}`,
            { method: 'POST' }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const blob = await response.blob();
        downloadBlob(blob, `${entityId}_relationships.pdf`);
    } catch (error) {
        console.error('Error downloading relationship PDF:', error);
        alert(`Failed to download PDF: ${error.message}`);
    }
}

/**
 * Download a PDF timeline report for an entity
 * @param {string} entityId - The entity ID
 * @param {string} projectName - The project name (optional)
 */
export async function downloadTimelinePdfReport(entityId, projectName = null) {
    try {
        const project = projectName || window.currentProjectId || 'default';

        const response = await fetch(
            `/api/v1/projects/${project}/reports/pdf/timeline/${entityId}`,
            { method: 'POST' }
        );

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const blob = await response.blob();
        downloadBlob(blob, `${entityId}_timeline.pdf`);
    } catch (error) {
        console.error('Error downloading timeline PDF:', error);
        alert(`Failed to download PDF: ${error.message}`);
    }
}

/**
 * Helper function to trigger blob download
 * @param {Blob} blob - The file blob
 * @param {string} filename - The filename to save as
 */
function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * Create a PDF download button and add it to a container
 * @param {HTMLElement} container - The container element
 * @param {string} entityId - The entity ID
 * @param {string} reportType - Type of report: 'entity', 'relationship', or 'timeline'
 * @param {object} options - Additional options
 */
export function createPdfDownloadButton(container, entityId, reportType = 'entity', options = {}) {
    const button = document.createElement('button');
    button.className = 'btn btn-success btn-sm';
    button.id = `pdf-download-${reportType}-${entityId}`;
    button.innerHTML = '<i class="fas fa-file-pdf"></i> Download PDF';

    button.addEventListener('click', async () => {
        try {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';

            switch (reportType) {
                case 'entity':
                    await downloadEntityPdfReport(entityId, options.projectName);
                    break;
                case 'relationship':
                    await downloadRelationshipPdfReport(
                        entityId,
                        options.depth || 2,
                        options.projectName
                    );
                    break;
                case 'timeline':
                    await downloadTimelinePdfReport(entityId, options.projectName);
                    break;
                default:
                    throw new Error(`Unknown report type: ${reportType}`);
            }
        } catch (error) {
            console.error(`Error generating ${reportType} PDF:`, error);
            alert(`Failed to generate PDF: ${error.message}`);
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-file-pdf"></i> Download PDF';
        }
    });

    if (container) {
        container.appendChild(button);
    }

    return button;
}
