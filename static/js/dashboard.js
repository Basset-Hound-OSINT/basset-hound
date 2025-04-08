// Global variables
let people = [];
let selectedPersonId = null;

// Function to fetch all people
async function fetchPeople() {
    const response = await fetch('/get_people');
    people = await response.json();
    renderPeopleList();
}

// Function to render the people list
function renderPeopleList() {
    const personList = document.getElementById('person-list');
    personList.innerHTML = '';
    
    people.forEach((person, index) => {
        const primaryName = person.names && person.names.length > 0 ? person.names[0] : { first_name: '', last_name: '' };
        const displayName = `${primaryName.first_name} ${primaryName.last_name}`.trim() || 'Unnamed Person';
        
        const li = document.createElement('li');
        li.className = 'person-item' + (index === selectedPersonId ? ' active' : '');
        li.textContent = displayName;
        li.addEventListener('click', () => selectPerson(index));
        personList.appendChild(li);
    });
}

// Function to show or hide a field based on value
function toggleField(containerId, valueElementId, value) {
    const container = document.getElementById(containerId);
    const valueElement = document.getElementById(valueElementId);
    
    if (value && value.trim() !== '') {
        container.style.display = 'flex';
        valueElement.textContent = value;
        return true;
    } else {
        container.style.display = 'none';
        return false;
    }
}

