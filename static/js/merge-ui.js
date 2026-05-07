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
 * Get confidence badge color based on score
 * @param {number} score - Confidence score (0-1)
 * @returns {string} Bootstrap color class
 */
function getConfidenceBadgeClass(score) {
    if (score >= 0.8) return 'bg-success';
    if (score >= 0.6) return 'bg-warning';
    return 'bg-danger';
}

/**
 * Extract key data from entity for comparison
 * @param {object} entity - The entity object
 * @returns {object} Key fields for comparison
 */
function extractEntityKeyData(entity) {
    const data = {
        name: getDisplayName(entity),
        email: null,
        phone: null,
        entity_type: entity.entity_type || 'Unknown',
        created_at: entity.created_at || 'N/A'
    };

    // Extract email and phone from profile
    if (entity.profile) {
        for (const sectionId in entity.profile) {
            const section = entity.profile[sectionId];
            if (section.email) {
                data.email = Array.isArray(section.email) ? section.email[0] : section.email;
            }
            if (section.phone) {
                data.phone = Array.isArray(section.phone) ? section.phone[0] : section.phone;
            }
            if (section.name && typeof section.name === 'object') {
                // Try to build a better name from name components
                const nameObj = section.name;
                const nameParts = [];
                if (nameObj.first_name) nameParts.push(nameObj.first_name);
                if (nameObj.middle_name) nameParts.push(nameObj.middle_name);
                if (nameObj.last_name) nameParts.push(nameObj.last_name);
                if (nameParts.length > 0) {
                    data.name = nameParts.join(' ');
                }
            }
        }
    }

    return data;
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

        // Fetch duplicate suggestions using the API endpoint
        const duplicatesRes = await fetch(`/api/v1/suggestions/entity/${entityId}?type=duplicate&min_confidence=0.6&limit=100`);
        if (!duplicatesRes.ok) {
            throw new Error(`Failed to fetch duplicate suggestions (${duplicatesRes.status})`);
        }
        const duplicatesData = await duplicatesRes.json();

        // Extract all matches from suggestions
        const allMatches = [];
        if (duplicatesData.data && duplicatesData.data.suggestions) {
            duplicatesData.data.suggestions.forEach(group => {
                if (group.matches) {
                    allMatches.push(...group.matches);
                }
            });
        }

        // Sort by confidence score (highest first) and take top 5
        allMatches.sort((a, b) => (b.confidence_score || 0) - (a.confidence_score || 0));
        const topMatches = allMatches.slice(0, 5);

        if (topMatches.length === 0) {
            showNoDuplicatesFound(modal);
        } else {
            // Fetch details for each matched entity
            const duplicates = [];
            for (const match of topMatches) {
                try {
                    const matched_entity_id = match.matched_entity_id;
                    if (!matched_entity_id) continue;

                    const dupRes = await fetch(`/get_person/${matched_entity_id}`);
                    if (dupRes.ok) {
                        const dupEntity = await dupRes.json();
                        duplicates.push({
                            ...match,
                            entity: dupEntity,
                            entity_id: matched_entity_id
                        });
                    } else {
                        console.warn(`Failed to fetch entity ${matched_entity_id}`);
                    }
                } catch (e) {
                    console.error(`Failed to fetch entity ${match.matched_entity_id}:`, e);
                }
            }

            if (duplicates.length === 0) {
                showNoDuplicatesFound(modal);
            } else {
                renderDuplicatesComparison(modal, currentEntity, duplicates, entityId, projectName);
            }
        }
    } catch (error) {
        console.error('Error finding duplicates:', error);
        modalBody.innerHTML = `<div class="alert alert-danger" role="alert">
            <strong>Error finding duplicates:</strong> ${error.message}
            <br><small class="text-muted">Check console for details.</small>
        </div>`;
    }

    // Show the modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Render the duplicates comparison view with side-by-side comparison
 */
