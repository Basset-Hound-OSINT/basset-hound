import { createInputElement, getSectionById } from './utils.js';
import { updatePerson } from './api.js';
import { renderPersonDetails } from './ui-person-details.js';
import { renderPeopleList } from './ui-people-list.js';

// Function to setup add buttons for form fields
export function setupAddButtons() {
    // Set up section add buttons
    document.querySelectorAll('.add-section-field').forEach(button => {
        button.addEventListener('click', function() {
            const sectionId = this.getAttribute('data-section');
            const fieldId = this.getAttribute('data-field');
            const container = document.getElementById(`${sectionId}-${fieldId}-container`);
            const index = container.querySelectorAll('.field-instance').length;
            
            // Get field configuration
            const config = window.appConfig;
            const section = getSectionById(config, sectionId);
            const field = section.fields.find(f => f.id === fieldId);
            
            addFieldInstance(container, sectionId, field, index);
        });
    });
}

// Function to add a new instance of a field
function addFieldInstance(container, sectionId, field, index) {
    const fieldId = field.id;
    const fieldInstance = document.createElement('div');
    fieldInstance.className = 'field-instance mb-3';
    fieldInstance.dataset.index = index;
    
    const fieldHeader = document.createElement('div');
    fieldHeader.className = 'd-flex justify-content-between align-items-center mb-2';
    
    const fieldTitle = document.createElement('h6');
    fieldTitle.textContent = field.name || fieldId;
    fieldHeader.appendChild(fieldTitle);
    
    // Add remove button for multiple instances
    if (field.multiple && index > 0) {
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-sm btn-outline-danger remove-field';
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.addEventListener('click', function() {
            fieldInstance.remove();
        });
        fieldHeader.appendChild(removeBtn);
    }
    
    fieldInstance.appendChild(fieldHeader);
    
    // Handle field with components
    if (field.components) {
        field.components.forEach(component => {
            const componentGroup = document.createElement('div');
            componentGroup.className = 'mb-2';
            
            const componentLabel = document.createElement('label');
            componentLabel.className = 'form-label';
            componentLabel.textContent = component.name || component.id;
            componentGroup.appendChild(componentLabel);
            
            const componentInput = createInputElement(
                component, 
                `${sectionId}.${fieldId}.${component.id}_${index}`, 
                ''
            );
            componentGroup.appendChild(componentInput);
            
            fieldInstance.appendChild(componentGroup);
        });
    } else {
        // Simple field without components
        const input = createInputElement(
            field, 
            `${sectionId}.${fieldId}_${index}`, 
            ''
        );
        fieldInstance.appendChild(input);
    }
    
    container.appendChild(fieldInstance);
}