// Function to select a person
async function selectPerson(personId) {
    selectedPersonId = personId;
    renderPeopleList();
    
    const response = await fetch(`/get_person/${personId}`);
    const person = await response.json();
    
    document.getElementById('no-selection').style.display = 'none';
    document.getElementById('person-profile').style.display = 'block';
    
    // Update profile name
    const primaryName = person.names && person.names.length > 0 ? person.names[0] : { first_name: '', middle_name: '', last_name: '' };
    document.getElementById('profile-name').textContent = `${primaryName.first_name} ${primaryName.middle_name ? primaryName.middle_name + ' ' : ''}${primaryName.last_name}`;
    
    // Display all names
    const namesElement = document.getElementById('view-names');
    namesElement.innerHTML = '';
    if (person.names && person.names.length > 0) {
        person.names.forEach(name => {
            const nameDiv = document.createElement('div');
            nameDiv.textContent = `${name.first_name} ${name.middle_name ? name.middle_name + ' ' : ''}${name.last_name}`;
            namesElement.appendChild(nameDiv);
        });
    }
    
    // Display dates of birth
    const dobElement = document.getElementById('view-dob');
    dobElement.innerHTML = '';
    const dobContainer = document.getElementById('view-dob-container');
    if (person.dates_of_birth && person.dates_of_birth.length > 0) {
        dobContainer.style.display = 'flex';
        person.dates_of_birth.forEach(dob => {
            const dobDiv = document.createElement('div');
            dobDiv.textContent = dob;
            dobElement.appendChild(dobDiv);
        });
    } else {
        dobContainer.style.display = 'none';
    }
    
    // Display emails
    const emailElement = document.getElementById('view-email');
    emailElement.innerHTML = '';
    const emailContainer = document.getElementById('view-email-container');
    let hasEmail = false;
    if (person.emails && person.emails.length > 0) {
        hasEmail = true;
        emailContainer.style.display = 'flex';
        person.emails.forEach(email => {
            const emailDiv = document.createElement('div');
            emailDiv.textContent = email;
            emailElement.appendChild(emailDiv);
        });
    } else {
        emailContainer.style.display = 'none';
    }
    
    // Show/hide contact section based on if any field is populated
    document.getElementById('contact-info-section').style.display = hasEmail ? 'block' : 'none';
    
    // Handle social media links
    const socialButtons = document.getElementById('social-buttons');
    socialButtons.innerHTML = '';
    
    let hasSocialMedia = false;
    
    // LinkedIn
    if (person.linkedin && person.linkedin.length > 0) {
        hasSocialMedia = true;
        person.linkedin.forEach(profile => {
            if (profile && profile.trim() !== '') {
                const linkedinBtn = document.createElement('a');
                linkedinBtn.href = ensureHttps(profile);
                linkedinBtn.target = "_blank";
                linkedinBtn.innerHTML = '<i class="fab fa-linkedin fa-2x text-primary"></i>';
                linkedinBtn.className = 'me-3';
                socialButtons.appendChild(linkedinBtn);
            }
        });
    }
    
    // Twitter
    if (person.twitter && person.twitter.length > 0) {
        hasSocialMedia = true;
        person.twitter.forEach(profile => {
            if (profile && profile.trim() !== '') {
                const twitterBtn = document.createElement('a');
                twitterBtn.href = ensureHttps(ensureTwitterUrl(profile));
                twitterBtn.target = "_blank";
                twitterBtn.innerHTML = '<i class="fab fa-twitter fa-2x text-info"></i>';
                twitterBtn.className = 'me-3';
                socialButtons.appendChild(twitterBtn);
            }
        });
    }
    
    // Facebook
    if (person.facebook && person.facebook.length > 0) {
        hasSocialMedia = true;
        person.facebook.forEach(profile => {
            if (profile && profile.trim() !== '') {
                const facebookBtn = document.createElement('a');
                facebookBtn.href = ensureHttps(profile);
                facebookBtn.target = "_blank";
                facebookBtn.innerHTML = '<i class="fab fa-facebook fa-2x text-primary"></i>';
                facebookBtn.className = 'me-3';
                socialButtons.appendChild(facebookBtn);
            }
        });
    }
    
    // Instagram
    if (person.instagram && person.instagram.length > 0) {
        hasSocialMedia = true;
        person.instagram.forEach(profile => {
            if (profile && profile.trim() !== '') {
                const instagramBtn = document.createElement('a');
                instagramBtn.href = ensureHttps(ensureInstagramUrl(profile));
                instagramBtn.target = "_blank";
                instagramBtn.innerHTML = '<i class="fab fa-instagram fa-2x text-danger"></i>';
                instagramBtn.className = 'me-3';
                socialButtons.appendChild(instagramBtn);
            }
        });
    }
    
    // Show/hide social media section based on if any field is populated
    document.getElementById('social-links-section').style.display = hasSocialMedia ? 'block' : 'none';
    
    // Populate edit form fields
    const editNamesContainer = document.getElementById('edit-names-container');
    editNamesContainer.innerHTML = '';
    if (person.names && person.names.length > 0) {
        person.names.forEach((name, index) => {
            addNameField(editNamesContainer, name, index > 0);
        });
    } else {
        addNameField(editNamesContainer, {}, false);
    }
    
    // Populate date of birth fields
    const birthDatesContainer = document.getElementById('edit-birth-dates-container');
    birthDatesContainer.innerHTML = '';
    if (person.dates_of_birth && person.dates_of_birth.length > 0) {
        person.dates_of_birth.forEach((dob, index) => {
            addField(birthDatesContainer, 'date_of_birth', dob, 'Date of Birth', 'date', index > 0);
        });
    } else {
        addField(birthDatesContainer, 'date_of_birth', '', 'Date of Birth', 'date', false);
    }
    
    // Populate email fields
    const emailsContainer = document.getElementById('edit-emails-container');
    emailsContainer.innerHTML = '';
    if (person.emails && person.emails.length > 0) {
        person.emails.forEach((email, index) => {
            addField(emailsContainer, 'email', email, 'Email Address', 'email', index > 0);
        });
    } else {
        addField(emailsContainer, 'email', '', 'Email Address', 'email', false);
    }
    
    // Populate LinkedIn fields
    const linkedinContainer = document.getElementById('edit-linkedin-container');
    linkedinContainer.innerHTML = '';
    if (person.linkedin && person.linkedin.length > 0) {
        person.linkedin.forEach((profile, index) => {
            addField(linkedinContainer, 'linkedin', profile, 'LinkedIn', 'text', index > 0, 'LinkedIn profile URL');
        });
    } else {
        addField(linkedinContainer, 'linkedin', '', 'LinkedIn', 'text', false, 'LinkedIn profile URL');
    }
    
    // Populate Twitter fields
    const twitterContainer = document.getElementById('edit-twitter-container');
    twitterContainer.innerHTML = '';
    if (person.twitter && person.twitter.length > 0) {
        person.twitter.forEach((profile, index) => {
            addField(twitterContainer, 'twitter', profile, 'Twitter', 'text', index > 0, 'Twitter handle or URL');
        });
    } else {
        addField(twitterContainer, 'twitter', '', 'Twitter', 'text', false, 'Twitter handle or URL');
    }
    
    // Populate Facebook fields
    const facebookContainer = document.getElementById('edit-facebook-container');
    facebookContainer.innerHTML = '';
    if (person.facebook && person.facebook.length > 0) {
        person.facebook.forEach((profile, index) => {
            addField(facebookContainer, 'facebook', profile, 'Facebook', 'text', index > 0, 'Facebook profile URL');
        });
    } else {
        addField(facebookContainer, 'facebook', '', 'Facebook', 'text', false, 'Facebook profile URL');
    }
    
    // Populate Instagram fields
    const instagramContainer = document.getElementById('edit-instagram-container');
    instagramContainer.innerHTML = '';
    if (person.instagram && person.instagram.length > 0) {
        person.instagram.forEach((profile, index) => {
            addField(instagramContainer, 'instagram', profile, 'Instagram', 'text', index > 0, 'Instagram handle or URL');
        });
    } else {
        addField(instagramContainer, 'instagram', '', 'Instagram', 'text', false, 'Instagram handle or URL');
    }
}

