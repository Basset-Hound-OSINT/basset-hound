// dashboard.js - Entry point for the application

import { fetchPeople } from './api.js';
import { setupAddButtons, createPersonForm, setupEntityTypeModal } from './ui-form-handlers.js';
import { renderPeopleList, setupSearch } from './ui-people-list.js';
import { initTagModal } from './tag-handler.js';

// Global window variables
window.people = [];
window.selectedPersonId = null;

// Initialize the application
async function initApp() {
    try {
        // Always fetch fresh config in case it was updated
        window.appConfig = await fetch('/get_config').then(res => res.json());

        // Fetch people data
        window.people = await fetchPeople();

        // Render people list
        renderPeopleList(window.people, window.selectedPersonId);

        // Setup event listeners
        setupAddButtons();
        setupSearch(window.people);
        setupFormHandlers();
        setupEntityTypeModal();
        initTagModal();

        // Setup download button
        const downloadBtn = document.getElementById('download-project-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', function() {
                window.location.href = '/download_project';
            });
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


// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initApp);