// Function to create form for adding/editing people
export function createPersonForm(container, config, person = null) {
    container.innerHTML = ''; // Clear existing content
    
    // Create a form
    const form = document.createElement('form');
    form.id = person ? 'edit-person-form' : 'add-person-form';
    form.className = 'needs-validation';
    form.noValidate = true;
    
    // For each section in the config
    config.sections.forEach(section => {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'card mb-4';
        
        const sectionHeader = document.createElement('div');
        sectionHeader.className = 'card-header';
        sectionHeader.innerHTML = `<h5>${section.name}</h5>`;
        sectionDiv.appendChild(sectionHeader);
        
        const sectionBody = document.createElement('div');
        sectionBody.className = 'card-body';
        
        // For each field in the section
        section.fields.forEach(field => {
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'mb-3';
            
            const fieldLabel = document.createElement('label');
            fieldLabel.className = 'form-label';
            fieldLabel.textContent = field.name || field.id;
            fieldDiv.appendChild(fieldLabel);
            
            // Container for field instances
            const instancesContainer = document.createElement('div');
            instancesContainer.id = `${section.id}-${field.id}-container`;
            instancesContainer.className = 'field-instances';
            
            // If editing a person, load existing data
            if (person && person.profile && person.profile[section.id] && person.profile[section.id][field.id]) {
                const fieldData = person.profile[section.id][field.id];
                
                if (Array.isArray(fieldData)) {
                    // Multiple values
                    fieldData.forEach((value, index) => {
                        createFieldWithValue(instancesContainer, section.id, field, value, index);
                    });
                } else {
                    // Single value
                    createFieldWithValue(instancesContainer, section.id, field, fieldData, 0);
                }
            } else {
                // Add empty field instance for new person
                addFieldInstance(instancesContainer, section.id, field, 0);
            }
            
            fieldDiv.appendChild(instancesContainer);
            
            // Add button for multiple fields
            if (field.multiple) {
                const addButton = document.createElement('button');
                addButton.type = 'button';
                addButton.className = 'btn btn-sm btn-outline-primary add-section-field mt-2';
                addButton.dataset.section = section.id;
                addButton.dataset.field = field.id;
                addButton.innerHTML = '<i class="fas fa-plus"></i> Add Another';
                fieldDiv.appendChild(addButton);
            }
            
            sectionBody.appendChild(fieldDiv);
        });
        
        sectionDiv.appendChild(sectionBody);
        form.appendChild(sectionDiv);
    });
    
    // Add save/cancel buttons
    const actionButtons = document.createElement('div');
    actionButtons.className = 'd-flex justify-content-between mb-4';
    
    const cancelButton = document.createElement('button');
    cancelButton.type = 'button';
    cancelButton.className = 'btn btn-secondary';
    cancelButton.textContent = 'Cancel';
    cancelButton.id = person ? 'cancel-edit' : 'cancel-add';
    
    const saveButton = document.createElement('button');
    saveButton.type = 'submit';
    saveButton.className = 'btn btn-primary';
    saveButton.textContent = person ? 'Update Person' : 'Add Person';
    
    actionButtons.appendChild(cancelButton);
    actionButtons.appendChild(saveButton);
    form.appendChild(actionButtons);
    
    container.appendChild(form);
    
    // Add event listeners for form buttons
    if (person) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = collectFormData(form);
            await updatePersonData(person.id, formData);
        });
        
        document.getElementById('cancel-edit').addEventListener('click', function() {
            // Return to person details view
            document.getElementById('person-form-container').style.display = 'none';
            document.getElementById('person-details').style.display = 'block';
        });
    } else {
        // Form event listeners for adding new person are already in place
    }
    
    // Setup add buttons for multiple fields
    setupAddButtons();
}

// Function to create a field with existing value
function createFieldWithValue(container, sectionId, field, value, index) {
    const fieldId = field.id;
    const fieldInstance = document.createElement('div');
    fieldInstance.className = 'field-instance mb-3';
    fieldInstance.dataset.index = index;
    
    const fieldHeader = document.createElement('div');
    fieldHeader.className = 'd-flex justify-content-between align-items-center mb-2';
    
    const fieldTitle = document.createElement('h6');
    fieldTitle.textContent = field.name || fieldId;
    fieldHeader.appendChild(fieldTitle);
    
    // Add remove button for multiple instances
    if (field.multiple && index > 0) {
        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'btn btn-sm btn-outline-danger remove-field';
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.addEventListener('click', function() {
            fieldInstance.remove();
        });
        fieldHeader.appendChild(removeBtn);
    }
    
    fieldInstance.appendChild(fieldHeader);
    
    // Handle field with components
    if (field.components) {
        field.components.forEach(component => {
            const componentGroup = document.createElement('div');
            componentGroup.className = 'mb-2';
            
            const componentLabel = document.createElement('label');
            componentLabel.className = 'form-label';
            componentLabel.textContent = component.name || component.id;
            componentGroup.appendChild(componentLabel);
            
            const componentValue = value && value[component.id] ? value[component.id] : '';
            const componentInput = createInputElement(
                component, 
                `${sectionId}.${fieldId}.${component.id}_${index}`, 
                componentValue
            );
            componentGroup.appendChild(componentInput);
            
            fieldInstance.appendChild(componentGroup);
        });
    } else {
        // Simple field without components
        const input = createInputElement(
            field, 
            `${sectionId}.${fieldId}_${index}`, 
            value
        );
        fieldInstance.appendChild(input);
    }
    
    container.appendChild(fieldInstance);
}