function renderDuplicatesComparison(modal, currentEntity, duplicates, currentEntityId, projectName) {
    const modalBody = modal.querySelector('.modal-body');
    modalBody.innerHTML = '';

    // Create header with instructions
    const header = document.createElement('div');
    header.className = 'mb-3 pb-3 border-bottom';
    header.innerHTML = `
        <h6 class="mb-2"><i class="fas fa-info-circle me-2"></i>Potential Duplicates Found: <strong>${duplicates.length}</strong></h6>
        <p class="text-muted small mb-0">Select a duplicate below to compare. The merge operation is <strong>irreversible</strong>.</p>
    `;
    modalBody.appendChild(header);

    // Create tabs for each duplicate
    const tabsContainer = document.createElement('div');
    tabsContainer.className = 'mb-4';

    const tabNav = document.createElement('ul');
    tabNav.className = 'nav nav-pills nav-fill';
    tabNav.role = 'tablist';

    duplicates.forEach((dup, idx) => {
        const confidence = dup.confidence_score || 0;
        const confidencePercent = (confidence * 100).toFixed(0);
        const badgeClass = getConfidenceBadgeClass(confidence);

        const tabItem = document.createElement('li');
        tabItem.className = 'nav-item';
        tabItem.role = 'presentation';

        const tabBtn = document.createElement('button');
        tabBtn.className = `nav-link ${idx === 0 ? 'active' : ''}`;
        tabBtn.id = `dup-tab-${idx}`;
        tabBtn.setAttribute('data-bs-toggle', 'tab');
        tabBtn.setAttribute('data-bs-target', `#dup-panel-${idx}`);
        tabBtn.setAttribute('type', 'button');
        tabBtn.role = 'tab';
        tabBtn.setAttribute('aria-controls', `dup-panel-${idx}`);
        tabBtn.setAttribute('aria-selected', idx === 0 ? 'true' : 'false');

        const dupName = getDisplayName(dup.entity);
        tabBtn.innerHTML = `
            <div class="d-flex align-items-center justify-content-center gap-2">
                <span>${dupName}</span>
                <span class="badge ${badgeClass}">${confidencePercent}%</span>
            </div>
        `;

        tabItem.appendChild(tabBtn);
        tabNav.appendChild(tabItem);
    });

    tabsContainer.appendChild(tabNav);

    // Create tab content panels
    const tabContent = document.createElement('div');
    tabContent.className = 'tab-content mt-3';

    duplicates.forEach((dup, idx) => {
        const confidence = dup.confidence_score || 0;
        const tabPane = document.createElement('div');
        tabPane.className = `tab-pane fade ${idx === 0 ? 'show active' : ''}`;
        tabPane.id = `dup-panel-${idx}`;
        tabPane.role = 'tabpanel';
        tabPane.setAttribute('aria-labelledby', `dup-tab-${idx}`);

        // Create side-by-side comparison
        const comparisonGrid = renderComparisonGrid(currentEntity, dup.entity, confidence);
        tabPane.appendChild(comparisonGrid);

        // Add merge button for this duplicate
        const mergeButtonsDiv = document.createElement('div');
        mergeButtonsDiv.className = 'd-flex gap-2 justify-content-end mt-4 pt-3 border-top';

        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn btn-secondary';
        cancelBtn.textContent = 'Cancel';
        cancelBtn.addEventListener('click', () => {
            bootstrap.Modal.getInstance(modal).hide();
        });

        const mergeBtn = document.createElement('button');
        mergeBtn.className = 'btn btn-danger';
        mergeBtn.innerHTML = '<i class="fas fa-code-branch me-2"></i>Merge Into This';
        mergeBtn.addEventListener('click', () => {
            performMergeWithConfirmation(modal, currentEntity, dup, currentEntityId, projectName);
        });

        mergeButtonsDiv.appendChild(cancelBtn);
        mergeButtonsDiv.appendChild(mergeBtn);
        tabPane.appendChild(mergeButtonsDiv);

        tabContent.appendChild(tabPane);
    });

    modalBody.appendChild(tabsContainer);
    modalBody.appendChild(tabContent);
}

/**
 * Render a side-by-side comparison grid
 */
