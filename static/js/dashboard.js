// dashboard.js - Entry point for the application
// OPTIMIZED: Lazy-load non-critical modules to reduce initial bundle size

import { fetchPeople } from './api.js';
import { setupAddButtons, createPersonForm, setupEntityTypeModal } from './ui-form-handlers.js';
import { renderPeopleList, setupSearch } from './ui-people-list.js';
import { initTagModal } from './tag-handler.js';
import { initExportHandlers } from './export-handler.js';

// Lazy-load non-critical modules
let advancedSearchInitialized = false;
let bulkImportInitialized = false;
let collaborationInitialized = false;

// Global window variables
window.people = [];
window.selectedPersonId = null;
window.collaborationManager = null;

// Lazy-load advanced search module
async function loadAdvancedSearch(projectSafeName) {
    if (advancedSearchInitialized) return;
    try {
        const module = await import('./advanced-search.js');
        module.initAdvancedSearch(projectSafeName);
        advancedSearchInitialized = true;
    } catch (error) {
        console.error('Error loading advanced search:', error);
    }
}

// Lazy-load bulk import module
async function loadBulkImport(projectSafeName) {
    if (bulkImportInitialized) return;
    try {
        const module = await import('./bulk-import.js');
        module.initBulkImport(projectSafeName);
        bulkImportInitialized = true;
    } catch (error) {
        console.error('Error loading bulk import:', error);
    }
}

// Lazy-load collaboration manager (Phase 8)
async function loadCollaboration() {
    if (collaborationInitialized) return;
    try {
        const module = await import('./collaboration-manager.js');
        const projectId = window.currentProjectId;
        const userId = window.userId || 'anonymous';

        if (projectId) {
            window.collaborationManager = new module.default(projectId, userId);
            await window.collaborationManager.initialize();

            // Setup event listeners for collaboration features
            window.collaborationManager.on('presenceUpdated', (presence) => {
                console.log('[Dashboard] User presence updated:', presence);
            });

            window.collaborationManager.on('syncConfirmed', (update) => {
                console.log('[Dashboard] Update synchronized:', update);
            });

            window.collaborationManager.on('activityLogged', (activity) => {
                console.log('[Dashboard] Activity logged:', activity);
            });

            window.collaborationManager.on('conflictDetected', (conflict) => {
                console.log('[Dashboard] Conflict detected:', conflict);
                window.collaborationManager.showMergeConflictDialog(conflict);
            });

            collaborationInitialized = true;
            console.log('[Dashboard] Collaboration manager initialized');
        }
    } catch (error) {
        console.error('Error loading collaboration manager:', error);
    }
}

// Initialize the application (critical path only)
async function initApp() {
    try {
        // Always fetch fresh config in case it was updated
        window.appConfig = await fetch('/get_config').then(res => res.json());

        // Fetch people data
        window.people = await fetchPeople();

        // Render people list (critical)
        renderPeopleList(window.people, window.selectedPersonId);

        // Setup event listeners (critical)
        setupAddButtons();
        setupSearch(window.people);
        setupFormHandlers();
        setupEntityTypeModal();
        initTagModal();

        // Setup metrics dashboard button (Phase 8)
        setupMetricsButton();

        // Setup export handlers (Phase 8)
        const projectSafeName = window.currentProjectSafeName || sessionStorage.getItem('currentProjectSafeName') || '';
        if (projectSafeName) {
            initExportHandlers(projectSafeName);
        }

        // Lazy-load advanced search when search panel is opened
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('focus', async () => {
                const projectSafeName = window.currentProjectSafeName || sessionStorage.getItem('currentProjectSafeName') || '';
                if (projectSafeName) {
                    await loadAdvancedSearch(projectSafeName);
                }
            });
        }

        // Setup event listener for entity selection to update suggestions
        document.addEventListener('entity-selected', (event) => {
            const entityId = event.detail?.entityId;
            if (entityId && window.currentProjectId) {
                // Dynamically import and call updateSuggestionsCount
                import('./suggestions/suggestions-init.js').then(module => {
                    module.updateSuggestionsCount(window.currentProjectId, entityId);
                }).catch(error => {
                    console.error('Error loading suggestions module:', error);
                });
            }
        });

        // Lazy-load bulk import when "Bulk Import" button is clicked
        document.addEventListener('click', async (event) => {
            if (event.target?.id === 'bulk-import-btn' || event.target?.closest('#bulk-import-btn')) {
                const projectSafeName = window.currentProjectSafeName || sessionStorage.getItem('currentProjectSafeName') || '';
                if (projectSafeName) {
                    await loadBulkImport(projectSafeName);
                }
            }
        });

        // Initialize collaboration manager (Phase 8)
        if (window.currentProjectId) {
            await loadCollaboration();
        }
    } catch (error) {
        console.error('Error initializing app:', error);
    }
}


// Setup form handlers for adding new entities
function setupFormHandlers() {
    // Note: Add Entity button now uses modal via data-bs-toggle, handled by setupEntityTypeModal()

    // Cancel add entity
    const cancelAdd = document.getElementById('cancel-add');
    if (cancelAdd) {
        cancelAdd.addEventListener('click', function () {
            document.getElementById('person-form-container').style.display = 'none';
            document.getElementById('person-details').style.display = 'block';
        });
    }

    // Setup validation for any existing forms (usually edit form only)
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
}

// Setup metrics dashboard button (Phase 8)
function setupMetricsButton() {
    const metricsBtn = document.getElementById('metrics-toggle-btn');
    if (!metricsBtn) return;

    metricsBtn.addEventListener('click', async () => {
        // Dynamically import metrics dashboard
        try {
            const { toggleMetricsDashboard } = await import('./metrics-dashboard.js');
            toggleMetricsDashboard(true);

            // Hide person details and show metrics
            const personDetails = document.getElementById('person-details');
            const personForm = document.getElementById('person-form-container');
            if (personDetails) personDetails.style.display = 'none';
            if (personForm) personForm.style.display = 'none';
        } catch (error) {
            console.error('Error loading metrics dashboard:', error);
            alert('Failed to load performance metrics dashboard');
        }
    });
}


// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initApp);