// Function to collect form data and organize it according to the configuration
export function collectFormData(form) {
    if (typeof form === 'string') {
        form = document.querySelector(form);
    }
    const formData = new FormData(form);
    const config = window.appConfig;
    const result = {
        profile: {}
    };
    
    // Initialize sections
    config.sections.forEach(section => {
        result.profile[section.id] = {};
    });
    
    // Process each form field
    for (const [key, value] of formData.entries()) {
        if (!value.trim()) continue; // Skip empty values
        
        const parts = key.split('.');
        if (parts.length < 2) continue;
        
        const sectionId = parts[0];
        let fieldId = parts[1];
        
        // Handle field index for multiple values
        let index = 0;
        if (fieldId.includes('_')) {
            const fieldParts = fieldId.split('_');
            fieldId = fieldParts[0];
            index = parseInt(fieldParts[1]);
        }
        
        // Initialize field if not exists
        if (!result.profile[sectionId][fieldId]) {
            const section = getSectionById(config, sectionId);
            const field = section.fields.find(f => f.id === fieldId);
            
            if (field.multiple) {
                result.profile[sectionId][fieldId] = [];
            } else {
                result.profile[sectionId][fieldId] = field.components ? {} : '';
            }
        }
        
        // Handle components
        if (parts.length === 3) {
            const componentParts = parts[2].split('_');
            const componentId = componentParts[0];
            
            // Get the section and field definitions
            const section = getSectionById(config, sectionId);
            const field = section.fields.find(f => f.id === fieldId);
            
            if (field.multiple) {
                // Ensure index exists
                while (result.profile[sectionId][fieldId].length <= index) {
                    result.profile[sectionId][fieldId].push({});
                }
                result.profile[sectionId][fieldId][index][componentId] = value;
            } else {
                result.profile[sectionId][fieldId][componentId] = value;
            }
        } else {
            // Simple field
            const section = getSectionById(config, sectionId);
            const field = section.fields.find(f => f.id === fieldId);
            
            if (field.multiple) {
                // Ensure index exists
                while (result.profile[sectionId][fieldId].length <= index) {
                    result.profile[sectionId][fieldId].push('');
                }
                result.profile[sectionId][fieldId][index] = value;
            } else {
                result.profile[sectionId][fieldId] = value;
            }
        }
    }
    
    return result;
}

