// relationship-manager.js - Handles relationship management UI for entities

import { getDisplayName } from './utils.js';
import { filterPeople } from './ui-people-list.js';

// Relationship types and their categories (comprehensive list from API)
const RELATIONSHIP_TYPES = {
    // Generic
    'RELATED_TO': 'General',
    'KNOWS': 'Social',

    // Professional
    'WORKS_WITH': 'Professional',
    'BUSINESS_PARTNER': 'Professional',
    'REPORTS_TO': 'Professional',
    'MANAGES': 'Professional',
    'COLLEAGUE': 'Professional',
    'CLIENT': 'Professional',
    'EMPLOYER': 'Professional',
    'EMPLOYEE': 'Professional',

    // Family
    'FAMILY': 'Family',
    'MARRIED_TO': 'Family',
    'PARENT_OF': 'Family',
    'CHILD_OF': 'Family',
    'SIBLING_OF': 'Family',
    'SPOUSE': 'Family',

    // Social
    'FRIEND': 'Social',
    'ACQUAINTANCE': 'Social',
    'NEIGHBOR': 'Social',

    // Organizational
    'MEMBER_OF': 'Organizational',
    'AFFILIATED_WITH': 'Organizational',

    // Investigative
    'ASSOCIATED_WITH': 'Investigative',
    'SUSPECTED_ASSOCIATE': 'Investigative',
    'ALIAS_OF': 'Investigative',

    // Communication
    'COMMUNICATES_WITH': 'Communication',
    'CONTACTED': 'Communication'
};

let relationshipState = {
    entityId: null,
    projectName: null,
    relationships: [],
    allEntities: [],
    currentEntity: null
};

export async function initRelationshipManager(entityId, projectName) {
    relationshipState.entityId = entityId;
    relationshipState.projectName = projectName;

    try {
        // Fetch all entities for the project
        const entitiesRes = await fetch('/get_people');
        if (!entitiesRes.ok) {
            throw new Error(`Failed to fetch entities: ${entitiesRes.statusText}`);
        }
        relationshipState.allEntities = await entitiesRes.json();

        // Fetch the current entity
        const currentEntityRes = await fetch(`/get_person/${entityId}`);
        if (!currentEntityRes.ok) {
            throw new Error(`Failed to fetch current entity: ${currentEntityRes.statusText}`);
        }
        relationshipState.currentEntity = await currentEntityRes.json();

        // Fetch relationships from API
        const relRes = await fetch(
            `/api/v1/projects/${projectName}/entities/${entityId}/relationships`
        );

        if (relRes.ok) {
            const relData = await relRes.json();
            relationshipState.relationships = relData.tagged_people || [];
        } else {
            console.warn('Could not fetch relationships from API, using fallback');
            // Fallback: extract from current entity profile
            const taggedSection = relationshipState.currentEntity?.profile?.["Tagged People"] || {};
            relationshipState.relationships = taggedSection.tagged_people || [];
        }

        // Create and inject the relationships tab UI
        createRelationshipsTabs();
        setupRelationshipEventListeners();

    } catch (error) {
        console.error('Error initializing relationship manager:', error);
        showToast('Failed to load relationships', 'danger');
    }
}

function createRelationshipsTabs() {
    const container = document.querySelector('#person-details');
    if (!container) return;

    // Check if tabs already exist
    let tabsContainer = container.querySelector('.relationships-tabs');
    if (tabsContainer) {
        tabsContainer.remove();
    }

    // Create the tab container
    const tabsHtml = `
    <div class="relationships-tabs">
        <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="relationships-tab" data-bs-toggle="tab"
                        data-bs-target="#relationships-panel" type="button" role="tab"
                        aria-controls="relationships-panel" aria-selected="true">
                    <i class="fas fa-link me-2"></i>Relationships
                    <span class="badge bg-secondary ms-2" id="relationship-count">0</span>
                </button>
            </li>
        </ul>
        <div class="tab-content mt-3">
            <div class="tab-pane fade show active" id="relationships-panel" role="tabpanel"
                 aria-labelledby="relationships-tab">
                <div id="relationships-content">
                    <!-- Will be populated -->
                </div>
            </div>
        </div>
    </div>
    `;

    // Insert tabs at the beginning of person-details
    const profileHeader = container.querySelector('.profile-header');
    if (profileHeader) {
        profileHeader.insertAdjacentHTML('afterend', tabsHtml);
    } else {
        container.insertAdjacentHTML('afterbegin', tabsHtml);
    }

    renderRelationshipsList();
}

