// merge-ui.js - Handles duplicate detection and entity merging UI

import { getDisplayName } from './utils.js';

/**
 * Initialize merge UI for an entity
 * @param {string} entityId - The entity ID
 * @param {string} projectName - The project name
 */
export async function initMergeUI(entityId, projectName) {
    // Create and inject the "Find Duplicates" button if it doesn't exist
    const actionButtons = document.querySelector('.d-flex.gap-2');

    if (actionButtons && !document.getElementById('find-duplicates-btn')) {
        const findDuplicatesBtn = document.createElement('button');
        findDuplicatesBtn.id = 'find-duplicates-btn';
        findDuplicatesBtn.className = 'btn btn-warning';
        findDuplicatesBtn.innerHTML = '<i class="fas fa-clone"></i> Find Duplicates';
        findDuplicatesBtn.addEventListener('click', () => {
            findDuplicates(entityId, projectName);
        });

        // Insert after the Refresh button
        const refreshBtn = actionButtons.querySelector('.btn-outline-primary');
        if (refreshBtn) {
            refreshBtn.parentNode.insertBefore(findDuplicatesBtn, refreshBtn.nextSibling);
        } else {
            actionButtons.insertBefore(findDuplicatesBtn, actionButtons.firstChild);
        }
    }
}

/**
 * Find duplicate candidates for an entity
 * @param {string} entityId - The entity ID
 * @param {string} projectName - The project name
 */
async function findDuplicates(entityId, projectName) {
    // Create modal container if it doesn't exist
    let modal = document.getElementById('duplicates-modal');
    if (!modal) {
        createDuplicatesModal();
        modal = document.getElementById('duplicates-modal');
    }

    // Show loading state
    const modalBody = modal.querySelector('.modal-body');
    modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Finding duplicate candidates...</p></div>';

    try {
        // Fetch the current entity details
        const currentEntityRes = await fetch(`/get_person/${entityId}`);
        if (!currentEntityRes.ok) throw new Error('Failed to fetch current entity');
        const currentEntity = await currentEntityRes.json();

        // Fetch duplicate suggestions
        const duplicatesRes = await fetch(`/api/v1/suggestions/entity/${entityId}?min_confidence=0.7`);
        if (!duplicatesRes.ok) throw new Error('Failed to fetch duplicate suggestions');
        const duplicatesData = await duplicatesRes.json();

        // Extract duplicate matches (we'll use all matches and treat them as potential duplicates)
        const allMatches = [];
        if (duplicatesData.data && duplicatesData.data.suggestions) {
            duplicatesData.data.suggestions.forEach(group => {
                if (group.matches) {
                    allMatches.push(...group.matches);
                }
            });
        }

        // Sort by confidence score (highest first)
        allMatches.sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0));

        if (allMatches.length === 0) {
            showNoDuplicatesFound(modal);
        } else {
            // Fetch details for each matched entity
            const duplicates = [];
            for (const match of allMatches) {
                try {
                    const dupRes = await fetch(`/get_person/${match.entity_id}`);
                    if (dupRes.ok) {
                        const dupEntity = await dupRes.json();
                        duplicates.push({
                            ...match,
                            entity: dupEntity
                        });
                    }
                } catch (e) {
                    console.error(`Failed to fetch entity ${match.entity_id}:`, e);
                }
            }

            if (duplicates.length === 0) {
                showNoDuplicatesFound(modal);
            } else {
                renderDuplicatesList(modal, currentEntity, duplicates, entityId, projectName);
            }
        }
    } catch (error) {
        console.error('Error finding duplicates:', error);
        modalBody.innerHTML = `<div class="alert alert-danger" role="alert">Error finding duplicates: ${error.message}</div>`;
    }

    // Show the modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Render the duplicates list modal
 */
function renderDuplicatesList(modal, currentEntity, duplicates, currentEntityId, projectName) {
    const modalBody = modal.querySelector('.modal-body');
    modalBody.innerHTML = '';

    // Create header with instructions
    const header = document.createElement('div');
    header.className = 'mb-4';
    header.innerHTML = `
        <h6 class="mb-2">Potential Duplicates Found: <strong>${duplicates.length}</strong></h6>
        <p class="text-muted small mb-0">Select a duplicate to compare and merge. The merge operation is irreversible.</p>
    `;
    modalBody.appendChild(header);

    // Create table
    const table = document.createElement('table');
    table.className = 'table table-hover table-sm mb-3';
    table.style.maxHeight = '400px';
    table.style.overflowY = 'auto';

    const thead = document.createElement('thead');
    thead.className = 'table-light';
    thead.innerHTML = `
        <tr>
            <th style="width: 30px;">Select</th>
            <th>Name</th>
            <th>Entity Type</th>
            <th>Confidence</th>
        </tr>
    `;
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    duplicates.forEach((dup, idx) => {
        const row = document.createElement('tr');
        row.style.cursor = 'pointer';

        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'duplicate-select';
        radio.value = dup.entity_id;
        radio.id = `dup-${idx}`;

        const name = getDisplayName(dup.entity) || dup.entity_id;
        const confidence = ((dup.confidence_score || 0) * 100).toFixed(0);
        const entityType = dup.entity.entity_type || 'Unknown';

        row.innerHTML = `
            <td><input type="radio" name="duplicate-select" value="${dup.entity_id}" id="dup-${idx}"></td>
            <td>${name}</td>
            <td><span class="badge bg-secondary">${entityType}</span></td>
            <td><span class="badge bg-info">${confidence}%</span></td>
        `;

        // Add click handler to select radio
        row.addEventListener('click', () => {
            document.getElementById(`dup-${idx}`).checked = true;
        });

        tbody.appendChild(row);
    });

    table.appendChild(tbody);
    modalBody.appendChild(table);

    // Create merge direction options
    const directionDiv = document.createElement('div');
    directionDiv.className = 'mb-3';
    directionDiv.innerHTML = `
        <h6 class="mb-2">Merge Direction:</h6>
        <div class="form-check">
            <input class="form-check-input" type="radio" name="merge-direction" id="merge-into-current" value="into-current" checked>
            <label class="form-check-label" for="merge-into-current">
                Merge selected into current (keep current)
            </label>
        </div>
        <div class="form-check">
            <input class="form-check-input" type="radio" name="merge-direction" id="merge-current-into" value="current-into">
            <label class="form-check-label" for="merge-current-into">
                Merge current into selected (keep selected)
            </label>
        </div>
    `;
    modalBody.appendChild(directionDiv);

    // Create action buttons
    const buttonsDiv = document.createElement('div');
    buttonsDiv.className = 'd-flex gap-2 justify-content-end mt-4 pt-3 border-top';

    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-secondary';
    cancelBtn.textContent = 'Cancel';
    cancelBtn.addEventListener('click', () => {
        bootstrap.Modal.getInstance(modal).hide();
    });

    const mergeBtn = document.createElement('button');
    mergeBtn.className = 'btn btn-danger';
    mergeBtn.innerHTML = '<i class="fas fa-code-branch"></i> Merge';
    mergeBtn.addEventListener('click', () => {
        performMerge(modal, currentEntity, currentEntityId, projectName);
    });

    buttonsDiv.appendChild(cancelBtn);
    buttonsDiv.appendChild(mergeBtn);
    modalBody.appendChild(buttonsDiv);
}

