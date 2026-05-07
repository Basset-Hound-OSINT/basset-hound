// advanced-search.js - Advanced search interface with field-specific filters and boolean operators

import { getDisplayName } from './utils.js';
import { renderPeopleList } from './ui-people-list.js';

/**
 * Advanced search filter state object
 */
class AdvancedSearchState {
    constructor() {
        this.name = '';
        this.email = '';
        this.phone = '';
        this.username = '';
        this.entityTypes = [];
        this.tags = [];
        this.booleanMode = 'AND'; // 'AND' or 'OR'
        this.createdAfter = '';
        this.createdBefore = '';
        this.customQuery = ''; // For advanced boolean syntax
    }

    /**
     * Save state to sessionStorage
     */
    save() {
        sessionStorage.setItem('advancedSearchState', JSON.stringify(this));
    }

    /**
     * Load state from sessionStorage
     */
    static load() {
        const saved = sessionStorage.getItem('advancedSearchState');
        if (saved) {
            const state = new AdvancedSearchState();
            const data = JSON.parse(saved);
            Object.assign(state, data);
            return state;
        }
        return new AdvancedSearchState();
    }

    /**
     * Clear all filters
     */
    clear() {
        this.name = '';
        this.email = '';
        this.phone = '';
        this.username = '';
        this.entityTypes = [];
        this.tags = [];
        this.booleanMode = 'AND';
        this.createdAfter = '';
        this.createdBefore = '';
        this.customQuery = '';
        this.save();
    }

    /**
     * Check if any filters are active
     */
    hasActiveFilters() {
        return this.name || this.email || this.phone || this.username ||
               this.entityTypes.length > 0 || this.tags.length > 0 ||
               this.createdAfter || this.createdBefore || this.customQuery;
    }
}

/**
 * Initialize advanced search UI
 * @param {string} projectName - The project safe name for API calls
 */
export function initAdvancedSearch(projectName) {
    // Load persisted state
    const state = AdvancedSearchState.load();

    // Setup toggle button
    setupToggleButton();

    // Setup advanced search panel
    setupAdvancedSearchPanel(state, projectName);

    // Setup search input listener
    setupBasicSearchInput(projectName, state);
}

/**
 * Setup the toggle button between Basic and Advanced search
 */
function setupToggleButton() {
    // Find the search input specifically (it has id="search-input")
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;

    const searchContainer = searchInput.parentElement;

    // Create toggle button wrapper
    const toggleWrapper = document.createElement('div');
    toggleWrapper.className = 'd-flex gap-2 mt-2';
    toggleWrapper.innerHTML = `
        <button type="button" id="search-mode-toggle" class="btn btn-sm btn-outline-secondary" title="Toggle between basic and advanced search">
            <i class="fas fa-sliders-h"></i> Advanced
        </button>
        <small class="text-muted align-self-center" id="search-mode-indicator">Basic Mode</small>
    `;

    searchContainer.appendChild(toggleWrapper);

    // Setup toggle click handler
    const toggleBtn = document.getElementById('search-mode-toggle');
    toggleBtn.addEventListener('click', () => {
        const panel = document.getElementById('advanced-search-panel');
        if (panel && panel.style.display === 'none') {
            panel.style.display = 'block';
            toggleBtn.classList.add('active');
            document.getElementById('search-mode-indicator').textContent = 'Advanced Mode';
            document.getElementById('search-input').style.display = 'none';
        } else if (panel) {
            panel.style.display = 'none';
            toggleBtn.classList.remove('active');
            document.getElementById('search-mode-indicator').textContent = 'Basic Mode';
            document.getElementById('search-input').style.display = 'block';
        }
    });
}

/**
 * Setup the advanced search panel
 */