function renderRelationshipsList() {
    const contentContainer = document.getElementById('relationships-content');
    const countBadge = document.getElementById('relationship-count');

    if (!contentContainer) return;

    // Update count badge
    countBadge.textContent = relationshipState.relationships.length;

    // Clear content
    contentContainer.innerHTML = '';

    if (relationshipState.relationships.length === 0) {
        contentContainer.innerHTML = `
        <div class="text-center py-5">
            <i class="fas fa-link fa-3x text-muted mb-3"></i>
            <p class="text-muted">No relationships yet</p>
            <button class="btn btn-primary btn-sm" id="add-relationship-btn">
                <i class="fas fa-plus me-2"></i>Add Relationship
            </button>
        </div>
        `;
        setupRelationshipEventListeners();
        return;
    }

    // Create table for relationships
    const table = document.createElement('table');
    table.className = 'table table-hover';
    table.innerHTML = `
    <thead>
        <tr>
            <th>Entity</th>
            <th>Relationship Type</th>
            <th>Properties</th>
            <th style="width: 120px;">Actions</th>
        </tr>
    </thead>
    <tbody id="relationships-table-body">
    </tbody>
    `;

    const tbody = table.querySelector('tbody');

    relationshipState.relationships.forEach((relatedId, idx) => {
        const relatedEntity = relationshipState.allEntities.find(e => e.id === relatedId);
        const relType = relationshipState.currentEntity?.profile?.["Tagged People"]?.relationship_types?.[relatedId];
        const relProps = relationshipState.currentEntity?.profile?.["Tagged People"]?.relationship_properties?.[relatedId] || {};

        const row = document.createElement('tr');
        row.className = 'relationship-row';
        row.dataset.relationshipId = relatedId;

        // Entity name column
        const nameCell = document.createElement('td');
        if (relatedEntity) {
            nameCell.innerHTML = `
            <div class="fw-bold">${getDisplayName(relatedEntity)}</div>
            <small class="text-muted">ID: ${relatedId}</small>
            `;
        } else {
            nameCell.innerHTML = `
            <div class="text-danger">Unknown Entity</div>
            <small class="text-muted">ID: ${relatedId}</small>
            `;
        }
        row.appendChild(nameCell);

        // Relationship type column
        const typeCell = document.createElement('td');
        const typeBadgeClass = getRelationshipTypeBadgeClass(relType);
        typeCell.innerHTML = `<span class="badge ${typeBadgeClass}">${relType || 'RELATED_TO'}</span>`;
        row.appendChild(typeCell);

        // Properties column
        const propsCell = document.createElement('td');
        const propsText = formatRelationshipProperties(relProps);
        propsCell.innerHTML = propsText ? `<small>${propsText}</small>` : '<small class="text-muted">-</small>';
        row.appendChild(propsCell);

        // Actions column
        const actionsCell = document.createElement('td');
        actionsCell.innerHTML = `
        <div class="btn-group btn-group-sm" role="group">
            <button class="btn btn-outline-secondary edit-relationship-btn" title="Edit">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-outline-danger delete-relationship-btn" title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        </div>
        `;

        actionsCell.querySelector('.edit-relationship-btn').addEventListener('click', () => {
            openRelationshipModal(relatedId);
        });

        actionsCell.querySelector('.delete-relationship-btn').addEventListener('click', () => {
            if (confirm(`Remove relationship with ${relatedEntity ? getDisplayName(relatedEntity) : 'this entity'}?`)) {
                deleteRelationship(relatedId);
            }
        });

        row.appendChild(actionsCell);
        tbody.appendChild(row);
    });

    contentContainer.appendChild(table);

    // Add button below table
    const addBtn = document.createElement('button');
    addBtn.id = 'add-relationship-btn';
    addBtn.className = 'btn btn-primary mt-3';
    addBtn.innerHTML = '<i class="fas fa-plus me-2"></i>Add Relationship';
    contentContainer.appendChild(addBtn);

    setupRelationshipEventListeners();
}

