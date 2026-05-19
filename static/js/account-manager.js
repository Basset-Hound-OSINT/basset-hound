// account-manager.js - Handles account management UI for entities (Phase 4)

// Account state management
let accountState = {
    entityId: null,
    projectName: null,
    accounts: [],
    platforms: [],
    currentEntity: null
};

export async function initAccountManager(entityId, projectName) {
    accountState.entityId = entityId;
    accountState.projectName = projectName;

    try {
        // Fetch the current entity
        const currentEntityRes = await fetch(`/get_person/${entityId}`);
        if (!currentEntityRes.ok) {
            throw new Error(`Failed to fetch current entity: ${currentEntityRes.statusText}`);
        }
        accountState.currentEntity = await currentEntityRes.json();

        // Fetch accounts from API (Phase 8: Updated schema)
        const accountsRes = await fetch(
            `/api/v1/projects/${projectName}/entities/${entityId}/accounts`
        );

        if (accountsRes.ok) {
            const accountData = await accountsRes.json();
            // Phase 8 schema: accounts is directly in response, with platform nested object
            accountState.accounts = accountData.accounts || [];
        } else {
            console.warn('Could not fetch accounts from API');
            accountState.accounts = [];
        }

        // Fetch platforms list
        const platformsRes = await fetch('/api/v1/platforms');
        if (platformsRes.ok) {
            const platformData = await platformsRes.json();
            accountState.platforms = platformData.platforms || [];
        } else {
            console.warn('Could not fetch platforms from API');
            accountState.platforms = [];
        }

        // Create and inject the accounts tab UI
        createAccountsTabs();
        setupAccountEventListeners();

    } catch (error) {
        console.error('Error initializing account manager:', error);
        showToast('Failed to load accounts', 'danger');
    }
}

function createAccountsTabs() {
    const container = document.querySelector('#person-details');
    if (!container) return;

    // Check if accounts tabs already exist
    let tabsContainer = container.querySelector('.accounts-tabs');
    if (tabsContainer) {
        tabsContainer.remove();
    }

    // Create the tab container
    const tabsHtml = `
    <div class="accounts-tabs">
        <ul class="nav nav-tabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="accounts-tab" data-bs-toggle="tab"
                        data-bs-target="#accounts-panel" type="button" role="tab"
                        aria-controls="accounts-panel" aria-selected="false">
                    <i class="fas fa-user-circle me-2"></i>Accounts
                    <span class="badge bg-secondary ms-2" id="account-count">0</span>
                </button>
            </li>
        </ul>
        <div class="tab-content mt-3">
            <div class="tab-pane fade" id="accounts-panel" role="tabpanel"
                 aria-labelledby="accounts-tab">
                <div id="accounts-content">
                    <!-- Will be populated -->
                </div>
            </div>
        </div>
    </div>
    `;

    // Insert tabs after relationships tabs or at the beginning
    const relationshipsTabs = container.querySelector('.relationships-tabs');
    if (relationshipsTabs) {
        relationshipsTabs.insertAdjacentHTML('afterend', tabsHtml);
    } else {
        const profileHeader = container.querySelector('.profile-header');
        if (profileHeader) {
            profileHeader.insertAdjacentHTML('afterend', tabsHtml);
        } else {
            container.insertAdjacentHTML('afterbegin', tabsHtml);
        }
    }

    renderAccountsList();
}

