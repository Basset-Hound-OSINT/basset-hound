// main.js - Entry point for the application

import { fetchPeople } from './api.js';
import { setupAddButtons, collectFormData } from './ui-form-handlers.js';
import { renderPeopleList, setupSearch } from './ui-people-list.js';
import { setupPersonDetailsListeners } from './ui-person-details.js';

// Global window variables
window.people = [];
window.selectedPersonId = null;

// Initialize the application
async function initApp() {
    // Fetch people data
    window.people = await fetchPeople();
    
    // Render people list
    renderPeopleList(window.people, window.selectedPersonId);
    
    // Setup event listeners
    setupAddButtons();
    setupPersonDetailsListeners();
    setupSearch(window.people);
    setupFormHandlers();
}

// Setup form handlers for adding new people
function setupFormHandlers() {
    // Add person button
    document.getElementById('add-person-btn').addEventListener('click', function() {
        document.getElementById('add-person-form').style.display = 'block';
        document.getElementById('person-details').style.display = 'none';
    });
    
    // Cancel add person
    document.getElementById('cancel-add').addEventListener('click', function() {
        document.getElementById('add-person-form').style.display = 'none';
        document.getElementById('person-details').style.display = 'block';
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initApp);