function setupAdvancedSearchPanel(state, projectName) {
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;

    const searchContainer = searchInput.parentElement;

    // Create panel
    const panel = document.createElement('div');
    panel.id = 'advanced-search-panel';
    panel.className = 'card mt-3';
    panel.style.display = 'none';

    panel.innerHTML = `
        <div class="card-header bg-light">
            <h6 class="mb-0">Advanced Search</h6>
        </div>
        <div class="card-body p-3">
            <!-- Field-specific search -->
            <div class="mb-3">
                <label class="form-label small fw-bold">Field Filters</label>
                <div class="input-group input-group-sm mb-2">
                    <span class="input-group-text" style="width: 60px;">Name</span>
                    <input type="text" id="filter-name" class="form-control" placeholder="First or last name">
                </div>
                <div class="input-group input-group-sm mb-2">
                    <span class="input-group-text" style="width: 60px;">Email</span>
                    <input type="email" id="filter-email" class="form-control" placeholder="email@domain.com">
                </div>
                <div class="input-group input-group-sm mb-2">
                    <span class="input-group-text" style="width: 60px;">Phone</span>
                    <input type="text" id="filter-phone" class="form-control" placeholder="+1-555-0000">
                </div>
                <div class="input-group input-group-sm">
                    <span class="input-group-text" style="width: 60px;">Username</span>
                    <input type="text" id="filter-username" class="form-control" placeholder="@username">
                </div>
            </div>

            <hr class="my-3">

            <!-- Entity type filter -->
            <div class="mb-3">
                <label class="form-label small fw-bold">Entity Types</label>
                <select id="filter-entity-types" class="form-select form-select-sm" multiple size="4">
                    <option value="person">Person</option>
                    <option value="organization">Organization</option>
                    <option value="government">Government</option>
                    <option value="group">Group</option>
                    <option value="sock_puppet">Sock Puppet</option>
                    <option value="location">Location</option>
                    <option value="unknown">Unknown</option>
                </select>
                <small class="text-muted d-block mt-1">Hold Ctrl to select multiple</small>
            </div>

            <hr class="my-3">

            <!-- Boolean mode -->
            <div class="mb-3">
                <label class="form-label small fw-bold">Boolean Mode</label>
                <div class="btn-group btn-group-sm w-100" role="group">
                    <input type="radio" class="btn-check" name="boolean-mode" id="bool-and" value="AND" checked>
                    <label class="btn btn-outline-secondary" for="bool-and">AND</label>
                    <input type="radio" class="btn-check" name="boolean-mode" id="bool-or" value="OR">
                    <label class="btn btn-outline-secondary" for="bool-or">OR</label>
                </div>
                <small class="text-muted d-block mt-1">AND: all filters must match | OR: any filter can match</small>
            </div>

            <hr class="my-3">

            <!-- Date range -->
            <div class="mb-3">
                <label class="form-label small fw-bold">Created Date Range</label>
                <div class="input-group input-group-sm mb-2">
                    <span class="input-group-text">After</span>
                    <input type="date" id="filter-created-after" class="form-control">
                </div>
                <div class="input-group input-group-sm">
                    <span class="input-group-text">Before</span>
                    <input type="date" id="filter-created-before" class="form-control">
                </div>
            </div>

            <hr class="my-3">

            <!-- Custom query (advanced syntax) -->
            <div class="mb-3">
                <label class="form-label small fw-bold">Advanced Query</label>
                <input type="text" id="filter-custom-query" class="form-control form-control-sm"
                       placeholder='e.g., email:*@gmail.com AND tag:suspect'>
                <small class="text-muted d-block mt-1">
                    <a href="#" id="syntax-help-link">View syntax help</a>
                </small>
            </div>

            <!-- Action buttons -->
            <div class="d-flex gap-2">
                <button id="search-apply-btn" class="btn btn-sm btn-primary flex-grow-1">
                    <i class="fas fa-search"></i> Search
                </button>
                <button id="search-clear-btn" class="btn btn-sm btn-outline-secondary">
                    <i class="fas fa-times"></i> Clear
                </button>
            </div>

            <!-- Result count badge -->
            <div id="search-result-badge" class="mt-2 text-center">
                <small class="text-muted" id="search-count-text"></small>
            </div>
        </div>
    `;

    // Insert panel into sidebar after search input
    searchContainer.appendChild(panel);

    // Load state into form
    restoreSearchState(state);

    // Setup event listeners
    setupSearchListeners(state, projectName);
    setupSyntaxHelpLink();
}

/**
 * Restore search state into form fields
 */
function restoreSearchState(state) {
    document.getElementById('filter-name').value = state.name;
    document.getElementById('filter-email').value = state.email;
    document.getElementById('filter-phone').value = state.phone;
    document.getElementById('filter-username').value = state.username;

    // Restore multi-select values
    const entityTypesSelect = document.getElementById('filter-entity-types');
    if (entityTypesSelect && Array.isArray(state.entityTypes)) {
        Array.from(entityTypesSelect.options).forEach(option => {
            option.selected = state.entityTypes.includes(option.value);
        });
    }

    document.getElementById('filter-created-after').value = state.createdAfter;
    document.getElementById('filter-created-before').value = state.createdBefore;
    document.getElementById('filter-custom-query').value = state.customQuery;

    // Set boolean mode radio
    const boolRadio = document.querySelector(`input[name="boolean-mode"][value="${state.booleanMode}"]`);
    if (boolRadio) boolRadio.checked = true;
}

/**
 * Setup event listeners for advanced search
 */
