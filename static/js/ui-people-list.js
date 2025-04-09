// ui-people-list.js - Handles displaying and interacting with the list of people

import { getDisplayName, calculateBassetAge } from './utils.js';
import { renderPersonDetails } from './ui-person-details.js';

// Function to render the list of people
function renderPeopleList(people, selectedPersonId = null) {
    const personList = document.getElementById('person-list');
    personList.innerHTML = '';
    
    if (people.length === 0) {
        const noData = document.createElement('li');
        noData.className = 'list-group-item text-center text-muted';
        noData.textContent = 'No people added yet';
        personList.appendChild(noData);
        return;
    }
    
    // Sort people by name
    people.sort((a, b) => {
        const nameA = getDisplayName(a).toLowerCase();
        const nameB = getDisplayName(b).toLowerCase();
        return nameA.localeCompare(nameB);
    });
    
    // Create list items for each person
    people.forEach(person => {
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item person-item d-flex justify-content-between align-items-center';
        if (selectedPersonId && person.id === selectedPersonId) {
            listItem.classList.add('active');
        }
        
        const personInfo = document.createElement('div');
        
        const personName = document.createElement('div');
        personName.className = 'fw-bold';
        personName.textContent = getDisplayName(person);
        personInfo.appendChild(personName);
        
        // Add age info if available
        if (person.created_at) {
            const ageInfo = calculateBassetAge(person.created_at);
            const personAge = document.createElement('small');
            personAge.className = 'text-muted';
            personAge.textContent = ageInfo.shortDisplay;
            personInfo.appendChild(personAge);
        }
        
        listItem.appendChild(personInfo);
        
        // Add click event to select person
        listItem.addEventListener('click', function() {
            // Remove active class from all items
            document.querySelectorAll('.person-item').forEach(item => {
                item.classList.remove('active');
            });

            // Add active class to clicked item
            listItem.classList.add('active');

            // ✅ FIXED: Render into actual container
            const detailsContainer = document.getElementById('person-details');
            renderPersonDetails(detailsContainer, person);

            // On mobile, hide sidebar
            if (window.innerWidth < 768) {
                document.querySelector('.sidebar').classList.add('d-none');
                detailsContainer.classList.remove('d-none');
            }
        });

        
        personList.appendChild(listItem);
    });
}

// Function to filter people list based on search term
function filterPeople(people, searchTerm) {
    if (!searchTerm) return people;

    searchTerm = searchTerm.toLowerCase();

    return people.filter(person => {
        // Check display name
        if (getDisplayName(person).toLowerCase().includes(searchTerm)) {
            return true;
        }

        // Check entire profile for any match
        const profile = person.profile || {};
        for (const sectionId in profile) {
            const section = profile[sectionId];
            for (const fieldId in section) {
                const field = section[fieldId];
                const values = Array.isArray(field) ? field : [field];
                for (const value of values) {
                    if (typeof value === 'string' && value.toLowerCase().includes(searchTerm)) {
                        return true;
                    }
                    if (typeof value === 'object') {
                        for (const key in value) {
                            const subValue = value[key];
                            if (typeof subValue === 'string' && subValue.toLowerCase().includes(searchTerm)) {
                                return true;
                            }
                        }
                    }
                }
            }
        }

        return false;
    });
}

// Function to setup search functionality
function setupSearch(people) {
    const searchInput = document.getElementById('search-input');
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value;
        const filteredPeople = filterPeople(people, searchTerm);
        renderPeopleList(filteredPeople, window.selectedPersonId);
    });
}

export { renderPeopleList, setupSearch };