// tag-handler.js - Handles tagging relationships between people with transitive relationships

import { getDisplayName } from './utils.js';
import { filterPeople } from './ui-people-list.js';

// Global state for the tag form
let tagState = {
    personId: null,
    taggedPeople: [],
    allPeople: [],
    searchResults: [],
    transitiveRelationships: []
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
            // Find transitive relationships (people connected through tags)
            const transitiveRelationships = findTransitiveRelationships(peopleData, personId);

            // Update tagState with fetched data
            tagState = {
                personId,
                taggedPeople: [],
                allPeople: peopleData,
                searchResults: [],
                transitiveRelationships
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

            renderTagSearchResults(availablePeople);

            // Show the modal
            const modal = new bootstrap.Modal(document.getElementById('tag-people-modal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error fetching people data:', error);
            alert('Failed to load people data. Please try again.');
        });
}

// Find transitive relationships (people connected through existing tags)
function findTransitiveRelationships(people, personId) {
    const relationships = new Set();
    
    // Get direct tags
    const person = people.find(p => p.id === personId);
    if (person?.profile?.["Tagged People"]?.tagged_people) {
        person.profile["Tagged People"].tagged_people.forEach(id => relationships.add(id));
    }
    
    // Find people who have tagged this person
    people.forEach(p => {
        if (p.profile?.["Tagged People"]?.tagged_people?.includes(personId)) {
            relationships.add(p.id);
        }
    });
    
    return Array.from(relationships);
}

// Create the tag modal HTML structure with relationship indicators
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
                    <div class="alert alert-info mb-3">
                        <i class="fas fa-info-circle me-2"></i>
                        Tagged relationships are bidirectional. When you tag someone, they'll see this connection too.
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Search People</h6>
                            <div class="input-group mb-3">
                                <input type="text" class="form-control" id="tag-search" placeholder="Search people to tag...">
                                <button class="btn btn-outline-secondary" type="button" id="show-related-btn">
                                    <i class="fas fa-project-diagram"></i> Show Related
                                </button>
                            </div>
                            <div id="tag-search-results" class="list-group" style="max-height: 300px; overflow-y: auto;">
                                <!-- Search results will be displayed here -->
                            </div>
                        </div>
                        <div class="col-md-6">
                            <h6>Tagged People <span class="badge bg-primary rounded-pill" id="tagged-count">0</span></h6>
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
    
    // Add event listener for showing related people
    document.getElementById('show-related-btn').addEventListener('click', showRelatedPeople);
}

// Show people related through existing tags
function showRelatedPeople() {
    if (!tagState.transitiveRelationships.length) {
        renderTagSearchResults([]);
        const container = document.getElementById('tag-search-results');
        container.innerHTML = '<div class="text-muted text-center py-3">No existing relationships found</div>';
        return;
    }
    
    const relatedPeople = tagState.allPeople.filter(p => 
        tagState.transitiveRelationships.includes(p.id) &&
        p.id !== tagState.personId &&
        !tagState.taggedPeople.some(tp => tp.id === p.id)
    );
    
    renderTagSearchResults(relatedPeople);
}

// Set up event listeners for the tag modal
function setupTagModalEvents() {
    const searchInput = document.getElementById('tag-search');
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        const filteredPeople = filterPeople(tagState.allPeople, searchTerm).filter(person =>
            !tagState.taggedPeople.some(tp => tp.id === person.id) && 
            person.id !== tagState.personId
        );
        renderTagSearchResults(filteredPeople);
    });
}

// Render the list of tagged people with relationship indicators