function setupSearchListeners(state, projectName) {
    const applyBtn = document.getElementById('search-apply-btn');
    const clearBtn = document.getElementById('search-clear-btn');

    applyBtn.addEventListener('click', async () => {
        // Gather filter values
        updateStateFromForm(state);
        state.save();

        // Execute search
        await executeAdvancedSearch(state, projectName);
    });

    clearBtn.addEventListener('click', () => {
        state.clear();
        restoreSearchState(state);
        document.getElementById('search-count-text').textContent = '';
        // Clear results
        const personList = document.getElementById('person-list');
        if (personList) {
            personList.innerHTML = '';
            const noData = document.createElement('li');
            noData.className = 'list-group-item text-center text-muted';
            noData.textContent = 'No results';
            personList.appendChild(noData);
        }
    });

    // Allow Enter key to trigger search in input fields
    ['filter-name', 'filter-email', 'filter-phone', 'filter-username', 'filter-custom-query'].forEach(id => {
        const input = document.getElementById(id);
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    applyBtn.click();
                }
            });
        }
    });
}

/**
 * Update state object from form fields
 */
function updateStateFromForm(state) {
    state.name = document.getElementById('filter-name').value;
    state.email = document.getElementById('filter-email').value;
    state.phone = document.getElementById('filter-phone').value;
    state.username = document.getElementById('filter-username').value;
    state.entityTypes = Array.from(document.getElementById('filter-entity-types').selectedOptions).map(o => o.value);
    state.booleanMode = document.querySelector('input[name="boolean-mode"]:checked')?.value || 'AND';
    state.createdAfter = document.getElementById('filter-created-after').value;
    state.createdBefore = document.getElementById('filter-created-before').value;
    state.customQuery = document.getElementById('filter-custom-query').value;
}

/**
 * Execute advanced search via API
 */
async function executeAdvancedSearch(state, projectName) {
    try {
        // Build query string
        const queryParts = [];

        // Add field filters with operator
        if (state.customQuery) {
            // Use custom query as-is
            queryParts.push(state.customQuery);
        } else {
            // Build from field filters
            if (state.name) queryParts.push(`name:${state.name}`);
            if (state.email) queryParts.push(`email:${state.email}`);
            if (state.phone) queryParts.push(`phone:${state.phone}`);
            if (state.username) queryParts.push(`username:${state.username}`);
        }

        // Join with boolean operator
        let query = queryParts.join(` ${state.booleanMode} `);

        // If no query built, show error
        if (!query) {
            alert('Please enter at least one search criteria');
            return;
        }

        // Add date filters if present
        if (state.createdAfter || state.createdBefore) {
            if (query) query = `(${query})`;
            const dateFilters = [];
            if (state.createdAfter) dateFilters.push(`created_after:${state.createdAfter}`);
            if (state.createdBefore) dateFilters.push(`created_before:${state.createdBefore}`);
            query = query ? query + ' AND ' + dateFilters.join(' AND ') : dateFilters.join(' AND ');
        }

        // Build URL with parameters
        const url = new URL(`/api/v1/projects/${projectName}/search/advanced`, window.location.origin);
        url.searchParams.append('q', query);
        url.searchParams.append('limit', '100');
        url.searchParams.append('highlight', 'true');

        // Add entity types filter if selected
        if (state.entityTypes.length > 0) {
            url.searchParams.append('entity_types', state.entityTypes.join(','));
        }

        console.log('Executing search:', {
            query,
            url: url.toString(),
            state
        });

        // Execute search
        const response = await fetch(url);
        if (!response.ok) {
            const error = await response.json();
            console.error('Search error:', error);
            alert(`Search failed: ${error.detail || 'Unknown error'}`);
            return;
        }

        const data = await response.json();
        console.log('Search results:', data);

        // Display results
        displaySearchResults(data.results, data.total);

    } catch (error) {
        console.error('Advanced search error:', error);
        alert('Search failed: ' + error.message);
    }
}

/**
 * Display search results in the people list
 */