// Helper function to ensure URL has https://
function ensureHttps(url) {
    if (!url) return '#';
    if (url.startsWith('http://') || url.startsWith('https://')) {
        return url;
    }
    return 'https://' + url;
}

// Helper function to ensure Twitter URL
function ensureTwitterUrl(handle) {
    if (!handle) return '#';
    if (handle.includes('twitter.com') || handle.includes('x.com')) {
        return handle;
    }
    // Remove @ if present
    const cleanHandle = handle.startsWith('@') ? handle.substring(1) : handle;
    return 'https://twitter.com/' + cleanHandle;
}

// Helper function to ensure Instagram URL
function ensureInstagramUrl(handle) {
    if (!handle) return '#';
    if (handle.includes('instagram.com')) {
        return handle;
    }
    // Remove @ if present
    const cleanHandle = handle.startsWith('@') ? handle.substring(1) : handle;
    return 'https://instagram.com/' + cleanHandle;
}

// Function to add a name field to a container
function addNameField(container, name = { first_name: '', middle_name: '', last_name: '' }, showRemoveButton = true) {
    const wrapper = document.createElement('div');
    wrapper.className = 'name-group mb-3';
    
    const row = document.createElement('div');
    row.className = 'row';
    
    // First name
    const firstNameCol = document.createElement('div');
    firstNameCol.className = 'col-md-4';
    
    const firstNameLabel = document.createElement('label');
    firstNameLabel.className = 'form-label';
    firstNameLabel.textContent = 'First Name';
    
    const firstNameInput = document.createElement('input');
    firstNameInput.type = 'text';
    firstNameInput.className = 'form-control';
    firstNameInput.name = 'first_name';
    firstNameInput.value = name.first_name || '';
    firstNameInput.required = true;
    
    firstNameCol.appendChild(firstNameLabel);
    firstNameCol.appendChild(firstNameInput);
    
    // Middle name
    const middleNameCol = document.createElement('div');
    middleNameCol.className = 'col-md-4';
    
    const middleNameLabel = document.createElement('label');
    middleNameLabel.className = 'form-label';
    middleNameLabel.textContent = 'Middle Name';
    
    const middleNameInput = document.createElement('input');
    middleNameInput.type = 'text';
    middleNameInput.className = 'form-control';
    middleNameInput.name = 'middle_name';
    middleNameInput.value = name.middle_name || '';
    
    middleNameCol.appendChild(middleNameLabel);
    middleNameCol.appendChild(middleNameInput);
    
    // Last name
    const lastNameCol = document.createElement('div');
    lastNameCol.className = 'col-md-4';
    
    const lastNameLabel = document.createElement('label');
    lastNameLabel.className = 'form-label';
    lastNameLabel.textContent = 'Last Name';
    
    const lastNameInput = document.createElement('input');
    lastNameInput.type = 'text';
    lastNameInput.className = 'form-control';
    lastNameInput.name = 'last_name';
    lastNameInput.value = name.last_name || '';
    lastNameInput.required = true;
    
    lastNameCol.appendChild(lastNameLabel);
    lastNameCol.appendChild(lastNameInput);
    
    row.appendChild(firstNameCol);
    row.appendChild(middleNameCol);
    row.appendChild(lastNameCol);
    
    wrapper.appendChild(row);
    
    // Add remove button if needed
    if (showRemoveButton) {
        const removeRow = document.createElement('div');
        removeRow.className = 'row mt-2';
        
        const removeCol = document.createElement('div');
        removeCol.className = 'col-12 text-end';
        
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-sm btn-outline-danger';
        removeBtn.textContent = 'Remove Name';
        removeBtn.addEventListener('click', function() {
            container.removeChild(wrapper);
        });
        
        removeCol.appendChild(removeBtn);
        removeRow.appendChild(removeCol);
        wrapper.appendChild(removeRow);
    }
    
    container.appendChild(wrapper);
}

