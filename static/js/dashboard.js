// dashboard.js - Entry point for the application

import { fetchPeople } from './api.js';
import { setupAddButtons, createPersonForm } from './ui-form-handlers.js';
import { renderPeopleList, setupSearch } from './ui-people-list.js';
import { initTagModal } from './tag_handler.js';

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
        initTagModal(); // Initialize the tag modal

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


// Setup form handlers for adding new people
function setupFormHandlers() {
    // Add person button
    const addPersonBtn = document.getElementById('add-person-btn');
    if (addPersonBtn) {
        addPersonBtn.addEventListener('click', function () {
            const container = document.getElementById('person-form-container');
            if (container) {
                container.style.display = 'block';
                document.getElementById('person-details').style.display = 'none';
                createPersonForm(container, window.appConfig, null); // null = Add Mode
            }
        });
    }

    // Cancel add person
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