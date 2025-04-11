// tag_handler.js - Handles tagging relationships between people

import { getDisplayName } from './utils.js';

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
    console.log('Loaded project:', projectName);
    etch(`/get_people?project=${encodeURIComponent(projectName)}`)  // ✅ updated fetch path
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch project data');
            return response.json();
        })
        .then(data => {
            const peopleData = data.people || [];
            console.log('Fetched people data:', peopleData);

            // Store globally if needed
            window.people = peopleData;

            tagState = {
                personId,
                taggedPeople: [],
                allPeople: peopleData,
                searchResults: []
            };

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

            // Filter out self and already tagged
            const availablePeople = peopleData.filter(p =>
                p.id !== personId &&
                !tagState.taggedPeople.some(tp => tp.id === p.id)
            );

            console.log('Available people for tagging:', availablePeople);
            renderTagSearchResults(availablePeople);

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
}

// Set up event listeners for the tag modal
function setupTagModalEvents() {
    // Search input
    const searchInput = document.getElementById('tag-search');
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase().trim();
        
        // Filter available people (exclude current person and already tagged people)
        const searchFilter = person => {
            const searchKeys = (obj, term) => {
                return Object.values(obj).some(value => {
                    if (typeof value === 'string') return value.toLowerCase().includes(term);
                    if (Array.isArray(value)) return value.some(item => searchKeys(item, term));
                    if (typeof value === 'object') return searchKeys(value, term);
                    return false;
                });
            };

            return searchKeys(person.profile || {}, searchTerm) || 
                   getDisplayName(person).toLowerCase().includes(searchTerm);
        };
        
        renderTagSearchResults(availablePeople);
    });
    
    // Save changes button
    const saveBtn = document.getElementById('save-tags-btn');
    saveBtn.addEventListener('click', async function() {
        // Get IDs of tagged people
        const taggedIds = tagState.taggedPeople.map(p => p.id);
        
        try {
            // Send data to server
            const response = await fetch(`/tag_person/${tagState.personId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tagged_ids: taggedIds
                })
            });
            
            if (response.ok) {
                // Update the person in the global people array
                const personIndex = window.people.findIndex(p => p.id === tagState.personId);
                if (personIndex !== -1) {
                    const person = window.people[personIndex];
                    
                    // Initialize the Tagged People section if it doesn't exist
                    if (!person.profile) person.profile = {};
                    if (!person.profile["Tagged People"]) person.profile["Tagged People"] = {};
                    
                    // Update tagged_people field
                    person.profile["Tagged People"]["tagged_people"] = taggedIds;
                    
                    // Re-render the person details
                    const detailsContainer = document.getElementById('person-details');
                    if (detailsContainer) {
                        const personObj = window.people.find(p => p.id === tagState.personId);
                        if (personObj) {
                            // Import here to avoid circular dependency
                            import('./ui-person-details.js').then(module => {
                                module.renderPersonDetails(detailsContainer, personObj);
                            });
                        }
                    }
                }
                
                // Close the modal
                bootstrap.Modal.getInstance(document.getElementById('tag-people-modal')).hide();
            } else {
                console.error('Failed to save tags:', await response.text());
                alert('Failed to save tags. Please try again.');
            }
        } catch (error) {
            console.error('Error saving tags:', error);
            alert('An error occurred while saving tags. Please try again.');
        }
    });
}

// Render the list of tagged people
function renderTaggedPeople(container, person) {
    const section = document.createElement('div');
    section.className = 'mt-4';
    section.innerHTML = `<h5>Tagged People</h5>`;
    
    const list = document.createElement('div');
    person.profile?.["Tagged People"]?.tagged_people?.forEach(taggedId => {
        const taggedPerson = window.people.find(p => p.id === taggedId);
        if (taggedPerson) {
            const div = document.createElement('div');
            div.className = 'd-flex justify-content-between align-items-center mb-2';
            div.innerHTML = `
                <div>
                    <span class="fw-bold">${getDisplayName(taggedPerson)}</span>
                    <small class="text-muted ms-2">ID: ${taggedPerson.id}</small>
                </div>
                <button class="btn btn-sm btn-outline-secondary py-0" 
                        onclick="navigator.clipboard.writeText('${taggedPerson.id}')">
                    Copy ID
                </button>
            `;
            list.appendChild(div);
        }
    });
    
    section.appendChild(list);
    container.appendChild(section);
}



// Render search results
function renderTagSearchResults(results) {
    const container = document.getElementById('tag-search-results');
    container.innerHTML = '';
    
    if (results.length === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'text-muted text-center py-3';
        noResults.textContent = 'No matching people found';
        container.appendChild(noResults);
        return;
    }
    
    results.forEach(person => {
        const item = document.createElement('div');
        item.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        
        const info = document.createElement('div');
        
        const name = document.createElement('div');
        name.className = 'fw-bold';
        name.textContent = getDisplayName(person);
        info.appendChild(name);
        
        const id = document.createElement('small');
        id.className = 'text-muted';
        id.textContent = `ID: ${person.id}`;
        info.appendChild(id);
        
        item.appendChild(info);
        
        item.addEventListener('click', function() {
            // Add to tagged people list
            if (!tagState.taggedPeople.some(p => p.id === person.id)) {
                tagState.taggedPeople.push(person);
                renderTaggedPeople();
                
                // Re-render available people list to exclude newly tagged person
                const searchTerm = document.getElementById('tag-search').value.toLowerCase().trim();
                const updatedAvailablePeople = tagState.allPeople.filter(p => 
                    p.id !== tagState.personId && 
                    !tagState.taggedPeople.some(tp => tp.id === p.id) &&
                    (!searchTerm || getDisplayName(p).toLowerCase().includes(searchTerm))
                );
                renderTagSearchResults(updatedAvailablePeople);
            }
        });
        
        container.appendChild(item);
    });
}