function displaySearchResults(results, total) {
    const personList = document.getElementById('person-list');
    const countText = document.getElementById('search-count-text');

    if (!personList) return;

    personList.innerHTML = '';
    countText.textContent = `Found ${total} result${total !== 1 ? 's' : ''}`;

    if (results.length === 0) {
        const noData = document.createElement('li');
        noData.className = 'list-group-item text-center text-muted';
        noData.textContent = 'No results found';
        personList.appendChild(noData);
        return;
    }

    // Create list items for results
    results.forEach(result => {
        const listItem = document.createElement('li');
        listItem.className = 'list-group-item person-item d-flex justify-content-between align-items-center';

        // Build display info
        const displayName = result.entity_data?.name?.first_name
            ? `${result.entity_data.name.first_name} ${result.entity_data.name.last_name || ''}`.trim()
            : result.entity_data?.name || 'Unknown';

        const personInfo = document.createElement('div');

        const nameDiv = document.createElement('div');
        nameDiv.className = 'fw-bold';
        nameDiv.textContent = displayName;
        personInfo.appendChild(nameDiv);

        // Add type badge
        const typeDiv = document.createElement('small');
        typeDiv.className = 'text-muted';
        typeDiv.textContent = `[${result.entity_type}] (Score: ${(result.score * 100).toFixed(0)}%)`;
        personInfo.appendChild(typeDiv);

        // Add matched fields
        if (result.matched_fields && result.matched_fields.length > 0) {
            const fieldsDiv = document.createElement('small');
            fieldsDiv.className = 'text-secondary';
            fieldsDiv.textContent = `Matched: ${result.matched_fields.join(', ')}`;
            personInfo.appendChild(fieldsDiv);
        }

        listItem.appendChild(personInfo);

        // Add click handler to select result
        listItem.addEventListener('click', async () => {
            // Remove active class from all items
            document.querySelectorAll('.person-item').forEach(item => {
                item.classList.remove('active');
            });
            listItem.classList.add('active');

            // Fetch full entity data and display
            try {
                const response = await fetch(`/get_person/${result.entity_id}`);
                if (response.ok) {
                    const entity = await response.json();
                    const detailsContainer = document.getElementById('person-details');
                    if (detailsContainer) {
                        // Import and use the renderPersonDetails function
                        const { renderPersonDetails } = await import('./ui-person-details.js');
                        renderPersonDetails(detailsContainer, entity);

                        // On mobile, hide sidebar
                        if (window.innerWidth < 768) {
                            document.querySelector('.sidebar').classList.add('d-none');
                            detailsContainer.classList.remove('d-none');
                        }
                    }
                }
            } catch (error) {
                console.error('Failed to load entity details:', error);
            }
        });

        personList.appendChild(listItem);
    });
}

/**
 * Setup syntax help link
 */
function setupSyntaxHelpLink() {
    const link = document.getElementById('syntax-help-link');
    if (link) {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            showSyntaxHelp();
        });
    }
}

/**
 * Show syntax help modal
 */
function showSyntaxHelp() {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'syntax-help-modal';
    modal.tabIndex = -1;
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Advanced Search Syntax Help</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <h6 class="mb-3">Operators</h6>
                    <ul class="mb-3">
                        <li><code>AND</code> - Both conditions must match</li>
                        <li><code>OR</code> - At least one condition must match</li>
                        <li><code>NOT</code> - Negates the following condition</li>
                    </ul>

                    <h6 class="mb-3">Field Search</h6>
                    <p>Search in specific fields using <code>field:value</code> syntax:</p>
                    <ul class="mb-3">
                        <li><code>name:John</code> - Search for name containing "John"</li>
                        <li><code>email:*@gmail.com</code> - Search for Gmail addresses</li>
                        <li><code>phone:555*</code> - Search for phone numbers starting with 555</li>
                    </ul>

                    <h6 class="mb-3">Wildcards</h6>
                    <ul class="mb-3">
                        <li><code>*</code> - Matches any number of characters</li>
                        <li><code>?</code> - Matches exactly one character</li>
                    </ul>

                    <h6 class="mb-3">Examples</h6>
                    <ul>
                        <li><code>email:john@example.com</code></li>
                        <li><code>name:John AND email:*@gmail.com</code></li>
                        <li><code>(tag:suspect OR tag:poi) AND NOT status:cleared</code></li>
                        <li><code>"John Smith"</code> - Exact phrase match</li>
                    </ul>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    const syntaxModal = new bootstrap.Modal(modal);
    syntaxModal.show();
}

/**
 * Setup basic search input to show result count
 */
function setupBasicSearchInput(projectName, state) {
    const searchInput = document.getElementById('search-input');
    if (!searchInput) return;

    let searchTimeout;
    searchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();

        if (!query) {
            document.getElementById('search-count-text').textContent = '';
            return;
        }

        // Debounce search
        searchTimeout = setTimeout(async () => {
            try {
                const url = new URL(`/api/v1/projects/${projectName}/search`, window.location.origin);
                url.searchParams.append('q', query);
                url.searchParams.append('limit', '100');

                const response = await fetch(url);
                if (response.ok) {
                    const data = await response.json();
                    const countText = document.getElementById('search-count-text');
                    if (countText) {
                        countText.textContent = `Found ${data.total} result${data.total !== 1 ? 's' : ''}`;
                    }
                }
            } catch (error) {
                console.error('Search error:', error);
            }
        }, 300);
    });
}

export { AdvancedSearchState };