// Function to add a generic field to a container
function addField(container, name, value = '', label, type = 'text', showRemoveButton = true, placeholder = '') {
    const wrapper = document.createElement('div');
    wrapper.className = `${name}-group mb-3`;
    
    const labelElement = document.createElement('label');
    labelElement.className = 'form-label';
    labelElement.textContent = label;
    
    const inputGroup = document.createElement('div');
    inputGroup.className = 'input-group';
    
    const input = document.createElement('input');
    input.type = type;
    input.className = 'form-control';
    input.name = name;
    input.value = value;
    if (placeholder) {
        input.placeholder = placeholder;
    }
    
    inputGroup.appendChild(input);
    
    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn btn-outline-danger remove-btn';
    removeBtn.textContent = 'Remove';
    removeBtn.style.display = showRemoveButton ? 'block' : 'none';
    removeBtn.addEventListener('click', function() {
        container.removeChild(wrapper);
    });
    
    inputGroup.appendChild(removeBtn);
    
    wrapper.appendChild(labelElement);
    wrapper.appendChild(inputGroup);
    
    container.appendChild(wrapper);
}

// Setup event listeners for adding more fields
function setupAddButtons() {
    // Add buttons in the create form
    document.getElementById('add-name-btn').addEventListener('click', function() {
        addNameField(document.getElementById('names-container'), {}, true);
    });
    
    document.getElementById('add-birth-date-btn').addEventListener('click', function() {
        const container = document.getElementById('birth-dates-container');
        addField(container, 'date_of_birth', '', 'Date of Birth', 'date', true);
        container.querySelectorAll('.remove-btn').forEach(btn => btn.style.display = 'block');
    });
    
    document.getElementById('add-email-btn').addEventListener('click', function() {
        const container = document.getElementById('emails-container');
        addField(container, 'email', '', 'Email Address', 'email', true);
        container.querySelectorAll('.remove-btn').forEach(btn => btn.style.display = 'block');
    });
    
    document.getElementById('add-linkedin-btn').addEventListener('click', function() {
        const container = document.getElementById('linkedin-container');
        addField(container, 'linkedin', '', 'LinkedIn', 'text', true, 'LinkedIn profile URL');
        container.querySelectorAll('.remove-btn').forEach(btn => btn.style.display = 'block');
    });
    
    document.getElementById('add-twitter-btn').addEventListener('click', function() {
        const container = document.getElementById('twitter-container');
        addField(container, 'twitter', '', 'Twitter', 'text', true, 'Twitter handle or URL');
        container.querySelectorAll('.remove-btn').forEach(btn => btn.style.display = 'block');
    });
    
    document.getElementById('add-facebook-btn').addEventListener('click', function() {
        const container = document.getElementById('facebook-container');
        addField(container, 'facebook', '', 'Facebook', 'text', true, 'Facebook profile URL');
        container.querySelectorAll('.remove-btn').forEach(btn => btn.style.display = 'block');
    });
    
    document.getElementById('add-instagram-btn').addEventListener('click', function() {
        const container = document.getElementById('instagram-container');
        addField(container, 'instagram', '', 'Instagram', 'text', true, 'Instagram handle or URL');
        container.querySelectorAll('.remove-btn').forEach(btn => btn.style.display = 'block');
    });
    
    // Add buttons in the edit form
    document.getElementById('edit-add-name-btn').addEventListener('click', function() {
        addNameField(document.getElementById('edit-names-container'), {}, true);
    });
    
    document.getElementById('edit-add-birth-date-btn').addEventListener('click', function() {
        const container = document.getElementById('edit-birth-dates-container');
        addField(container, 'date_of_birth', '', 'Date of Birth', 'date', true);
    });
    
    document.getElementById('edit-add-email-btn').addEventListener('click', function() {
        const container = document.getElementById('edit-emails-container');
        addField(container, 'email', '', 'Email Address', 'email', true);
    });
    
    document.getElementById('edit-add-linkedin-btn').addEventListener('click', function() {
        const container = document.getElementById('edit-linkedin-container');
        addField(container, 'linkedin', '', 'LinkedIn', 'text', true, 'LinkedIn profile URL');
    });
    
    document.getElementById('edit-add-twitter-btn').addEventListener('click', function() {
        const container = document.getElementById('edit-twitter-container');
        addField(container, 'twitter', '', 'Twitter', 'text', true, 'Twitter handle or URL');
    });
    
    document.getElementById('edit-add-facebook-btn').addEventListener('click', function() {
        const container = document.getElementById('edit-facebook-container');
        addField(container, 'facebook', '', 'Facebook', 'text', true, 'Facebook profile URL');
    });
    
    document.getElementById('edit-add-instagram-btn').addEventListener('click', function() {
        const container = document.getElementById('edit-instagram-container');
        addField(container, 'instagram', '', 'Instagram', 'text', true, 'Instagram handle or URL');
    });
}

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

