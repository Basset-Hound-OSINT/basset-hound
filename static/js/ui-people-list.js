// ui-people-list.js - Handles displaying and interacting with the list of people

import { getDisplayName, calculateBassetAge } from './utils.js';
import { renderPersonDetails } from './ui-person-details.js';

// Pagination state
let currentPage = 1;
let pageSize = 50;
let totalPages = 1;
let allPeople = [];
let currentSearchTerm = '';
let searchDebounceTimer = null;

// Function to render the list of people (append mode for pagination)
function renderPeopleList(people, selectedPersonId = null, appendMode = false) {
    const personList = document.getElementById('person-list');

    // Clear only if not appending
    if (!appendMode) {
        personList.innerHTML = '';
    }

    if (people.length === 0 && !appendMode) {
        const noData = document.createElement('li');
        noData.className = 'list-group-item text-center text-muted';
        noData.textContent = 'No people added yet';
        personList.appendChild(noData);
        return;
    }

    // Sort people by name
    const sortedPeople = [...people].sort((a, b) => {
        const nameA = getDisplayName(a).toLowerCase();
        const nameB = getDisplayName(b).toLowerCase();
        return nameA.localeCompare(nameB);
    });

    // Create list items for each person
    sortedPeople.forEach(person => {
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

        // Add ID and Account Age
        if (person.created_at) {
            const ageInfo = calculateBassetAge(person.created_at);

            const personId = document.createElement('small');
            personId.className = 'text-muted me-2';
            personId.textContent = `ID: ${person.id}`;

            const personAge = document.createElement('small');
            personAge.className = 'text-muted';
            personAge.textContent = ageInfo.shortDisplay;

            const infoLine = document.createElement('div');
            infoLine.className = 'd-flex gap-2 text-muted small';
            infoLine.appendChild(personId);
            infoLine.appendChild(personAge);

            personInfo.appendChild(infoLine);
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

            // Render into actual container
            const detailsContainer = document.getElementById('person-details');
            renderPersonDetails(detailsContainer, person);

            // Update selected person ID globally
            window.selectedPersonId = person.id;

            // Dispatch entity-selected event for suggestions panel
            const entityEvent = new CustomEvent('entity-selected', {
                detail: { entityId: person.id },
            });
            document.dispatchEvent(entityEvent);

            // On mobile, hide sidebar
            if (window.innerWidth < 768) {
                document.querySelector('.sidebar').classList.add('d-none');
                detailsContainer.classList.remove('d-none');
            }
        });


        personList.appendChild(listItem);
    });
}

// Helper to extract searchable fields from a person
function getSearchableText(person) {
    const parts = [
        getDisplayName(person),
        person.profile?.profile?.email || '',
        person.profile?.profile?.phone || '',
        person.profile?.personal?.email || '',
        person.profile?.personal?.phone || '',
    ];
    return parts.join(' ').toLowerCase();
}

// Function to filter people list based on search term (fast path)
export function filterPeople(people, searchTerm) {
    if (!searchTerm) return people;

    searchTerm = searchTerm.toLowerCase();

    return people.filter(person => {
        // Search only key fields: name, email, phone
        return getSearchableText(person).includes(searchTerm);
    });
}

// Function to perform debounced search
function performSearch(people, searchTerm) {
    currentSearchTerm = searchTerm;
    currentPage = 1;

    const filteredPeople = filterPeople(people, searchTerm);
    const paginated = filteredPeople.slice(0, pageSize);

    renderPeopleList(paginated, window.selectedPersonId, false);
    updateLoadMoreButton(filteredPeople.length);
}

// Function to load more entities (infinite scroll)
function loadMore(people) {
    const filteredPeople = filterPeople(people, currentSearchTerm);
    const start = currentPage * pageSize;
    const end = start + pageSize;
    const nextBatch = filteredPeople.slice(start, end);

    if (nextBatch.length > 0) {
        renderPeopleList(nextBatch, window.selectedPersonId, true);
        currentPage++;
        updateLoadMoreButton(filteredPeople.length);
    }
}

// Function to update load more button visibility
function updateLoadMoreButton(totalFiltered) {
    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
        const currentlyShown = currentPage * pageSize + pageSize;
        loadMoreBtn.style.display = currentlyShown < totalFiltered ? 'block' : 'none';
    }
}

// Function to setup search functionality with debouncing
function setupSearch(people) {
    allPeople = people;
    const searchInput = document.getElementById('search-input');

    // Create load-more button if it doesn't exist
    const peopleContainer = document.querySelector('.sidebar-content');
    if (peopleContainer && !document.getElementById('load-more-btn')) {
        const loadMoreBtn = document.createElement('button');
        loadMoreBtn.id = 'load-more-btn';
        loadMoreBtn.className = 'btn btn-sm btn-outline-secondary w-100 mt-2';
        loadMoreBtn.textContent = 'Load More';
        loadMoreBtn.style.display = 'none';
        loadMoreBtn.addEventListener('click', () => loadMore(allPeople));
        peopleContainer.appendChild(loadMoreBtn);
    }

    // Debounced search
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value;

        // Clear previous timeout
        if (searchDebounceTimer) {
            clearTimeout(searchDebounceTimer);
        }

        // Set new timeout - only search after 300ms of no typing
        searchDebounceTimer = setTimeout(() => {
            performSearch(allPeople, searchTerm);
        }, 300);
    });
}

export { renderPeopleList, setupSearch, loadMore };