function renderAccountsList() {
    const contentContainer = document.getElementById('accounts-content');
    const countBadge = document.getElementById('account-count');

    if (!contentContainer) return;

    // Update count badge
    countBadge.textContent = accountState.accounts.length;

    // Clear content
    contentContainer.innerHTML = '';

    if (accountState.accounts.length === 0) {
        contentContainer.innerHTML = `
        <div class="text-center py-5">
            <i class="fas fa-user-circle fa-3x text-muted mb-3"></i>
            <p class="text-muted">No accounts yet</p>
            <button class="btn btn-primary btn-sm" id="add-account-btn">
                <i class="fas fa-plus me-2"></i>Link Account
            </button>
        </div>
        `;
        setupAccountEventListeners();
        return;
    }

    // Create table for accounts
    const table = document.createElement('table');
    table.className = 'table table-hover';
    table.innerHTML = `
    <thead>
        <tr>
            <th style="width: 30px;"></th>
            <th>Platform</th>
            <th>Account</th>
            <th>Properties</th>
            <th style="width: 120px;">Actions</th>
        </tr>
    </thead>
    <tbody id="accounts-table-body">
    </tbody>
    `;

    const tbody = table.querySelector('tbody');

    accountState.accounts.forEach((account, idx) => {
        const row = document.createElement('tr');
        row.className = 'account-row';
        // Phase 8: platform_id is a direct property of account response
        row.dataset.accountId = account.platform_id;

        // Icon column (Phase 8: platform is nested object in response)
        const iconCell = document.createElement('td');
        const platformIconClass = account.platform?.icon_class || 'fas fa-globe';
        const platformColor = account.platform?.color || '#999999';
        iconCell.innerHTML = `<i class="${platformIconClass}" style="color: ${platformColor}; font-size: 1.2em;"></i>`;
        row.appendChild(iconCell);

        // Platform column (Phase 8: full platform info embedded in account)
        const platformCell = document.createElement('td');
        const platformBadge = `<span class="badge" style="background-color: ${platformColor}; color: white;">${account.platform?.name || 'Unknown'}</span>`;
        const categoryBadge = account.platform?.category ? `<br><small class="text-muted">${account.platform.category}</small>` : '';
        platformCell.innerHTML = platformBadge + categoryBadge;
        row.appendChild(platformCell);

        // Account column
        const accountCell = document.createElement('td');
        const displayName = account.display_name || account.username;
        const profileLink = account.profile_url
            ? `<a href="${account.profile_url}" target="_blank" title="View profile">${displayName}</a>`
            : displayName;
        accountCell.innerHTML = `
        <div class="fw-bold">${profileLink}</div>
        <small class="text-muted">@${account.username}</small>
        `;
        if (account.verified) {
            accountCell.innerHTML += '<br><small><i class="fas fa-check-circle text-success me-1"></i>Verified</small>';
        }
        row.appendChild(accountCell);

        // Properties column
        const propsCell = document.createElement('td');
        const propsText = formatAccountProperties(account);
        propsCell.innerHTML = propsText ? `<small>${propsText}</small>` : '<small class="text-muted">-</small>';
        row.appendChild(propsCell);

        // Actions column
        const actionsCell = document.createElement('td');
        actionsCell.innerHTML = `
        <div class="btn-group btn-group-sm" role="group">
            <button class="btn btn-outline-secondary edit-account-btn" title="Edit">
                <i class="fas fa-edit"></i>
            </button>
            <button class="btn btn-outline-danger delete-account-btn" title="Delete">
                <i class="fas fa-trash"></i>
            </button>
        </div>
        `;

        actionsCell.querySelector('.edit-account-btn').addEventListener('click', () => {
            openAccountModal(account.platform_id, account);
        });

        actionsCell.querySelector('.delete-account-btn').addEventListener('click', () => {
            showDeleteConfirmation(account);
        });

        row.appendChild(actionsCell);
        tbody.appendChild(row);
    });

    contentContainer.appendChild(table);

    // Add button below table
    const addBtn = document.createElement('button');
    addBtn.id = 'add-account-btn';
    addBtn.className = 'btn btn-primary mt-3';
    addBtn.innerHTML = '<i class="fas fa-plus me-2"></i>Link Account';
    contentContainer.appendChild(addBtn);

    setupAccountEventListeners();
}

function setupAccountEventListeners() {
    const addBtn = document.getElementById('add-account-btn');
    if (addBtn) {
        // Remove old listeners to prevent duplicates
        const newBtn = addBtn.cloneNode(true);
        if (addBtn.parentNode) {
            addBtn.parentNode.replaceChild(newBtn, addBtn);
        }

        // Add new listener
        const updatedBtn = document.getElementById('add-account-btn');
        if (updatedBtn) {
            updatedBtn.addEventListener('click', () => openAccountModal());
        }
    }
}