// Function to update person data via API
async function updatePersonData(personId, data) {
    try {
        const response = await fetch(`/update_person/${personId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const result = await response.json();
            // Refresh the page to show updated data
            window.location.reload();
            return result;
        } else {
            throw new Error('Failed to update person');
        }
    } catch (error) {
        console.error('Error updating person:', error);
        alert('Failed to update person. Please try again.');
    }
}

export function editPerson(personId) {
    console.log("Editing person:", personId);

    const personDetails = document.getElementById('person-details');
    const profileEdit = document.getElementById('profile-edit');
    const form = document.getElementById('edit-person-form');

    form.classList.remove('was-validated');

    if (!personDetails || !profileEdit || !form) return;

    personDetails.style.display = 'none';
    profileEdit.classList.remove('d-none');
    profileEdit.style.display = 'block';

    const person = window.selectedPerson = window.people.find(p => p.id === personId);
    window.selectedPersonId = personId;
    const profile = person.profile || {};
    const config = window.appConfig;

    form.innerHTML = '';

    for (const section of config.sections) {
        const sectionData = profile[section.id] || {};
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'mb-4';

        const sectionHeader = document.createElement('h5');
        sectionHeader.textContent = section.name || section.id;
        sectionDiv.appendChild(sectionHeader);

        for (const field of section.fields) {
            const fieldValues = sectionData[field.id] || [];
            const values = Array.isArray(fieldValues) ? fieldValues : [fieldValues];

            // Render at least one input, even if no values exist
            const maxEntries = field.multiple ? Math.max(values.length, 1) : 1;

            for (let index = 0; index < maxEntries; index++) {
                const val = values[index] || {};

                if (field.components) {
                    const groupDiv = document.createElement('div');
                    groupDiv.className = 'mb-3';
                    groupDiv.setAttribute('data-field', field.id);

                    if (field.components) {
                        const groupTitle = document.createElement('h6');
                        groupTitle.textContent = `${field.name || field.id} #${index + 1}`;
                        groupDiv.appendChild(groupTitle);

                        field.components.forEach(component => {
                            const name = `${section.id}.${field.id}.${component.id}_${index}`;

                            // Try to read value from `val` using known fallback keys
                            const fallbackKeys = [
                                component.id,
                                component.id.replace('_name', ''),
                                component.id.replace('name', ''),
                                component.id.replace('_', ''),
                            ];
                            const value = fallbackKeys.reduce((acc, key) => acc || val[key], '');

                            // Create a label element for the input
                            const label = document.createElement('label');
                            label.className = 'form-label';
                            label.textContent = component.name || component.id;
                            label.setAttribute('for', name); // optional, good for accessibility

                            // Create the input element
                            const inputGroup = createInputElement(field, name, value, component);

                            // Append label and input to group
                            groupDiv.appendChild(label);
                            groupDiv.appendChild(inputGroup);
                        });


                    } else {
                        const groupTitle = document.createElement('h6');
                        groupTitle.textContent = `${field.name || field.id} #${index + 1}`;
                        groupDiv.appendChild(groupTitle);

                        const name = `${section.id}.${field.id}_${index}`;
                        const inputGroup = createInputElement(field, name, '');
                        groupDiv.appendChild(inputGroup);
                    }

                    sectionDiv.appendChild(groupDiv);

                } else {
                    const groupDiv = document.createElement('div');
                    groupDiv.className = 'mb-3';
                    groupDiv.setAttribute('data-field', field.id);

                    const groupTitle = document.createElement('h6');
                    groupTitle.textContent = `${field.name || field.id} #${index + 1}`;
                    groupDiv.appendChild(groupTitle);

                    const name = `${section.id}.${field.id}_${index}`;
                    const value = values[index] || '';
                    const inputGroup = createInputElement(field, name, value);
                    groupDiv.appendChild(inputGroup);

                    sectionDiv.appendChild(groupDiv);
                }
            }

            // Add "Add Another" button if field supports multiple values
            if (field.multiple) {
                const addBtn = document.createElement('button');
                addBtn.className = 'btn btn-sm btn-outline-primary mt-2';
                addBtn.type = 'button';
                addBtn.innerHTML = `<i class="fas fa-plus"></i> Add Another`;

                addBtn.addEventListener('click', () => {
                    // Calculate correct index based on existing input groups
                    const currentGroups = sectionDiv.querySelectorAll(`div[data-field="${field.id}"]`);
                    const index = currentGroups.length;

                    const groupDiv = document.createElement('div');
                    groupDiv.className = 'mb-3';
                    groupDiv.setAttribute('data-field', field.id);

                    const groupTitle = document.createElement('h6');
                    groupTitle.textContent = `${field.name || field.id} #${index + 1}`;
                    groupDiv.appendChild(groupTitle);

                    if (field.components) {
                        field.components.forEach(component => {
                            const name = `${section.id}.${field.id}.${component.id}_${index}`;

                            const wrapper = document.createElement('div');
                            wrapper.className = 'mb-2';

                            const label = document.createElement('label');
                            label.textContent = component.name || component.id;
                            label.classList.add('form-label');

                            const inputGroup = createInputElement(field, name, '', component);

                            wrapper.appendChild(label);
                            wrapper.appendChild(inputGroup);
                            groupDiv.appendChild(wrapper);
                        });
                    } else {
                        const name = `${section.id}.${field.id}_${index}`;
                        const inputGroup = createInputElement(field, name, '');
                        groupDiv.appendChild(inputGroup);
                    }

                    sectionDiv.insertBefore(groupDiv, addBtn);
                });



                sectionDiv.appendChild(addBtn);
            }
        }


        form.appendChild(sectionDiv);
    }

    const cancelBtn = document.getElementById('cancel-edit');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            // Hide edit form and show profile
            document.getElementById('profile-edit').style.display = 'none';
            document.getElementById('person-details').style.display = 'block';
        });
    }

}


export function deletePerson(personId) {
  fetch(`/delete_person/${personId}`, { method: 'POST' })
    .then(() => window.location.reload())
    .catch(err => console.error("Failed to delete person", err));
}


document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('edit-person-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(form);  // ✅ Fixed here
    const params = new URLSearchParams(formData);

    try {
        const response = await fetch(`/update_person/${window.selectedPersonId}`, {
        method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: params
        });

        if (!response.ok) throw new Error('Failed to update person');

        // ✅ Refresh view
        const updatedPerson = await fetch(`/get_person/${window.selectedPersonId}`).then(r => r.json());
        renderPersonDetails(document.getElementById('person-details'), updatedPerson);

        const people = await fetch('/get_people').then(r => r.json());
        window.people = people;

        // Re-render the sidebar list
        renderPeopleList(people, window.selectedPersonId);

        document.getElementById('profile-edit').style.display = 'none';
        document.getElementById('person-details').style.display = 'block';

    } catch (err) {
      console.error("[ERROR] Failed to update person", err);
    }
  });
});