function renderTaggedPeopleList() {
    const container = document.getElementById('tagged-people-list');
    const countElement = document.getElementById('tagged-count');
    container.innerHTML = '';

    // Update count
    countElement.textContent = tagState.taggedPeople.length;

    if (tagState.taggedPeople.length === 0) {
        const noTagged = document.createElement('div');
        noTagged.className = 'text-muted text-center py-3';
        noTagged.textContent = 'No people tagged yet';
        container.appendChild(noTagged);
        return;
    }

    tagState.taggedPeople.forEach(taggedPerson => {
        const isRelated = tagState.transitiveRelationships.includes(taggedPerson.id);
        
        const item = document.createElement('div');
        item.className = `list-group-item d-flex justify-content-between align-items-center ${isRelated ? 'bg-light' : ''}`;
        
        const personInfo = document.createElement('div');
        personInfo.className = 'd-flex align-items-center';

        // Add relationship indicator icon
        if (isRelated) {
            const relationIcon = document.createElement('i');
            relationIcon.className = 'fas fa-link text-primary me-2';
            relationIcon.title = 'Already connected through other tags';
            personInfo.appendChild(relationIcon);
        }

        const textContainer = document.createElement('div');
        
        // Display person's name
        const personName = document.createElement('div');
        personName.className = 'fw-bold';
        personName.textContent = getDisplayName(taggedPerson);
        textContainer.appendChild(personName);

        // Display person's ID
        const personId = document.createElement('small');
        personId.className = 'text-muted';
        personId.textContent = `ID: ${taggedPerson.id}`;
        textContainer.appendChild(personId);

        personInfo.appendChild(textContainer);
        item.appendChild(personInfo);

        // Button group
        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'btn-group btn-group-sm';

        // Add copy button
        const copyBtn = document.createElement('button');
        copyBtn.className = 'btn btn-outline-secondary';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
        copyBtn.title = 'Copy details';
        copyBtn.addEventListener('click', () => {
            const copyText = `${getDisplayName(taggedPerson)} (${taggedPerson.id})`;
            navigator.clipboard.writeText(copyText).then(() => {
                copyBtn.innerHTML = '<i class="fas fa-check"></i>';
                setTimeout(() => {
                    copyBtn.innerHTML = '<i class="fas fa-copy"></i>';
                }, 1500);
            });
        });

        // Add remove button
        const removeButton = document.createElement('button');
        removeButton.className = 'btn btn-outline-danger';
        removeButton.innerHTML = '<i class="fas fa-times"></i>';
        removeButton.title = 'Remove tag';
        removeButton.onclick = () => {
            tagState.taggedPeople = tagState.taggedPeople.filter(p => p.id !== taggedPerson.id);
            renderTaggedPeopleList();
        };

        buttonGroup.appendChild(copyBtn);
        buttonGroup.appendChild(removeButton);
        item.appendChild(buttonGroup);
        container.appendChild(item);
    });
}


// Render search results with relationship indicators
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
        const isRelated = tagState.transitiveRelationships.includes(person.id);
        
        const item = document.createElement('div');
        item.className = `list-group-item list-group-item-action d-flex justify-content-between align-items-center ${isRelated ? 'bg-light' : ''}`;
        
        const info = document.createElement('div');
        info.className = 'd-flex align-items-center';

        // Add relationship indicator if exists
        if (isRelated) {
            const relationIcon = document.createElement('i');
            relationIcon.className = 'fas fa-link text-primary me-2';
            relationIcon.title = 'Connected through other tags';
            info.appendChild(relationIcon);
        }

        const textContainer = document.createElement('div');
        textContainer.innerHTML = `
            <div class="fw-bold">${getDisplayName(person)}</div>
            <small class="text-muted">ID: ${person.id}</small>
        `;
        info.appendChild(textContainer);
        item.appendChild(info);

        const addButton = document.createElement('button');
        addButton.className = 'btn btn-sm btn-outline-primary';
        addButton.innerHTML = '<i class="fas fa-plus"></i> Tag';
        addButton.onclick = (e) => {
            e.stopPropagation();
            if (!tagState.taggedPeople.some(p => p.id === person.id)) {
                tagState.taggedPeople.push(person);
                renderTaggedPeopleList();
                renderTagSearchResults(tagState.allPeople.filter(p =>
                    p.id !== tagState.personId &&
                    !tagState.taggedPeople.some(tp => tp.id === p.id)
                ));
            }
        };

        item.appendChild(addButton);
        container.appendChild(item);
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1100'; // Above modals
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
    
    // Auto-remove after dismissal
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// Save tagged people with relationship data
function saveTaggedPeople() {
    const taggedIds = tagState.taggedPeople.map(person => person.id);
    const relationshipData = {
        tagged_ids: taggedIds,
        transitive_relationships: tagState.transitiveRelationships
    };

    // Show loading state
    const saveBtn = document.getElementById('save-tags-btn');
    const originalBtnText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';

    fetch(`/tag_person/${tagState.personId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(relationshipData),
    })
    .then(response => {
        if (!response.ok) {
            // Log additional details about the failed response
            console.error('Failed to save tagged people. Response status:', response.status);
            return response.text().then(text => {
                console.error('Response text:', text);
                throw new Error(`Failed to save tagged people. Server responded with ${response.status}: ${text}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('tag-people-modal'));
            modal.hide();
            
            // Show success toast notification
            showToast('Tags saved successfully!', 'success');
            
            // Optional: Refresh the person details to show updated tags
            if (window.refreshPersonDetails) {
                window.refreshPersonDetails(tagState.personId);
            }
        } else {
            console.error('Server returned success:false with data:', data);
            showToast('Failed to save tags. Please try again.', 'danger');
        }
    })
    .catch(error => {
        console.error('Error saving tagged people:', error);
        showToast('Error saving tags. See console for details.', 'danger');
        
        // For debugging, show more details in the console
        console.debug('Tag State at time of error:', tagState);
        console.debug('Request payload:', relationshipData);
    })
    .finally(() => {
        // Restore button state
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalBtnText;
    });
}