function openAccountModal(platformId = null, existingAccount = null) {
    const projectName = accountState.projectName;
    const currentEntityId = accountState.entityId;

    // Remove existing modal if present and clean up
    let modal = document.getElementById('account-modal');
    if (modal) {
        try {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
                bsModal.dispose();
            }
        } catch (e) {
            // Modal instance doesn't exist
        }
        modal.remove();
    }

    const isEdit = !!existingAccount;
    const modalHtml = `
    <div class="modal fade" id="account-modal" tabindex="-1" aria-labelledby="account-modal-label" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="account-modal-label">
                        <i class="fas fa-user-circle me-2"></i>${isEdit ? 'Edit' : 'Link'} Account
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <form id="account-form">
                        <!-- Platform selection -->
                        <div class="mb-3">
                            <label for="platform-select" class="form-label">
                                <i class="fas fa-globe me-2"></i>Platform <span class="text-danger">*</span>
                            </label>
                            <div class="input-group">
                                <input type="text" class="form-control" id="platform-search"
                                       placeholder="Search platforms...">
                                <button class="btn btn-outline-secondary" type="button" id="clear-platform-btn">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                            <div id="platform-search-results" class="list-group mt-2" style="max-height: 250px; overflow-y: auto; display: none;">
                            </div>
                            <div id="selected-platform-display" class="alert alert-info mt-2" style="display: none;">
                                Selected: <strong id="selected-platform-name"></strong>
                                <small id="selected-platform-category" class="d-block text-muted"></small>
                            </div>
                            <input type="hidden" id="platform-id-field">
                        </div>

                        <!-- Username/identifier -->
                        <div class="mb-3">
                            <label for="account-username" class="form-label">
                                <i class="fas fa-at me-2"></i>Username/Handle <span class="text-danger">*</span>
                            </label>
                            <input type="text" class="form-control" id="account-username"
                                   placeholder="e.g., johndoe, @johndoe, john@example.com">
                        </div>

                        <!-- Optional fields -->
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="account-display-name" class="form-label">
                                    <i class="fas fa-id-card me-2"></i>Display Name
                                </label>
                                <input type="text" class="form-control" id="account-display-name"
                                       placeholder="e.g., John Doe">
                            </div>

                            <div class="col-md-6 mb-3">
                                <label for="account-verified" class="form-label">
                                    <i class="fas fa-check-circle me-2"></i>Verification
                                </label>
                                <select class="form-select" id="account-verified">
                                    <option value="">Not specified</option>
                                    <option value="true">Verified</option>
                                    <option value="false">Not verified</option>
                                </select>
                            </div>
                        </div>

                        <!-- Bio field -->
                        <div class="mb-3">
                            <label for="account-bio" class="form-label">
                                <i class="fas fa-align-left me-2"></i>Bio/Description
                            </label>
                            <textarea class="form-control" id="account-bio" rows="2"
                                      placeholder="Account bio or description..."></textarea>
                        </div>

                        <!-- Profile URL -->
                        <div class="mb-3">
                            <label for="account-profile-url" class="form-label">
                                <i class="fas fa-link me-2"></i>Profile URL
                            </label>
                            <input type="url" class="form-control" id="account-profile-url"
                                   placeholder="https://example.com/profile">
                        </div>

                        <!-- Advanced properties row -->
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label for="account-followers" class="form-label">
                                    <i class="fas fa-users me-2"></i>Followers
                                </label>
                                <input type="number" class="form-control" id="account-followers"
                                       placeholder="Number of followers" min="0">
                            </div>

                            <div class="col-md-6 mb-3">
                                <label for="account-last-active" class="form-label">
                                    <i class="fas fa-calendar me-2"></i>Last Active
                                </label>
                                <input type="datetime-local" class="form-control" id="account-last-active">
                            </div>
                        </div>

                        <!-- Password reference -->
                        <div class="mb-3">
                            <label for="account-password-ref" class="form-label">
                                <i class="fas fa-key me-2"></i>Password Reference
                            </label>
                            <input type="text" class="form-control" id="account-password-ref"
                                   placeholder="Reference or vault location">
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="save-account-btn">
                        <i class="fas fa-save me-2"></i>${isEdit ? 'Update' : 'Link'} Account
                    </button>
                </div>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    modal = document.getElementById('account-modal');

    // Setup event listeners for modal
    const platformSearchInput = document.getElementById('platform-search');
    const platformSearchResults = document.getElementById('platform-search-results');
    const selectedPlatformDisplay = document.getElementById('selected-platform-display');
    const selectedPlatformName = document.getElementById('selected-platform-name');
    const selectedPlatformCategory = document.getElementById('selected-platform-category');
    const platformIdField = document.getElementById('platform-id-field');
    const clearPlatformBtn = document.getElementById('clear-platform-btn');
    const saveBtn = document.getElementById('save-account-btn');

    // Platform search with debouncing
    let searchTimeout;
    platformSearchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const searchTerm = e.target.value.toLowerCase().trim();

        if (!searchTerm) {
            platformSearchResults.style.display = 'none';
            return;
        }

        searchTimeout = setTimeout(() => {
            const filtered = accountState.platforms.filter(platform => {
                const nameMatch = platform.name.toLowerCase().includes(searchTerm);
                const categoryMatch = platform.category.toLowerCase().includes(searchTerm);
                return nameMatch || categoryMatch;
            }).slice(0, 15);

            if (filtered.length === 0) {
                platformSearchResults.innerHTML = '<div class="list-group-item text-muted text-center py-3"><i class="fas fa-search me-2"></i>No platforms found</div>';
                platformSearchResults.style.display = 'block';
                return;
            }

            platformSearchResults.innerHTML = filtered.map(platform => {
                const platformName = platform.name.toLowerCase();
                const highlightedName = platform.name.replace(
                    new RegExp(`(${searchTerm})`, 'gi'),
                    '<strong>$1</strong>'
                );
                const iconClass = platform.icon_class || 'fas fa-globe';
                const color = platform.color || '#999999';
                return `
                <button type="button" class="list-group-item list-group-item-action" data-platform-id="${platform.id}">
                    <div class="d-flex align-items-center gap-2">
                        <i class="${iconClass}" style="color: ${color};"></i>
                        <div class="flex-grow-1">
                            <div class="fw-bold">${highlightedName}</div>
                            <small class="text-muted">${platform.category}</small>
                        </div>
                    </div>
                </button>
                `;
            }).join('');
            platformSearchResults.style.display = 'block';

            // Add click handlers
            platformSearchResults.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    const pId = btn.dataset.platformId;
                    const platform = accountState.platforms.find(p => p.id === pId);

                    if (platform) {
                        platformIdField.value = pId;
                        selectedPlatformName.textContent = platform.name;
                        selectedPlatformCategory.textContent = platform.category;
                        selectedPlatformDisplay.style.display = 'block';
                        platformSearchResults.style.display = 'none';
                        platformSearchInput.value = '';
                    }
                });
            });
        }, 300); // Debounce for 300ms
    });

    clearPlatformBtn.addEventListener('click', () => {
        platformIdField.value = '';
        selectedPlatformDisplay.style.display = 'none';
        platformSearchInput.value = '';
        platformSearchResults.style.display = 'none';
    });

    // If editing existing account, populate form
    if (isEdit && existingAccount) {
        platformIdField.value = existingAccount.platform_id;
        selectedPlatformName.textContent = existingAccount.platform?.name || 'Unknown';
        selectedPlatformCategory.textContent = existingAccount.platform?.category || '';
        selectedPlatformDisplay.style.display = 'block';
        platformSearchInput.disabled = true;
        platformSearchInput.value = existingAccount.platform?.name || '';
        clearPlatformBtn.disabled = true;

        document.getElementById('account-username').value = existingAccount.username || '';
        document.getElementById('account-display-name').value = existingAccount.display_name || '';
        document.getElementById('account-bio').value = existingAccount.bio || '';
        document.getElementById('account-profile-url').value = existingAccount.profile_url || '';
        document.getElementById('account-followers').value = existingAccount.followers || '';
        document.getElementById('account-password-ref').value = existingAccount.password_ref || '';

        if (existingAccount.verified !== undefined && existingAccount.verified !== null) {
            document.getElementById('account-verified').value = existingAccount.verified ? 'true' : 'false';
        }

        if (existingAccount.last_active) {
            // Convert ISO format to datetime-local format
            const dateObj = new Date(existingAccount.last_active);
            const isoString = dateObj.toISOString().slice(0, 16);
            document.getElementById('account-last-active').value = isoString;
        }
    }

    // Save button handler
    saveBtn.addEventListener('click', () => {
        if (isEdit) {
            updateAccount();
        } else {
            createAccount();
        }
    });

    // Show modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

async function createAccount() {
    const projectName = accountState.projectName;
    const currentEntityId = accountState.entityId;
    const platformId = document.getElementById('platform-id-field').value;
    const username = document.getElementById('account-username').value.trim();
    const displayName = document.getElementById('account-display-name').value.trim();
    const bio = document.getElementById('account-bio').value.trim();
    const profileUrl = document.getElementById('account-profile-url').value.trim();
    const followers = document.getElementById('account-followers').value;
    const lastActive = document.getElementById('account-last-active').value;
    const passwordRef = document.getElementById('account-password-ref').value.trim();
    const verifiedValue = document.getElementById('account-verified').value;

    // Validation
    if (!platformId || platformId.trim() === '') {
        showToast('Please select a platform', 'warning');
        return;
    }

    if (!username || username.trim() === '') {
        showToast('Please enter a username/handle', 'warning');
        return;
    }

    try {
        const saveBtn = document.getElementById('save-account-btn');
        const originalText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Linking...';

        const accountData = {
            platform_id: platformId,
            username: username,
            profile_url: profileUrl || undefined,
            display_name: displayName || undefined,
            verified: verifiedValue ? (verifiedValue === 'true') : undefined,
            followers: followers ? parseInt(followers) : undefined,
            bio: bio || undefined,
            last_active: lastActive || undefined,
            password_ref: passwordRef || undefined
        };

        // Remove undefined values
        Object.keys(accountData).forEach(key => {
            if (accountData[key] === undefined) {
                delete accountData[key];
            }
        });

        const createRes = await fetch(
            `/api/v1/projects/${projectName}/entities/${currentEntityId}/accounts`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(accountData)
            }
        );

        if (!createRes.ok) {
            const errorData = await createRes.json().catch(() => ({}));
            // Phase 8: error response may have detail or error fields
            throw new Error(errorData.detail || errorData.error?.message || `Failed to link account: ${createRes.statusText}`);
        }

        showToast('Account linked successfully', 'success');

        // Close modal and refresh
        const modal = document.getElementById('account-modal');
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }

        // Refresh accounts
        setTimeout(() => {
            initAccountManager(currentEntityId, projectName);
        }, 300);

    } catch (error) {
        console.error('Error linking account:', error);
        showToast(`Error: ${error.message}`, 'danger');
    } finally {
        const saveBtn = document.getElementById('save-account-btn');
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fas fa-save me-2"></i>Link Account';
        }
    }
}

async function updateAccount() {
    const projectName = accountState.projectName;
    const currentEntityId = accountState.entityId;
    const platformId = document.getElementById('platform-id-field').value;
    const username = document.getElementById('account-username').value.trim();
    const displayName = document.getElementById('account-display-name').value.trim();
    const bio = document.getElementById('account-bio').value.trim();
    const profileUrl = document.getElementById('account-profile-url').value.trim();
    const followers = document.getElementById('account-followers').value;
    const lastActive = document.getElementById('account-last-active').value;
    const passwordRef = document.getElementById('account-password-ref').value.trim();
    const verifiedValue = document.getElementById('account-verified').value;

    // Validation
    if (!username || username.trim() === '') {
        showToast('Please enter a username/handle', 'warning');
        return;
    }

    try {
        const saveBtn = document.getElementById('save-account-btn');
        const originalText = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Updating...';

        const updateData = {
            username: username,
            profile_url: profileUrl || undefined,
            display_name: displayName || undefined,
            verified: verifiedValue ? (verifiedValue === 'true') : undefined,
            followers: followers ? parseInt(followers) : undefined,
            bio: bio || undefined,
            last_active: lastActive || undefined,
            password_ref: passwordRef || undefined
        };

        // Remove undefined values
        Object.keys(updateData).forEach(key => {
            if (updateData[key] === undefined) {
                delete updateData[key];
            }
        });

        const updateRes = await fetch(
            `/api/v1/projects/${projectName}/entities/${currentEntityId}/accounts/${platformId}`,
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updateData)
            }
        );

        if (!updateRes.ok) {
            const errorData = await updateRes.json().catch(() => ({}));
            // Phase 8: error response may have detail or error fields
            throw new Error(errorData.detail || errorData.error?.message || `Failed to update account: ${updateRes.statusText}`);
        }

        showToast('Account updated successfully', 'success');

        // Close modal and refresh
        const modal = document.getElementById('account-modal');
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }

        // Refresh accounts
        setTimeout(() => {
            initAccountManager(currentEntityId, projectName);
        }, 300);

    } catch (error) {
        console.error('Error updating account:', error);
        showToast(`Error: ${error.message}`, 'danger');
    } finally {
        const saveBtn = document.getElementById('save-account-btn');
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fas fa-save me-2"></i>Update Account';
        }
    }
}

function showDeleteConfirmation(account) {
    const projectName = accountState.projectName;
    const currentEntityId = accountState.entityId;
    const platformName = account.platform?.name || 'Unknown Platform';
    const username = account.username;

    // Remove existing modal if present
    let modal = document.getElementById('delete-account-modal');
    if (modal) {
        modal.remove();
    }

    const modalHtml = `
    <div class="modal fade" id="delete-account-modal" tabindex="-1" aria-labelledby="delete-account-modal-label" aria-hidden="true">
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header bg-danger text-white">
                    <h5 class="modal-title" id="delete-account-modal-label">
                        <i class="fas fa-trash me-2"></i>Delete Account
                    </h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <p>Are you sure you want to remove <strong>@${username}</strong> from <strong>${platformName}</strong>?</p>
                    <p class="text-muted small">This action cannot be undone.</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-danger" id="confirm-delete-btn">
                        <i class="fas fa-trash me-2"></i>Delete
                    </button>
                </div>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    modal = document.getElementById('delete-account-modal');

    document.getElementById('confirm-delete-btn').addEventListener('click', async () => {
        await deleteAccount(account.platform_id);

        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }
    });

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