/**
 * Show "no duplicates found" message
 */
function showNoDuplicatesFound(modal) {
    const modalBody = modal.querySelector('.modal-body');
    modalBody.innerHTML = `
        <div class="alert alert-info text-center" role="alert">
            <i class="fas fa-check-circle mb-2" style="font-size: 2rem;"></i>
            <p class="mb-0"><strong>No duplicates found</strong></p>
            <p class="text-muted small mb-0">This entity does not appear to have any duplicate matches.</p>
        </div>
    `;
}

/**
 * Perform the merge operation
 */
async function performMerge(modal, currentEntity, currentEntityId, projectName) {
    const selectedDuplicate = document.querySelector('input[name="duplicate-select"]:checked');
    if (!selectedDuplicate) {
        alert('Please select a duplicate to merge');
        return;
    }

    const mergeDirection = document.querySelector('input[name="merge-direction"]:checked').value;

    // Determine which entity to keep and which to merge
    let keepEntityId, mergeEntityId;
    if (mergeDirection === 'into-current') {
        keepEntityId = currentEntityId;
        mergeEntityId = selectedDuplicate.value;
    } else {
        keepEntityId = selectedDuplicate.value;
        mergeEntityId = currentEntityId;
    }

    // Show confirmation dialog
    if (!confirm('This action is irreversible. The merged entity will be permanently deleted. Proceed?')) {
        return;
    }

    // Show loading state
    const modalBody = modal.querySelector('.modal-body');
    modalBody.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Merging entities...</p></div>';

    try {
        const response = await fetch('/api/v1/suggestions/linking/merge-entities', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                entity_id_1: currentEntityId,
                entity_id_2: selectedDuplicate.value,
                keep_entity_id: keepEntityId,
                reason: 'Duplicate entity merged via UI',
                created_by: 'web-ui'
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to merge entities');
        }

        const result = await response.json();

        // Hide modal
        bootstrap.Modal.getInstance(modal).hide();

        // Show success toast
        showSuccessToast('Entities merged successfully!');

        // Refresh the current entity details if it was kept
        if (keepEntityId === currentEntityId) {
            const updated = await fetch(`/get_person/${currentEntityId}`).then(r => r.json());
            // Trigger a refresh of the UI
            const detailsContainer = document.getElementById('person-details');
            if (detailsContainer) {
                const { renderPersonDetails } = await import('./ui-person-details.js');
                await renderPersonDetails(detailsContainer, updated);
            }
        } else {
            // The current entity was merged away, reload the page to go back to list
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        }

        // Remove the merged entity from the sidebar if visible
        const mergedListItem = document.querySelector(`[data-person-id="${mergeEntityId}"]`);
        if (mergedListItem) {
            mergedListItem.style.transition = 'opacity 0.3s ease';
            mergedListItem.style.opacity = '0';
            setTimeout(() => mergedListItem.remove(), 300);
        }

    } catch (error) {
        console.error('Error merging entities:', error);
        // Show error in modal
        const modalBody = modal.querySelector('.modal-body');
        modalBody.innerHTML = `<div class="alert alert-danger" role="alert">Error merging entities: ${error.message}</div>`;
    }
}

/**
 * Create the duplicates modal if it doesn't exist
 */
function createDuplicatesModal() {
    if (document.getElementById('duplicates-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'duplicates-modal';
    modal.className = 'modal fade';
    modal.tabIndex = '-1';
    modal.setAttribute('aria-labelledby', 'duplicates-modal-label');
    modal.setAttribute('aria-hidden', 'true');

    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="duplicates-modal-label">
                        <i class="fas fa-clone me-2"></i>Find Duplicates
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <!-- Content will be rendered here -->
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

/**
 * Show a success toast notification
 */
function showSuccessToast(message) {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.style.position = 'fixed';
        toastContainer.style.top = '20px';
        toastContainer.style.right = '20px';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast align-items-center text-white bg-success border-0';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    toast.style.minWidth = '300px';

    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas fa-check-circle me-2"></i>${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Create Bootstrap toast and show it
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();

    // Remove from DOM after it hides
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}
