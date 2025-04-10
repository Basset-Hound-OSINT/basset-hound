import { getDisplayName, calculateBassetAge, renderFieldValue } from './utils.js';
import { editPerson, deletePerson } from './ui-form-handlers.js';

export function renderPersonDetails(container, person) {
    if (!person) {
        console.error("renderPersonDetails was called with undefined person!");
        container.innerHTML = '<div class="alert alert-danger">Error: Could not load person data.</div>';
        return;
    }

    container.innerHTML = '';

    // Create profile header
    const profileHeader = document.createElement('div');
    profileHeader.className = 'profile-header card mb-3 p-3';
    
    // Create main row for header content
    const headerRow = document.createElement('div');
    headerRow.className = 'd-flex align-items-center gap-3';

    // Profile picture section
    const profilePicData = person.profile?.["Profile Picture Section"]?.profilepicturefile;
    let profilePicEl;

    if (profilePicData && profilePicData.path && profilePicData.name) {
        profilePicEl = document.createElement('img');
        profilePicEl.src = `/files/${person.id}/${profilePicData.path}`;
        profilePicEl.alt = "Profile Picture";
        profilePicEl.className = "rounded-circle";
        profilePicEl.style.width = "100px";
        profilePicEl.style.height = "100px";
        profilePicEl.style.objectFit = "cover";
    } else {
        profilePicEl = document.createElement('i');
        profilePicEl.className = 'fas fa-user-circle text-muted';
        profilePicEl.style.fontSize = '5rem';
        profilePicEl.title = 'Click to upload a profile picture';
        profilePicEl.style.cursor = 'pointer';

        // Optional: Click to trigger file input
        profilePicEl.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.style.display = 'none';

            input.addEventListener('change', async () => {
                const file = input.files[0];
                if (!file) return;

                // Check file type client-side
                if (!file.type.startsWith('image/')) {
                    alert('Only image files are allowed as profile pictures.');
                    return;
                }

                const formData = new FormData();
                formData.append('profile.profile_picture', file);
                formData.append('person_id', person.id);

                const res = await fetch(`/update_person/${person.id}`, {
                    method: 'POST',
                    body: formData
                });

                if (res.ok) {
                    const updated = await fetch(`/get_person/${person.id}`).then(r => r.json());
                    renderPersonDetails(container, updated); // Refresh
                }
            });

            document.body.appendChild(input);
            input.click();
        });
    }

    // Add profile picture to header row
    headerRow.appendChild(profilePicEl);

    // Name and metadata column
    const infoCol = document.createElement('div');
    infoCol.className = 'flex-grow-1';

    // Name heading
    const name = document.createElement('h2');
    name.textContent = getDisplayName(person);
    name.className = 'mb-1';
    infoCol.appendChild(name);

    // ID and account age row
    if (person.created_at) {
        const ageInfo = calculateBassetAge(person.created_at);
        const metaRow = document.createElement('div');
        metaRow.className = 'text-muted d-flex gap-3 align-items-center flex-wrap';

        const idSpan = document.createElement('span');
        idSpan.innerHTML = `<strong>ID:</strong> ${person.id}`;
        
        const ageSpan = document.createElement('span');
        ageSpan.innerHTML = `<strong>Added:</strong> ${ageInfo.shortDisplay}`;
        ageSpan.title = ageInfo.fullDisplay;
        
        metaRow.appendChild(idSpan);
        metaRow.appendChild(ageSpan);
        infoCol.appendChild(metaRow);
    }

    headerRow.appendChild(infoCol);

    // Actions column
    const actionsCol = document.createElement('div');
    actionsCol.className = 'd-flex gap-2';

    const editBtn = document.createElement('button');
    editBtn.className = 'btn btn-primary';
    editBtn.innerHTML = '<i class="fas fa-edit"></i> Edit';
    editBtn.addEventListener('click', () => editPerson(person.id));
    actionsCol.appendChild(editBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'btn btn-danger';
    deleteBtn.innerHTML = '<i class="fas fa-trash"></i> Delete';
    deleteBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to delete this person?')) {
            deletePerson(person.id);
        }
    });
    actionsCol.appendChild(deleteBtn);
    
    headerRow.appendChild(actionsCol);
    profileHeader.appendChild(headerRow);
    
    // Add header to main container
    container.appendChild(profileHeader);

    // Create scrollable section container
    const sectionsContainer = document.createElement('div');
    sectionsContainer.className = 'profile-sections-container';
    sectionsContainer.style.height = '75vh';
    sectionsContainer.style.overflowY = 'auto';
    sectionsContainer.style.paddingRight = '5px';

    // Profile sections
    if (person.profile) {
        for (const sectionId in person.profile) {
            const sectionData = person.profile[sectionId];
            const hasData = Object.values(sectionData).some(value => {
                if (Array.isArray(value)) return value.length > 0;
                if (typeof value === 'object') return Object.keys(value).length > 0;
                return value !== null && value !== '';
            });

            if (!hasData) continue;

            const section = window.appConfig.sections.find(s => s.id === sectionId);
            const sectionCard = document.createElement('div');
            sectionCard.className = 'card mb-3';

            const sectionHeader = document.createElement('div');
            sectionHeader.className = 'card-header';
            sectionHeader.innerHTML = `<h5>${section?.name || sectionId}</h5>`;
            sectionCard.appendChild(sectionHeader);

            const sectionBody = document.createElement('div');
            sectionBody.className = 'card-body';

            for (const fieldId in sectionData) {
                const fieldValue = sectionData[fieldId];
                if (!fieldValue || (Array.isArray(fieldValue) && fieldValue.length === 0)) continue;

                const field = section?.fields?.find(f => f.id === fieldId);
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'mb-3';

                const fieldLabel = document.createElement('h6');
                fieldLabel.textContent = field?.name || fieldId;
                fieldDiv.appendChild(fieldLabel);

                const values = Array.isArray(fieldValue) ? fieldValue : [fieldValue];

                if (field?.type === "component" && field.components) {
                    values.forEach((entry, idx) => {
                        const entryDiv = document.createElement('div');
                        entryDiv.classList.add('mb-2');

                        field.components.forEach(component => {
                          let compVals = entry[component.id];
                          if (!compVals || (Array.isArray(compVals) && compVals.length === 0)) return;
                          if (!Array.isArray(compVals)) compVals = [compVals];

                          compVals.forEach((compVal, compIdx) => {
                            const compRow = document.createElement('div');
                            compRow.classList.add('mb-2', 'd-flex', 'align-items-center', 'gap-2');

                            const copyIcon = document.createElement('i');
                            copyIcon.className = 'fas fa-copy text-secondary';
                            copyIcon.style.cursor = 'pointer';
                            copyIcon.title = `Copy ${component.name || component.id}`;

                            const label = document.createElement('span');
                            label.classList.add('text-muted', 'me-1');
                            label.textContent = `${component.name || component.id}${compVals.length > 1 ? ` [${compIdx + 1}]` : ''}: `;

                            let valueDisplay;
                            let copyText = '';

                            if (component.type === 'password') {
                              // Your existing password logic
                            } else if (component.type === 'file' && compVal && compVal.path) {
                                valueDisplay = document.createElement('div');

                                const fileId = document.createElement('div');
                                fileId.className = 'text-muted small';
                                fileId.textContent = `ID: ${compVal.id || '(missing)'}`;

                                const link = document.createElement('a');
                                link.href = `/files/${person.id}/${compVal.path}`;
                                link.target = '_blank';
                                link.textContent = compVal.name || compVal.path;

                                valueDisplay.appendChild(fileId);
                                valueDisplay.appendChild(link);

                                copyText = compVal.name || compVal.path;
                            } else {
                                valueDisplay = renderFieldValue(compVal, component.type, person.id);
                                copyText = typeof compVal === 'string' ? compVal : '';
                                if (typeof valueDisplay === 'string') {
                                    const span = document.createElement('span');
                                    span.textContent = valueDisplay;
                                    valueDisplay = span;
                                }
                            }


                            copyIcon.addEventListener('click', () => {
                              navigator.clipboard.writeText(copyText).then(() => {
                                copyIcon.classList.replace('fa-copy', 'fa-check');
                                copyIcon.classList.add('text-success');
                                setTimeout(() => {
                                  copyIcon.classList.replace('fa-check', 'fa-copy');
                                  copyIcon.classList.remove('text-success');
                                }, 1000);
                              });
                            });

                            compRow.appendChild(copyIcon);
                            compRow.appendChild(label);
                            compRow.appendChild(valueDisplay);
                            entryDiv.appendChild(compRow);
                          });
                        });


                        if (idx > 0) fieldDiv.appendChild(document.createElement('hr'));
                        fieldDiv.appendChild(entryDiv);
                    });
                } else {
                    values.forEach((value, idx) => {
                        const wrapper = document.createElement('div');
                        wrapper.classList.add('mb-2', 'd-flex', 'align-items-start', 'gap-2');

                        const copyIcon = document.createElement('i');
                        copyIcon.className = 'fas fa-copy text-secondary mt-1';
                        copyIcon.style.cursor = 'pointer';
                        copyIcon.title = `Copy ${field?.name || fieldId}`;

                        let valueEl;
                        let copyText = value;

                        // Special handling for file type values before sending to renderFieldValue
                        if (field?.type === 'file') {
                            if (typeof value === 'object' && value.path && value.name) {
                                // Make sure the file value has its ID if available
                                if (!value.id && value.file_id) {
                                    value.id = value.file_id;
                                }
                                copyText = value.name;
                            } else if (typeof value === 'string') {
                                // If it's a simple string, check if it's in format "id:path"
                                if (value.includes(':')) {
                                    const parts = value.split(':');
                                    copyText = parts.slice(1).join(':').split('/').pop() || value;
                                } else {
                                    copyText = value.split('/').pop() || value;
                                }
                            }
                        }

                        valueEl = renderFieldValue(value, field?.type, person.id);
                        if (typeof valueEl === 'string') {
                            const span = document.createElement('span');
                            span.textContent = valueEl;
                            valueEl = span;
                        }

                        copyIcon.addEventListener('click', () => {
                            navigator.clipboard.writeText(copyText).then(() => {
                                copyIcon.classList.replace('fa-copy', 'fa-check');
                                copyIcon.classList.add('text-success');
                                setTimeout(() => {
                                    copyIcon.classList.replace('fa-check', 'fa-copy');
                                    copyIcon.classList.remove('text-success');
                                }, 1000);
                            });
                        });

                        wrapper.appendChild(copyIcon);
                        wrapper.appendChild(valueEl);

                        if (idx > 0) fieldDiv.appendChild(document.createElement('hr'));
                        fieldDiv.appendChild(wrapper);
                    });
                }

                sectionBody.appendChild(fieldDiv);
            }

            sectionCard.appendChild(sectionBody);
            sectionsContainer.appendChild(sectionCard);
        }
    }
    
    // Add scrollable sections container to main container
    container.appendChild(sectionsContainer);
}