// tag-handler.js - Handles tagging relationships between people

import { getDisplayName } from './utils.js';
import { filterPeople } from './ui-people-list.js';

// Global state for the tag form
let tagState = {
    personId: null,
    taggedPeople: [],
    allPeople: [],
    searchResults: []
};

// Initialize the tag modal
export function initTagModal() {
    // Create the modal if it doesn't exist
    if (!document.getElementById('tag-people-modal')) {
        createTagModal();
    }
    
    // Set up event listeners
    setupTagModalEvents();
}

// Open the tag modal for a specific person
export function openTagModal(personId) {
    console.log('Opening tag modal for person:', personId);

    // Fetch all people data
    fetch('/get_people')
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch people data');
            return response.json();
        })
        .then(peopleData => {
            console.log('Fetched people data:', peopleData);

            // Update tagState with fetched data
            tagState = {
                personId,
                taggedPeople: [],
                allPeople: peopleData,
                searchResults: []
            };

            // Find the current person
            const person = peopleData.find(p => p.id === personId);
            let taggedIds = [];

            if (person?.profile?.["Tagged People"]?.tagged_people) {
                taggedIds = person.profile["Tagged People"].tagged_people;
            }

            // Map tagged IDs to person objects
            tagState.taggedPeople = taggedIds.map(id =>
                peopleData.find(p => p.id === id)
            ).filter(Boolean);

            const personName = person ? getDisplayName(person) : 'Unknown Person';
            document.getElementById('tag-modal-person-name').textContent = personName;

            renderTaggedPeopleList();
            document.getElementById('tag-search').value = '';

            // Filter out self and already tagged people
            const availablePeople = peopleData.filter(p =>
                p.id !== personId && // Exclude the current person
                !tagState.taggedPeople.some(tp => tp.id === p.id) // Exclude already tagged people
            );

            console.log('Available people for tagging:', availablePeople);
            renderTagSearchResults(availablePeople);

            // Debugging logs (moved inside the .then() block)
            console.log('All people:', peopleData);
            console.log('Current person:', person);
            console.log('Tagged IDs:', taggedIds);
            console.log('Tagged people:', tagState.taggedPeople);
            console.log('Available people for tagging:', availablePeople);

            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('tag-people-modal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error fetching people data:', error);
            alert('Failed to load people data. Please try again.');
        });
}

// Create the tag modal HTML structure
function createTagModal() {
    const modalHtml = `
    <div class="modal fade" id="tag-people-modal" tabindex="-1" aria-labelledby="tag-people-modal-label" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="tag-people-modal-label">Tag People for <span id="tag-modal-person-name"></span></h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Search People</h6>
                            <div class="input-group mb-3">
                                <input type="text" class="form-control" id="tag-search" placeholder="Search people to tag...">
                            </div>
                            <div id="tag-search-results" class="list-group" style="max-height: 300px; overflow-y: auto;">
                                <!-- Search results will be displayed here -->
                            </div>
                        </div>
                        <div class="col-md-6">
                            <h6>Tagged People</h6>
                            <div id="tagged-people-list" class="list-group" style="max-height: 300px; overflow-y: auto;">
                                <!-- Tagged people will be displayed here -->
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="save-tags-btn">Save Changes</button>
                </div>
            </div>
        </div>
    </div>
    `;

    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHtml;
    document.body.appendChild(modalContainer);

    // Add the event listener for the "Save Changes" button
    document.getElementById('save-tags-btn').addEventListener('click', saveTaggedPeople);
}

// Set up event listeners for the tag modal
function setupTagModalEvents() {
    const searchInput = document.getElementById('tag-search');
    searchInput.addEventListener('input', function () {
        const searchTerm = this.value.toLowerCase().trim();
        const filteredPeople = filterPeople(tagState.allPeople, searchTerm).filter(person =>
            !tagState.taggedPeople.some(tp => tp.id === person.id) && person.id !== tagState.personId
        );
        renderTagSearchResults(filteredPeople);
    });
}

// Render the list of tagged people
function renderTaggedPeopleList() {
    const container = document.getElementById('tagged-people-list');
    container.innerHTML = '';

    if (tagState.taggedPeople.length === 0) {
        const noTagged = document.createElement('div');
        noTagged.className = 'text-muted text-center py-3';
        noTagged.textContent = 'No people tagged yet';
        container.appendChild(noTagged);
        return;
    }

    const taggedList = document.createElement('ul');
    taggedList.className = 'list-group';

    tagState.taggedPeople.forEach(taggedPerson => {
        const item = document.createElement('li');
        item.className = 'list-group-item d-flex justify-content-between align-items-center';

        const personInfo = document.createElement('div');

        // Display person's name
        const personName = document.createElement('div');
        personName.className = 'fw-bold';
        personName.textContent = getDisplayName(taggedPerson);
        personInfo.appendChild(personName);

        // Display person's ID
        const personId = document.createElement('small');
        personId.className = 'text-muted';
        personId.textContent = `ID: ${taggedPerson.id}`;
        personInfo.appendChild(personId);

        item.appendChild(personInfo);

        // Add copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-sm btn-outline-secondary';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy';
        copyBtn.addEventListener('click', () => {
            const copyText = `${getDisplayName(taggedPerson)} (${taggedPerson.id})`;
            navigator.clipboard.writeText(copyText).then(() => {
                copyBtn.innerHTML = '<i class="fas fa-check"></i> Copied';
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy';
                }, 1500);
            });
        });

        item.appendChild(copyBtn);

        // Add remove button
        const removeButton = document.createElement('button');
        removeButton.className = 'btn btn-sm btn-outline-danger';
        removeButton.textContent = 'Remove';
        removeButton.onclick = () => {
            tagState.taggedPeople = tagState.taggedPeople.filter(p => p.id !== taggedPerson.id);
            renderTaggedPeopleList();
        };

        item.appendChild(removeButton);
        taggedList.appendChild(item);
    });

    container.appendChild(taggedList);
}

// Render search results
function renderTagSearchResults(results) {
    const container = document.getElementById('tag-search-results');
    container.innerHTML = '';

    if (results.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'text-muted text-center py-3';
        noResults.textContent = 'No people available for tagging';
        container.appendChild(noResults);
        return;
    }

    results.forEach(person => {
        const item = document.createElement('div');
        item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';

        const info = document.createElement('div');
        info.innerHTML = `
            <div class="fw-bold">${getDisplayName(person)}</div>
            <small class="text-muted">ID: ${person.id}</small>
        `;

        item.appendChild(info);

        item.addEventListener('click', function () {
            if (!tagState.taggedPeople.some(p => p.id === person.id)) {
                tagState.taggedPeople.push(person);
                renderTaggedPeopleList();
                renderTagSearchResults(tagState.allPeople.filter(p =>
                    p.id !== tagState.personId &&
                    !tagState.taggedPeople.some(tp => tp.id === p.id)
                ));
            }
        });

        container.appendChild(item);
    });
}

function saveTaggedPeople() {
    const taggedIds = tagState.taggedPeople.map(person => person.id);

    fetch(`/tag_person/${tagState.personId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ tagged_ids: taggedIds }),
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to save tagged people');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                //alert('Tagged people saved successfully!');
                const modal = bootstrap.Modal.getInstance(document.getElementById('tag-people-modal'));
                modal.hide();
            } else {
                alert('Failed to save tagged people. Please try again.');
            }
        })
        .catch(error => {
            console.error('Error saving tagged people:', error);
            alert('An error occurred while saving tagged people.');
        });
}