async function deleteAccount(platformId) {
    const projectName = accountState.projectName;
    const currentEntityId = accountState.entityId;

    try {
        const deleteRes = await fetch(
            `/api/v1/projects/${projectName}/entities/${currentEntityId}/accounts/${platformId}`,
            {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' }
            }
        );

        if (!deleteRes.ok) {
            const errorData = await deleteRes.json().catch(() => ({}));
            // Phase 8: error response may have detail or error fields
            throw new Error(errorData.detail || errorData.error?.message || `Failed to delete account: ${deleteRes.statusText}`);
        }

        showToast('Account deleted successfully', 'success');

        // Refresh accounts
        setTimeout(() => {
            initAccountManager(currentEntityId, projectName);
        }, 300);

    } catch (error) {
        console.error('Error deleting account:', error);
        showToast(`Error: ${error.message}`, 'danger');
    }
}

function formatAccountProperties(account) {
    if (!account || typeof account !== 'object') return '';

    const parts = [];

    if (account.bio) {
        const bioPreview = account.bio.substring(0, 25);
        const truncated = account.bio.length > 25 ? '...' : '';
        parts.push(`Bio: ${bioPreview}${truncated}`);
    }

    if (account.followers) {
        parts.push(`Followers: ${account.followers.toLocaleString()}`);
    }

    if (account.last_active) {
        const dateStr = account.last_active.split('T')[0];
        parts.push(`Last active: ${dateStr}`);
    }

    if (account.created_at) {
        const dateStr = account.created_at.split('T')[0];
        parts.push(`Created: ${dateStr}`);
    }

    return parts.join(' • ');
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'position-fixed bottom-0 end-0 p-3';
    container.style.zIndex = '1100';
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

    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}