function setupRelationshipEventListeners() {
    const addBtn = document.getElementById('add-relationship-btn');
    if (addBtn) {
        // Remove old listeners to prevent duplicates
        const newBtn = addBtn.cloneNode(true);
        addBtn.parentNode?.replaceChild(newBtn, addBtn);

        // Add new listener
        const updatedBtn = document.getElementById('add-relationship-btn');
        if (updatedBtn) {
            updatedBtn.addEventListener('click', () => openRelationshipModal());
        }
    }
}

function openRelationshipModal(relationshipId = null) {
    const projectName = relationshipState.projectName;
    const currentEntityId = relationshipState.entityId;

    // Remove existing modal if present and clean up
    let modal = document.getElementById('relationship-modal');
    if (modal) {
        try {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
                bsModal.dispose();
            }
        } catch (e) {
            // Modal instance doesn't exist, just remove the element
        }
        modal.remove();
    }

    const modalHtml = `
    <div class="modal fade" id="relationship-modal" tabindex="-1" aria-labelledby="relationship-modal-label" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="relationship-modal-label">
                        <i class="fas fa-link me-2"></i>${relationshipId ? 'Edit' : 'Add'} Relationship
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="relationship-form">
                        <!-- Target entity selection -->
                        <div class="mb-3">
                            <label for="target-entity-select" class="form-label">
                                <i class="fas fa-user me-2"></i>Target Entity <span class="text-danger">*</span>
                            </label>
                            <div class="input-group">
                                <input type="text" class="form-control" id="target-entity-search"
                                       placeholder="Search entities...">
                                <button class="btn btn-outline-secondary" type="button" id="clear-entity-btn">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                            <div id="entity-search-results" class="list-group mt-2" style="max-height: 250px; overflow-y: auto; display: none;">
                            </div>
                            <div id="selected-entity-display" class="alert alert-info mt-2" style="display: none;">
                                Selected: <strong id="selected-entity-name"></strong>
                            </div>
                            <input type="hidden" id="target-entity-id">
                        </div>

                        <!-- Relationship type -->
                        <div class="mb-3">
                            <label for="relationship-type-select" class="form-label">
                                <i class="fas fa-link me-2"></i>Relationship Type <span class="text-danger">*</span>
                            </label>
                            <select class="form-select" id="relationship-type-select">
                                <option value="">-- Select a type --</option>
                                ${Object.entries(RELATIONSHIP_TYPES).map(([type, category]) =>
                                    `<option value="${type}">${type} (${category})</option>`
                                ).join('')}
                            </select>
                        </div>

                        <!-- Optional properties -->
                        <div class="row">
                            <!-- Since date -->
                            <div class="col-md-6 mb-3">
                                <label for="relationship-since" class="form-label">
                                    <i class="fas fa-calendar me-2"></i>Since (Date)
                                </label>
                                <input type="date" class="form-control" id="relationship-since">
                            </div>

                            <!-- Confidence slider -->
                            <div class="col-md-6 mb-3">
                                <label for="relationship-confidence" class="form-label">
                                    <i class="fas fa-chart-pie me-2"></i>Confidence
                                </label>
                                <div class="d-flex gap-2 align-items-center">
                                    <input type="range" class="form-range" id="relationship-confidence"
                                           min="0" max="100" value="50">
                                    <span id="confidence-value" class="badge bg-secondary">50%</span>
                                </div>
                            </div>
                        </div>

                        <!-- Notes -->
                        <div class="mb-3">
                            <label for="relationship-notes" class="form-label">
                                <i class="fas fa-sticky-note me-2"></i>Notes
                            </label>
                            <textarea class="form-control" id="relationship-notes" rows="3"
                                      placeholder="Add any notes about this relationship..."></textarea>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="save-relationship-btn">
                        <i class="fas fa-save me-2"></i>Save Relationship
                    </button>
                </div>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    modal = document.getElementById('relationship-modal');

    // Setup event listeners for modal
    const targetSearchInput = document.getElementById('target-entity-search');
    const entitySearchResults = document.getElementById('entity-search-results');
    const selectedEntityDisplay = document.getElementById('selected-entity-display');
    const selectedEntityName = document.getElementById('selected-entity-name');
    const targetEntityIdField = document.getElementById('target-entity-id');
    const clearBtn = document.getElementById('clear-entity-btn');
    const confidenceSlider = document.getElementById('relationship-confidence');
    const confidenceValue = document.getElementById('confidence-value');
    const saveBtn = document.getElementById('save-relationship-btn');

    // Update confidence display
    confidenceSlider.addEventListener('input', (e) => {
        confidenceValue.textContent = e.target.value + '%';
    });

    // Entity search with debouncing
    let searchTimeout;
    targetSearchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const searchTerm = e.target.value.toLowerCase().trim();

        if (!searchTerm) {
            entitySearchResults.style.display = 'none';
            return;
        }

        searchTimeout = setTimeout(() => {
            const filtered = relationshipState.allEntities.filter(entity => {
                // Skip self-reference
                if (entity.id === currentEntityId) return false;

                // Skip already tagged entities
                if (relationshipState.relationships.includes(entity.id)) return false;

                const displayName = getDisplayName(entity).toLowerCase();
                const idMatch = entity.id.toLowerCase().includes(searchTerm);
                const nameMatch = displayName.includes(searchTerm);
                return nameMatch || idMatch;
            }).slice(0, 15); // Increased from 10 to 15 results

            if (filtered.length === 0) {
                entitySearchResults.innerHTML = '<div class="list-group-item text-muted text-center py-3"><i class="fas fa-search me-2"></i>No entities found</div>';
                entitySearchResults.style.display = 'block';
                return;
            }

            entitySearchResults.innerHTML = filtered.map(entity => {
                const displayName = getDisplayName(entity);
                const displayNameLower = displayName.toLowerCase();
                const highlightedName = displayName.replace(
                    new RegExp(`(${searchTerm})`, 'gi'),
                    '<strong>$1</strong>'
                );
                return `
                <button type="button" class="list-group-item list-group-item-action" data-entity-id="${entity.id}">
                    <div class="fw-bold">${highlightedName}</div>
                    <small class="text-muted">ID: ${entity.id}</small>
                </button>
                `;
            }).join('');
            entitySearchResults.style.display = 'block';

            // Add click handlers
            entitySearchResults.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const entityId = btn.dataset.entityId;
                    const entity = relationshipState.allEntities.find(e => e.id === entityId);

                    if (entity) {
                        targetEntityIdField.value = entityId;
                        selectedEntityName.textContent = getDisplayName(entity);
                        selectedEntityDisplay.style.display = 'block';
                        entitySearchResults.style.display = 'none';
                        targetSearchInput.value = '';
                    }
                });
            });
        }, 300); // Debounce for 300ms
    });

    clearBtn.addEventListener('click', () => {
        targetEntityIdField.value = '';
        selectedEntityDisplay.style.display = 'none';
        targetSearchInput.value = '';
        entitySearchResults.style.display = 'none';
    });

    // If editing existing relationship, populate form
    if (relationshipId) {
        const relatedEntity = relationshipState.allEntities.find(e => e.id === relationshipId);
        const relType = relationshipState.currentEntity?.profile?.["Tagged People"]?.relationship_types?.[relationshipId];
        const relProps = relationshipState.currentEntity?.profile?.["Tagged People"]?.relationship_properties?.[relationshipId] || {};

        if (relatedEntity) {
            targetEntityIdField.value = relationshipId;
            selectedEntityName.textContent = getDisplayName(relatedEntity);
            selectedEntityDisplay.style.display = 'block';
        }

        if (relType) {
            document.getElementById('relationship-type-select').value = relType;
        }

        if (relProps.since) {
            document.getElementById('relationship-since').value = relProps.since;
        }

        if (relProps.confidence) {
            const confValue = parseInt(relProps.confidence) || 50;
            confidenceSlider.value = confValue;
            confidenceValue.textContent = confValue + '%';
        }

        if (relProps.notes) {
            document.getElementById('relationship-notes').value = relProps.notes;
        }
    }

    // Save button handler
    saveBtn.addEventListener('click', saveRelationship);

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

async function saveRelationship() {
    const projectName = relationshipState.projectName;
    const currentEntityId = relationshipState.entityId;
    const targetEntityId = document.getElementById('target-entity-id').value;
    const relationshipType = document.getElementById('relationship-type-select').value;
    const since = document.getElementById('relationship-since').value;
    const confidence = document.getElementById('relationship-confidence').value;
    const notes = document.getElementById('relationship-notes').value;

    // Validation
    if (!targetEntityId || targetEntityId.trim() === '') {
        showToast('Please select a target entity', 'warning');
        return;
    }

    if (!relationshipType || relationshipType.trim() === '') {
        showToast('Please select a relationship type', 'warning');
        return;
    }

    // Prevent self-reference
    if (targetEntityId === currentEntityId) {
        showToast('Cannot create a relationship to the same entity', 'warning');
        return;
    }

    try {
        const saveBtn = document.getElementById('save-relationship-btn');
        const originalText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

        // Build the update payload
        const currentProfile = relationshipState.currentEntity?.profile?.["Tagged People"] || {};
        const currentTaggedIds = currentProfile.tagged_people || [];
        const currentRelTypes = currentProfile.relationship_types || {};
        const currentRelProps = currentProfile.relationship_properties || {};

        // Add or update the relationship
        if (!currentTaggedIds.includes(targetEntityId)) {
            currentTaggedIds.push(targetEntityId);
        }

        currentRelTypes[targetEntityId] = relationshipType;

        // Build properties object
        const properties = {};
        if (since) properties.since = since;
        if (confidence && parseInt(confidence) > 0) {
            properties.confidence = parseInt(confidence);
        }
        if (notes && notes.trim()) {
            properties.notes = notes.trim();
        }

        // Only set properties if we have something
        if (Object.keys(properties).length > 0) {
            currentRelProps[targetEntityId] = properties;
        } else {
            // Remove if no properties exist
            delete currentRelProps[targetEntityId];
        }

        // Send update to API
        const updateRes = await fetch(
            `/api/v1/projects/${projectName}/entities/${currentEntityId}/relationships`,
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tagged_ids: currentTaggedIds,
                    transitive_relationships: currentProfile.transitive_relationships || [],
                    relationship_types: currentRelTypes,
                    relationship_properties: currentRelProps
                })
            }
        );

        if (!updateRes.ok) {
            const errorData = await updateRes.json().catch(() => ({}));
            throw new Error(errorData.detail || `Failed to save relationship: ${updateRes.statusText}`);
        }

        showToast('Relationship saved successfully', 'success');

        // Close modal and refresh
        const modal = document.getElementById('relationship-modal');
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }

        // Refresh relationships
        setTimeout(() => {
            initRelationshipManager(currentEntityId, projectName);
        }, 300); // Small delay to allow modal to close

    } catch (error) {
        console.error('Error saving relationship:', error);
        showToast('Error saving relationship', 'danger');
    } finally {
        const saveBtn = document.getElementById('save-relationship-btn');
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fas fa-save me-2"></i>Save Relationship';
        }
    }
}

async function deleteRelationship(targetEntityId) {
    const projectName = relationshipState.projectName;
    const currentEntityId = relationshipState.entityId;

    try {
        const currentProfile = relationshipState.currentEntity?.profile?.["Tagged People"] || {};
        const currentTaggedIds = (currentProfile.tagged_people || []).filter(id => id !== targetEntityId);
        const currentRelTypes = { ...currentProfile.relationship_types || {} };
        const currentRelProps = { ...currentProfile.relationship_properties || {} };

        delete currentRelTypes[targetEntityId];
        delete currentRelProps[targetEntityId];

        // Send update to API
        const updateRes = await fetch(
            `/api/v1/projects/${projectName}/entities/${currentEntityId}/relationships`,
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tagged_ids: currentTaggedIds,
                    transitive_relationships: currentProfile.transitive_relationships || [],
                    relationship_types: currentRelTypes,
                    relationship_properties: currentRelProps
                })
            }
        );

        if (!updateRes.ok) {
            const errorData = await updateRes.json().catch(() => ({}));
            throw new Error(errorData.detail || `Failed to delete relationship: ${updateRes.statusText}`);
        }

        showToast('Relationship deleted successfully', 'success');

        // Refresh relationships
        setTimeout(() => {
            initRelationshipManager(currentEntityId, projectName);
        }, 300);

    } catch (error) {
        console.error('Error deleting relationship:', error);
        showToast('Error deleting relationship', 'danger');
    }
}

function getRelationshipTypeBadgeClass(relType) {
    const typeMap = {
        // Generic
        'RELATED_TO': 'bg-secondary',
        'KNOWS': 'bg-info',

        // Professional
        'WORKS_WITH': 'bg-primary',
        'BUSINESS_PARTNER': 'bg-primary',
        'REPORTS_TO': 'bg-primary',
        'MANAGES': 'bg-primary',
        'COLLEAGUE': 'bg-primary',
        'CLIENT': 'bg-primary',
        'EMPLOYER': 'bg-primary',
        'EMPLOYEE': 'bg-primary',

        // Family
        'FAMILY': 'bg-success',
        'MARRIED_TO': 'bg-success',
        'PARENT_OF': 'bg-success',
        'CHILD_OF': 'bg-success',
        'SIBLING_OF': 'bg-success',
        'SPOUSE': 'bg-success',

        // Social
        'FRIEND': 'bg-info',
        'ACQUAINTANCE': 'bg-info',
        'NEIGHBOR': 'bg-info',

        // Organizational
        'MEMBER_OF': 'bg-success',
        'AFFILIATED_WITH': 'bg-success',

        // Investigative
        'ASSOCIATED_WITH': 'bg-warning',
        'SUSPECTED_ASSOCIATE': 'bg-warning',
        'ALIAS_OF': 'bg-danger',

        // Communication
        'COMMUNICATES_WITH': 'bg-secondary',
        'CONTACTED': 'bg-secondary'
    };
    return typeMap[relType] || 'bg-secondary';
}

function formatRelationshipProperties(props) {
    if (!props || typeof props !== 'object') return '';

    const parts = [];
    if (props.since) {
        // Handle both date strings and full ISO timestamps
        const dateStr = props.since.split('T')[0]; // Extract just the date part
        parts.push(`Since: ${dateStr}`);
    }
    if (props.confidence) {
        const confValue = typeof props.confidence === 'number'
            ? props.confidence
            : parseInt(props.confidence);
        parts.push(`Conf: ${confValue}%`);
    }
    if (props.source) parts.push(`Source: ${props.source}`);
    if (props.notes) {
        const notePreview = props.notes.substring(0, 25);
        const truncated = props.notes.length > 25 ? '...' : '';
        parts.push(`Notes: ${notePreview}${truncated}`);
    }
    if (props.timestamp) {
        // Only show timestamp if it's different from 'since'
        if (props.timestamp !== props.since) {
            const dateStr = props.timestamp.split('T')[0];
            parts.push(`Updated: ${dateStr}`);
        }
    }

    return parts.join(' • ');
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1100';
    document.body.appendChild(container);
    return container;
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toastId = 'toast-' + Date.now();

    const toastHtml = `
    <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();

    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}