function renderComparisonGrid(entity1, entity2, confidenceScore) {
    const container = document.createElement('div');
    container.className = 'row g-3 mb-3';

    // Extract key data
    const data1 = extractEntityKeyData(entity1);
    const data2 = extractEntityKeyData(entity2);

    // Left column (current entity)
    const leftCol = document.createElement('div');
    leftCol.className = 'col-md-6';

    const leftCard = document.createElement('div');
    leftCard.className = 'card h-100 border-primary';

    const leftHeader = document.createElement('div');
    leftHeader.className = 'card-header bg-primary text-white';
    leftHeader.innerHTML = '<strong><i class="fas fa-circle me-2"></i>Current Entity</strong>';
    leftCard.appendChild(leftHeader);

    const leftBody = document.createElement('div');
    leftBody.className = 'card-body';
    leftBody.innerHTML = renderEntityComparisonData(data1);
    leftCard.appendChild(leftBody);

    leftCol.appendChild(leftCard);
    container.appendChild(leftCol);

    // Right column (duplicate entity)
    const rightCol = document.createElement('div');
    rightCol.className = 'col-md-6';

    const rightCard = document.createElement('div');
    rightCard.className = 'card h-100 border-danger';

    const rightHeader = document.createElement('div');
    rightHeader.className = 'card-header bg-danger text-white';
    rightHeader.innerHTML = '<strong><i class="fas fa-circle me-2"></i>Potential Duplicate</strong>';
    rightCard.appendChild(rightHeader);

    const rightBody = document.createElement('div');
    rightBody.className = 'card-body';
    rightBody.innerHTML = renderEntityComparisonData(data2);
    rightCard.appendChild(rightBody);

    rightCol.appendChild(rightCard);
    container.appendChild(rightCol);

    // Add confidence score indicator
    const scoreDiv = document.createElement('div');
    scoreDiv.className = 'alert alert-info mt-3 mb-0';
    const confidence = (confidenceScore * 100).toFixed(0);
    const badgeClass = getConfidenceBadgeClass(confidenceScore);
    scoreDiv.innerHTML = `
        <div class="d-flex align-items-center justify-content-between">
            <div><strong><i class="fas fa-chart-line me-2"></i>Confidence Match Score:</strong></div>
            <span class="badge ${badgeClass}" style="font-size: 1rem;">${confidence}%</span>
        </div>
    `;
    container.appendChild(scoreDiv);

    return container;
}

/**
 * Render entity comparison data as HTML
 */
