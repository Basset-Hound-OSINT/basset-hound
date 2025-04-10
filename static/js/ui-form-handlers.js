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
export function addFieldInstance(container, sectionId, field, index) {
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
            
            // Create the component input
            if (component.multiple) {
                // Create a container for multiple values of this component
                const componentContainer = document.createElement('div');
                componentContainer.className = 'component-container';
                componentContainer.id = `${sectionId}-${fieldId}-${component.id}-container-${index}`;
                
                // Add the first component input
                const componentInputGroup = document.createElement('div');
                componentInputGroup.className = 'input-group mb-2';
                
                const componentInput = createInputElement(
                    component, 
                    `${sectionId}.${fieldId}.${component.id}_${index}.0`, 
                    ''
                );
                componentInput.classList.add('form-control');
                componentInputGroup.appendChild(componentInput);
                
                // Add button to add more of this component
                const addComponentBtn = document.createElement('button');
                addComponentBtn.type = 'button';
                addComponentBtn.className = 'btn btn-outline-secondary';
                addComponentBtn.innerHTML = '<i class="fas fa-plus"></i>';
                addComponentBtn.title = `Add another ${component.name || component.id}`;
                addComponentBtn.addEventListener('click', function() {
                    const compInputs = componentContainer.querySelectorAll('.input-group');
                    const compIndex = compInputs.length;
                    
                    const newComponentGroup = document.createElement('div');
                    newComponentGroup.className = 'input-group mb-2';
                    
                    const newInput = createInputElement(
                        component, 
                        `${sectionId}.${fieldId}.${component.id}_${index}.${compIndex}`, 
                        ''
                    );
                    newInput.classList.add('form-control');
                    newComponentGroup.appendChild(newInput);
                    
                    // Add remove button for this component value
                    const removeCompBtn = document.createElement('button');
                    removeCompBtn.type = 'button';
                    removeCompBtn.className = 'btn btn-outline-danger';
                    removeCompBtn.innerHTML = '<i class="fas fa-times"></i>';
                    removeCompBtn.addEventListener('click', function() {
                        newComponentGroup.remove();
                    });
                    newComponentGroup.appendChild(removeCompBtn);
                    
                    componentContainer.appendChild(newComponentGroup);
                });
                
                componentInputGroup.appendChild(addComponentBtn);
                componentContainer.appendChild(componentInputGroup);
                componentGroup.appendChild(componentContainer);
            } else {
                // Single component value
                const componentInput = createInputElement(
                    component, 
                    `${sectionId}.${fieldId}.${component.id}_${index}`, 
                    ''
                );
                componentGroup.appendChild(componentInput);
            }
            
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

export function createPersonForm(container, config, person = null) {
    container.innerHTML = '';

    const form = document.createElement('form');
    form.id = 'person-form';
    form.className = 'needs-validation';
    form.noValidate = true;
    form.enctype = 'multipart/form-data';

    config.sections.forEach(section => {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'card mb-4';

        const sectionHeader = document.createElement('div');
        sectionHeader.className = 'card-header';
        sectionHeader.innerHTML = `<h5>${section.name}</h5>`;
        sectionDiv.appendChild(sectionHeader);

        const sectionBody = document.createElement('div');
        sectionBody.className = 'card-body';

        section.fields.forEach(field => {
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'mb-3';

            const fieldLabel = document.createElement('label');
            fieldLabel.className = 'form-label';
            fieldLabel.textContent = field.name || field.id;
            fieldDiv.appendChild(fieldLabel);

            const containerDiv = document.createElement('div');
            containerDiv.id = `${section.id}-${field.id}-container`;
            containerDiv.className = 'field-instances';

            const values = person?.profile?.[section.id]?.[field.id];
            const entries = Array.isArray(values) ? values : values ? [values] : [null];

            const entryCount = field.multiple ? Math.max(entries.length, 1) : 1;

            for (let index = 0; index < entryCount; index++) {
                const entry = entries[index] || {};
                const groupDiv = document.createElement('div');
                groupDiv.className = 'mb-3 field-instance';
                groupDiv.setAttribute('data-field', field.id);

                if (field.components) {
                    const groupTitle = document.createElement('h6');
                    groupTitle.textContent = `${field.name || field.id} #${index + 1}`;
                    groupDiv.appendChild(groupTitle);

                    field.components.forEach(component => {
                        const compWrapper = document.createElement('div');
                        compWrapper.className = 'mb-2';

                        const label = document.createElement('label');
                        label.className = 'form-label';
                        label.textContent = component.name || component.id;
                        compWrapper.appendChild(label);

                        if (component.multiple) {
                            const compContainer = document.createElement('div');
                            compContainer.className = 'component-container';
                            compContainer.id = `${section.id}-${field.id}-${component.id}-container-${index}`;

                            const compValues = entry?.[component.id]
                                ? (Array.isArray(entry[component.id]) ? entry[component.id] : [entry[component.id]])
                                : [''];

                            compValues.forEach((compValue, compIndex) => {
                                const inputGroup = document.createElement('div');
                                inputGroup.className = 'input-group mb-2';

                                const inputName = `${section.id}.${field.id}.${component.id}_${index}.${compIndex}`;
                                const input = createInputElement(component, inputName, compValue, null, section.id);
                                input.classList.add('form-control');
                                inputGroup.appendChild(input);

                                if (compIndex === 0) {
                                    const addBtn = document.createElement('button');
                                    addBtn.type = 'button';
                                    addBtn.className = 'btn btn-outline-secondary';
                                    addBtn.innerHTML = '<i class="fas fa-plus"></i>';
                                    addBtn.addEventListener('click', function () {
                                        const newIndex = compContainer.querySelectorAll('.input-group').length;
                                        const newInputGroup = document.createElement('div');
                                        newInputGroup.className = 'input-group mb-2';

                                        const newName = `${section.id}.${field.id}.${component.id}_${index}.${newIndex}`;
                                        const newInput = createInputElement(component, newName, '', null, section.id);
                                        newInput.classList.add('form-control');
                                        newInputGroup.appendChild(newInput);

                                        const removeBtn = document.createElement('button');
                                        removeBtn.type = 'button';
                                        removeBtn.className = 'btn btn-outline-danger';
                                        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
                                        removeBtn.addEventListener('click', () => newInputGroup.remove());
                                        newInputGroup.appendChild(removeBtn);

                                        compContainer.appendChild(newInputGroup);
                                    });

                                    inputGroup.appendChild(addBtn);
                                } else {
                                    const removeBtn = document.createElement('button');
                                    removeBtn.type = 'button';
                                    removeBtn.className = 'btn btn-outline-danger';
                                    removeBtn.innerHTML = '<i class="fas fa-times"></i>';
                                    removeBtn.addEventListener('click', () => inputGroup.remove());
                                    inputGroup.appendChild(removeBtn);
                                }

                                compContainer.appendChild(inputGroup);
                            });

                            compWrapper.appendChild(compContainer);
                        } else {
                            const baseName = `${section.id}.${field.id}.${component.id}_${index}`;
                            const compValue = entry?.[component.id] || '';
                            const input = createInputElement(component, baseName, compValue, null, section.id);
                            compWrapper.appendChild(input);
                        }

                        groupDiv.appendChild(compWrapper);
                    });
                } else {
                    const name = `${section.id}.${field.id}_${index}`;
                    const value = entry || '';
                    const inputGroup = createInputElement(field, name, value, null, section.id);
                    groupDiv.appendChild(inputGroup);
                }

                containerDiv.appendChild(groupDiv);
            }

            fieldDiv.appendChild(containerDiv);

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

    // Action Buttons
    const actionButtons = document.createElement('div');
    actionButtons.className = 'd-flex justify-content-between mb-4';

    const cancelButton = document.createElement('button');
    cancelButton.type = 'button';
    cancelButton.className = 'btn btn-secondary';
    cancelButton.textContent = 'Cancel';
    cancelButton.id = 'cancel-form';

    const saveButton = document.createElement('button');
    saveButton.type = 'submit';
    saveButton.className = 'btn btn-primary';
    saveButton.textContent = person ? 'Update Person' : 'Add Person';

    actionButtons.appendChild(cancelButton);
    actionButtons.appendChild(saveButton);
    form.appendChild(actionButtons);

    // Append form to container
    container.appendChild(form);

    // Show/hide relevant UI sections
    document.getElementById('person-form-container').style.display = 'block';
    document.getElementById('person-details').style.display = 'none';

    // Set up event handling
    if (person) {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();
            await updatePersonData(person.id, e.target);
        });
    } else {
        form.addEventListener('submit', async function (e) {
            e.preventDefault();

            if (!form.checkValidity()) {
                form.classList.add('was-validated');
                return;
            }

            const formData = new FormData(form);

            try {
                const response = await fetch('/add_person', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(errorText);
                }

                window.location.reload();

            } catch (error) {
                console.error('[ERROR] Failed to add person', error);
                alert('Failed to add person. Please try again.');
            }
        });
    }

    cancelButton.addEventListener('click', function () {
        document.getElementById('person-form-container').style.display = 'none';
        document.getElementById('person-details').style.display = 'block';
    });

    setupAddButtons();
}

// Function to create a field with existing value
export function createFieldWithValue(container, sectionId, field, value, index) {
    const fieldId = field.id;
    const fieldInstance = document.createElement('div');
    fieldInstance.className = 'field-instance mb-3';
    fieldInstance.dataset.index = index;
    
    const fieldHeader = document.createElement('div');
    fieldHeader.className = 'd-flex justify-content-between align-items-center mb-2';
    
    const fieldTitle = document.createElement('h6');
    fieldTitle.textContent = field.name || fieldId;
    fieldHeader.appendChild(fieldTitle);

    if (field.type === 'file') {
        const files = value ? (Array.isArray(value) ? value : [value]) : [];

        const fileList = document.createElement('div');
        fileList.className = 'mb-2 file-list';

        files.forEach((file, i) => {
            const fileEntry = document.createElement('div');
            fileEntry.className = 'mb-2';

            // 🔹 File download link
            const fileLink = document.createElement('a');
            fileLink.href = `/files/${window.selectedPersonId}/${file.path}`;
            fileLink.textContent = file.name;
            fileLink.target = '_blank';
            fileLink.className = 'me-3';
            fileEntry.appendChild(fileLink);

            // 🔹 Textarea for existing comment
            const commentInput = document.createElement('textarea');
            commentInput.name = `${sectionId}.${fieldId}.comment_${i}`;
            commentInput.className = 'form-control mt-1';
            commentInput.placeholder = 'Comment about this file...';
            commentInput.value = file.comment || '';
            fileEntry.appendChild(commentInput);

            fileList.appendChild(fileEntry);
        });

        if (files.length) {
            fieldInstance.appendChild(fileList);
        }

        // 🔹 New file input
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.name = `${sectionId}.${fieldId}_${index}`;
        fileInput.className = 'form-control';
        if (field.multiple) {
            fileInput.multiple = true;
        }
        fieldInstance.appendChild(fileInput);

        container.appendChild(fieldInstance);
        return;
    }

    
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
            
            if (component.multiple) {
                // Create a container for multiple values of this component
                const componentContainer = document.createElement('div');
                componentContainer.className = 'component-container';
                componentContainer.id = `${sectionId}-${fieldId}-${component.id}-container-${index}`;
                
                // Get component values (ensure it's an array)
                const componentValues = value && value[component.id] 
                    ? (Array.isArray(value[component.id]) ? value[component.id] : [value[component.id]])
                    : [''];
                
                // Create an input group for each value
                componentValues.forEach((compValue, compIndex) => {
                    const componentInputGroup = document.createElement('div');
                    componentInputGroup.className = 'input-group mb-2';
                    
                    const componentInput = createInputElement(
                        component, 
                        `${sectionId}.${fieldId}.${component.id}_${index}.${compIndex}`, 
                        compValue
                    );
                    componentInput.classList.add('form-control');
                    componentInputGroup.appendChild(componentInput);
                    
                    // Only add buttons to the first one, or add remove button to others
                    if (compIndex === 0) {
                        // Add button to add more of this component
                        const addComponentBtn = document.createElement('button');
                        addComponentBtn.type = 'button';
                        addComponentBtn.className = 'btn btn-outline-secondary';
                        addComponentBtn.innerHTML = '<i class="fas fa-plus"></i>';
                        addComponentBtn.title = `Add another ${component.name || component.id}`;
                        addComponentBtn.addEventListener('click', function() {
                            const compInputs = componentContainer.querySelectorAll('.input-group');
                            const newCompIndex = compInputs.length;
                            
                            const newComponentGroup = document.createElement('div');
                            newComponentGroup.className = 'input-group mb-2';
                            
                            const newInput = createInputElement(
                                component, 
                                `${sectionId}.${fieldId}.${component.id}_${index}.${newCompIndex}`, 
                                ''
                            );
                            newInput.classList.add('form-control');
                            newComponentGroup.appendChild(newInput);
                            
                            // Add remove button for this component value
                            const removeCompBtn = document.createElement('button');
                            removeCompBtn.type = 'button';
                            removeCompBtn.className = 'btn btn-outline-danger';
                            removeCompBtn.innerHTML = '<i class="fas fa-times"></i>';
                            removeCompBtn.addEventListener('click', function() {
                                newComponentGroup.remove();
                            });
                            newComponentGroup.appendChild(removeCompBtn);
                            
                            componentContainer.appendChild(newComponentGroup);
                        });
                        
                        componentInputGroup.appendChild(addComponentBtn);
                    } else {
                        // Add remove button for non-first items
                        const removeCompBtn = document.createElement('button');
                        removeCompBtn.type = 'button';
                        removeCompBtn.className = 'btn btn-outline-danger';
                        removeCompBtn.innerHTML = '<i class="fas fa-times"></i>';
                        removeCompBtn.addEventListener('click', function() {
                            componentInputGroup.remove();
                        });
                        componentInputGroup.appendChild(removeCompBtn);
                    }
                    
                    componentContainer.appendChild(componentInputGroup);
                });
                
                componentGroup.appendChild(componentContainer);
            } else {
                // Single component value
                const componentValue = value && value[component.id] ? value[component.id] : '';
                const componentInput = createInputElement(
                    component, 
                    `${sectionId}.${fieldId}.${component.id}_${index}`, 
                    componentValue
                );
                componentGroup.appendChild(componentInput);
            }
            
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
        let fieldIndex = 0;
        if (fieldId.includes('_')) {
            const fieldParts = fieldId.split('_');
            fieldId = fieldParts[0];
            fieldIndex = parseInt(fieldParts[1]);
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
        if (parts.length >= 3) {
            let componentParts = parts[2].split('_');
            const componentId = componentParts[0];
            
            // Get the section and field definitions
            const section = getSectionById(config, sectionId);
            const field = section.fields.find(f => f.id === fieldId);
            const component = field.components.find(c => c.id === componentId);
            
            if (field.multiple) {
                // Ensure index exists
                while (result.profile[sectionId][fieldId].length <= fieldIndex) {
                    result.profile[sectionId][fieldId].push({});
                }
                
                // Handle multiple component values (part[3] might have component index)
                if (component.multiple && parts.length >= 4) {
                    const componentIndex = parseInt(parts[3]);
                    
                    // Initialize component array if needed
                    if (!result.profile[sectionId][fieldId][fieldIndex][componentId] ||
                        !Array.isArray(result.profile[sectionId][fieldId][fieldIndex][componentId])) {
                        result.profile[sectionId][fieldId][fieldIndex][componentId] = [];
                    }
                    
                    // Ensure index exists
                    while (result.profile[sectionId][fieldId][fieldIndex][componentId].length <= componentIndex) {
                        result.profile[sectionId][fieldId][fieldIndex][componentId].push('');
                    }
                    
                    result.profile[sectionId][fieldId][fieldIndex][componentId][componentIndex] = value;
                } else {
                    // Single component value
                    result.profile[sectionId][fieldId][fieldIndex][componentId] = value;
                }
            } else {
                // Handle multiple component values in a non-multiple field
                if (component.multiple && parts.length >= 4) {
                    const componentIndex = parseInt(parts[3]);
                    
                    // Initialize component array if needed
                    if (!result.profile[sectionId][fieldId][componentId] ||
                        !Array.isArray(result.profile[sectionId][fieldId][componentId])) {
                        result.profile[sectionId][fieldId][componentId] = [];
                    }
                    
                    // Ensure index exists
                    while (result.profile[sectionId][fieldId][componentId].length <= componentIndex) {
                        result.profile[sectionId][fieldId][componentId].push('');
                    }
                    
                    result.profile[sectionId][fieldId][componentId][componentIndex] = value;
                } else {
                    // Single component value
                    result.profile[sectionId][fieldId][componentId] = value;
                }
            }
        } else {
            // Simple field
            const section = getSectionById(config, sectionId);
            const field = section.fields.find(f => f.id === fieldId);
            
            if (field.multiple) {
                // Ensure index exists
                while (result.profile[sectionId][fieldId].length <= fieldIndex) {
                    result.profile[sectionId][fieldId].push('');
                }
                result.profile[sectionId][fieldId][fieldIndex] = value;
            } else {
                result.profile[sectionId][fieldId] = value;
            }
        }
    }
    
    return result;
}

// Function to update person data via API using FormData
async function updatePersonData(personId, form) {
    try {
        // Ensure we're passing an actual HTMLFormElement
        if (!(form instanceof HTMLFormElement)) {
            throw new Error('Invalid form element provided to updatePersonData');
        }
        
        const formData = new FormData(form);
        const response = await fetch(`/update_person/${personId}`, {
            method: 'POST',
            body: formData
            // Don't set Content-Type, browser will set it with boundary for multipart/form-data
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText);
        }

        const result = await response.json();
        
        // Update the UI without full page reload
        const updatedPerson = await fetch(`/get_person/${personId}`).then(r => r.json());
        renderPersonDetails(document.getElementById('person-details'), updatedPerson);

        const people = await fetch('/get_people').then(r => r.json());
        window.people = people;

        // Re-render the sidebar list
        renderPeopleList(people, personId);

        const editSection = document.getElementById('profile-edit');
        if (editSection) editSection.style.display = 'none';
        
        // hide and clear the update person form after changes to info are made
        const formContainer = document.getElementById('person-form-container');
        if (formContainer) {
            formContainer.style.display = 'none';
            formContainer.innerHTML = '';
        }

        const detailsSection = document.getElementById('person-details');
        if (detailsSection) detailsSection.style.display = 'block';

        return result;
    } catch (error) {
        console.error('[ERROR] Failed to update person', error);
        alert('Failed to update person. Please try again.');
    }
}

export function editPerson(personId) {
    const person = window.people.find(p => p.id === personId);
    if (!person) return;

    window.selectedPersonId = personId;
    window.selectedPerson = person;

    const container = document.getElementById('person-form-container');
    const details = document.getElementById('person-details');

    if (!container || !details) return;

    // Hide the details view
    details.style.display = 'none';

    // Generate the edit form with person data
    createPersonForm(container, window.appConfig, person);

    // Ensure the form container is visible
    container.style.display = 'block';
}

export function deletePerson(personId) {
  fetch(`/delete_person/${personId}`, { method: 'POST' })
    .then(() => window.location.reload())
    .catch(err => console.error("Failed to delete person", err));
}

document.getElementById('add-person-btn').addEventListener('click', () => {
    const container = document.getElementById('person-form-container');
    createPersonForm(container, window.appConfig);
    container.style.display = 'block';
    document.getElementById('person-details').style.display = 'none';
});