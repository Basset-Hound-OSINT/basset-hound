// ui-form-handlers.js - Handles form field generation and management

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

// Function to collect form data for submission
function collectFormData(formId) {
    const formData = new FormData();
    
    // Collect name fields
    const firstNames = document.querySelectorAll(`${formId} input[name="first_name"]`);
    const middleNames = document.querySelectorAll(`${formId} input[name="middle_name"]`);
    const lastNames = document.querySelectorAll(`${formId} input[name="last_name"]`);
    
    firstNames.forEach(input => formData.append('first_name', input.value));
    middleNames.forEach(input => formData.append('middle_name', input.value));
    lastNames.forEach(input => formData.append('last_name', input.value));
    
    // Collect all other fields
    const fieldTypes = [
        { selector: `${formId} input[name="date_of_birth"]`, name: 'date_of_birth' },
        { selector: `${formId} input[name="email"]`, name: 'email' },
        { selector: `${formId} input[name="linkedin"]`, name: 'linkedin' },
        { selector: `${formId} input[name="twitter"]`, name: 'twitter' },
        { selector: `${formId} input[name="facebook"]`, name: 'facebook' },
        { selector: `${formId} input[name="instagram"]`, name: 'instagram' }
    ];
    
    fieldTypes.forEach(field => {
        document.querySelectorAll(field.selector).forEach(input => {
            formData.append(field.name, input.value);
        });
    });
    
    return formData;
}

export { addNameField, addField, setupAddButtons, collectFormData };