function renderEntityComparisonData(data) {
    return `
        <table class="table table-sm mb-0">
            <tbody>
                <tr>
                    <td class="fw-bold w-40">Name:</td>
                    <td>${data.name || '<em class="text-muted">Not provided</em>'}</td>
                </tr>
                <tr>
                    <td class="fw-bold">Email:</td>
                    <td>${data.email ? `<a href="mailto:${data.email}">${data.email}</a>` : '<em class="text-muted">Not provided</em>'}</td>
                </tr>
                <tr>
                    <td class="fw-bold">Phone:</td>
                    <td>${data.phone || '<em class="text-muted">Not provided</em>'}</td>
                </tr>
                <tr>
                    <td class="fw-bold">Entity Type:</td>
                    <td><span class="badge bg-secondary">${data.entity_type}</span></td>
                </tr>
                <tr>
                    <td class="fw-bold">Created:</td>
                    <td><small class="text-muted">${data.created_at}</small></td>
                </tr>
            </tbody>
        </table>
    `;
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
 * Perform merge with confirmation dialog
 */
async function performMergeWithConfirmation(modal, currentEntity, duplicateEntity, currentEntityId, projectName) {
    const duplicateId = duplicateEntity.entity_id;
    const currentName = getDisplayName(currentEntity);
    const duplicateName = getDisplayName(duplicateEntity.entity);

    // Show confirmation warning
    const confirmDiv = document.createElement('div');
    confirmDiv.className = 'alert alert-danger alert-dismissible fade show mt-3';
    confirmDiv.role = 'alert';
    confirmDiv.innerHTML = `
        <div class="d-flex align-items-start gap-3">
            <i class="fas fa-exclamation-triangle" style="font-size: 1.5rem; margin-top: 2px;"></i>
            <div>
                <h5 class="alert-heading"><strong>⚠️ Warning: Irreversible Action</strong></h5>
                <p class="mb-2">This will permanently merge <strong>${duplicateName}</strong> into <strong>${currentName}</strong>.</p>
                <p class="mb-2">All data, relationships, and history from the duplicate will be transferred to the current entity.</p>
                <p class="mb-0"><strong>The duplicate entity will be deleted and cannot be recovered.</strong></p>
                <hr>
                <div class="form-check mt-2">
                    <input class="form-check-input" type="checkbox" id="confirm-merge-checkbox">
                    <label class="form-check-label" for="confirm-merge-checkbox">
                        I understand this is irreversible and want to proceed
                    </label>
                </div>
            </div>
        </div>
    `;

    // Get the tab pane that's currently showing
    const currentTabPane = document.querySelector('.tab-pane.show.active');
    const buttonsDiv = currentTabPane.querySelector('.d-flex.gap-2.justify-content-end');
    const mergeBtn = buttonsDiv.querySelector('.btn-danger');

    // Insert confirmation after the comparison
    const comparisonGrid = currentTabPane.querySelector('.row.g-3.mb-3');
    comparisonGrid.parentNode.insertBefore(confirmDiv, comparisonGrid.nextSibling);

    // Disable merge button until confirmed
    mergeBtn.disabled = true;
    mergeBtn.innerHTML = '<i class="fas fa-lock me-2"></i>Confirm above to merge';

    // Enable merge button when checkbox is checked
    document.getElementById('confirm-merge-checkbox').addEventListener('change', (e) => {
        mergeBtn.disabled = !e.target.checked;
        if (e.target.checked) {
            mergeBtn.innerHTML = '<i class="fas fa-code-branch me-2"></i>Merge Into This';
        } else {
            mergeBtn.innerHTML = '<i class="fas fa-lock me-2"></i>Confirm above to merge';
        }
    });

    // Update merge button handler
    mergeBtn.onclick = async () => {
        await performMerge(modal, currentEntity, currentEntityId, duplicateId, projectName);
    };
}

/**
 * Perform the actual merge operation
 */
async function performMerge(modal, currentEntity, currentEntityId, duplicateEntityId, projectName) {
    // Show loading state
    const modalBody = modal.querySelector('.modal-body');
    const originalContent = modalBody.innerHTML;

    modalBody.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="fs-5"><strong>Merging entities...</strong></p>
            <small class="text-muted">This may take a moment. Please do not close this window.</small>
        </div>
    `;

    try {
        const response = await fetch('/api/v1/suggestions/linking/merge-entities', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                entity_id_1: currentEntityId,
                entity_id_2: duplicateEntityId,
                keep_entity_id: currentEntityId,
                reason: 'Duplicate entity merged via UI',
                created_by: 'web-ui'
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        console.log('Merge successful:', result);

        // Hide modal
        bootstrap.Modal.getInstance(modal).hide();

        // Show success notification
        showSuccessToast(`Successfully merged "${getDisplayName(currentEntity)}" entities!`);

        // Refresh the current entity details
        setTimeout(async () => {
            try {
                const updated = await fetch(`/get_person/${currentEntityId}`).then(r => r.json());
                // Trigger a refresh of the UI
                const detailsContainer = document.getElementById('person-details');
                if (detailsContainer) {
                    const { renderPersonDetails } = await import('./ui-person-details.js');
                    await renderPersonDetails(detailsContainer, updated);
                }

                // Remove the merged entity from the sidebar
                const mergedListItem = document.querySelector(`[data-person-id="${duplicateEntityId}"]`);
                if (mergedListItem) {
                    mergedListItem.style.transition = 'opacity 0.3s ease';
                    mergedListItem.style.opacity = '0';
                    setTimeout(() => mergedListItem.remove(), 300);
                }
            } catch (e) {
                console.error('Error refreshing UI after merge:', e);
            }
        }, 500);

    } catch (error) {
        console.error('Error merging entities:', error);
        // Show error in modal
        modalBody.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show" role="alert">
                <h5 class="alert-heading"><strong>Error Merging Entities</strong></h5>
                <p class="mb-2">${error.message}</p>
                <small class="text-muted">Check the browser console for more details.</small>
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
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
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header bg-light border-bottom">
                    <h5 class="modal-title" id="duplicates-modal-label">
                        <i class="fas fa-clone me-2"></i>Duplicate Detection & Merge Tool
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
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