// Edit person button
document.getElementById('edit-person-btn').addEventListener('click', function() {
    document.getElementById('profile-view').style.display = 'none';
    document.getElementById('profile-edit').style.display = 'block';
});

// Cancel edit
document.getElementById('cancel-edit').addEventListener('click', function() {
    document.getElementById('profile-view').style.display = 'block';
    document.getElementById('profile-edit').style.display = 'none';
});

// Edit form submission
document.getElementById('edit-person-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData();
    
    // Collect all name fields
    const firstNames = document.querySelectorAll('#edit-names-container input[name="first_name"]');
    const middleNames = document.querySelectorAll('#edit-names-container input[name="middle_name"]');
    const lastNames = document.querySelectorAll('#edit-names-container input[name="last_name"]');
    
    firstNames.forEach(input => formData.append('first_name', input.value));
    middleNames.forEach(input => formData.append('middle_name', input.value));
    lastNames.forEach(input => formData.append('last_name', input.value));
    
    // Collect all other fields
    const collectFields = (selector, name) => {
        document.querySelectorAll(selector).forEach(input => {
            formData.append(name, input.value);
        });
    };
    
    collectFields('#edit-birth-dates-container input[name="date_of_birth"]', 'date_of_birth');
    collectFields('#edit-emails-container input[name="email"]', 'email');
    collectFields('#edit-linkedin-container input[name="linkedin"]', 'linkedin');
    collectFields('#edit-twitter-container input[name="twitter"]', 'twitter');
    collectFields('#edit-facebook-container input[name="facebook"]', 'facebook');
    collectFields('#edit-instagram-container input[name="instagram"]', 'instagram');
    
    fetch(`/update_person/${selectedPersonId}`, {
        method: 'POST',
        body: formData
    }).then(() => {
        window.location.reload();
    });
});

// Delete person button
document.getElementById('delete-person-btn').addEventListener('click', function() {
    if (confirm('Are you sure you want to delete this person?')) {
        fetch(`/delete_person/${selectedPersonId}`, {
            method: 'POST'
        }).then(() => {
            window.location.reload();
        });
    }
});

// Search functionality
document.getElementById('search-input').addEventListener('input', function(e) {
    const searchTerm = e.target.value.toLowerCase();
    const personList = document.getElementById('person-list');
    personList.innerHTML = '';
    
    people.forEach((person, index) => {
        // Check if any of the person's data contains the search term
        let matches = false;
        
        // Check names
        if (person.names) {
            for (const name of person.names) {
                const fullName = `${name.first_name || ''} ${name.middle_name || ''} ${name.last_name || ''}`.toLowerCase();
                if (fullName.includes(searchTerm)) {
                    matches = true;
                    break;
                }
            }
        }
        
        // Check emails
        if (!matches && person.emails) {
            for (const email of person.emails) {
                if (email.toLowerCase().includes(searchTerm)) {
                    matches = true;
                    break;
                }
            }
        }
        
        // Check social media
        const socialFields = ['linkedin', 'twitter', 'facebook', 'instagram'];
        for (const field of socialFields) {
            if (!matches && person[field]) {
                for (const profile of person[field]) {
                    if (profile.toLowerCase().includes(searchTerm)) {
                        matches = true;
                        break;
                    }
                }
            }
        }
        
        // Check dates of birth
        if (!matches && person.dates_of_birth) {
            for (const dob of person.dates_of_birth) {
                if (dob.includes(searchTerm)) {
                    matches = true;
                    break;
                }
            }
        }
        
        if (matches) {
            const primaryName = person.names && person.names.length > 0 ? person.names[0] : { first_name: '', last_name: '' };
            const displayName = `${primaryName.first_name} ${primaryName.last_name}`.trim() || 'Unnamed Person';
            
            const li = document.createElement('li');
            li.className = 'person-item' + (index === selectedPersonId ? ' active' : '');
            li.textContent = displayName;
            li.addEventListener('click', () => selectPerson(index));
            personList.appendChild(li);
        }
    });
});

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    fetchPeople();
    setupAddButtons();
});