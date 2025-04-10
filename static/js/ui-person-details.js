import { getDisplayName, calculateBassetAge, renderFieldValue } from './utils.js';
import { editPerson, deletePerson } from './ui-form-handlers.js';

export function renderPersonDetails(container, person) {
    if (!person) {
        console.error("renderPersonDetails was called with undefined person!");
        container.innerHTML = '<div class="alert alert-danger">Error: Could not load person data.</div>';
        return;
    }

    container.innerHTML = '';

    // Header
    const header = document.createElement('div');
    header.className = 'd-flex justify-content-between align-items-center mb-4';
    const name = document.createElement('h2');
    name.textContent = getDisplayName(person);
    header.appendChild(name);

    const actionsDiv = document.createElement('div');
    const editBtn = document.createElement('button');
    editBtn.className = 'btn btn-primary me-2';
    editBtn.innerHTML = '<i class="fas fa-edit"></i> Edit';
    editBtn.addEventListener('click', () => editPerson(person.id));
    actionsDiv.appendChild(editBtn);

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'btn btn-danger';
    deleteBtn.innerHTML = '<i class="fas fa-trash"></i> Delete';
    deleteBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to delete this person?')) {
            deletePerson(person.id);
        }
    });
    actionsDiv.appendChild(deleteBtn);
    header.appendChild(actionsDiv);
    container.appendChild(header);

    // ID + Account Age
    if (person.created_at) {
        const ageInfo = calculateBassetAge(person.created_at);
        const metaRow = document.createElement('div');
        metaRow.className = 'mb-4 text-muted d-flex gap-4 align-items-center flex-wrap';

        const idSpan = document.createElement('span');
        idSpan.innerHTML = `<strong>ID:</strong> ${person.id}`;
        const ageSpan = document.createElement('span');
        ageSpan.innerHTML = `<strong>Added:</strong> ${ageInfo.fullDisplay}`;

        metaRow.appendChild(idSpan);
        metaRow.appendChild(ageSpan);
        container.appendChild(metaRow);
    }

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
            sectionCard.className = 'card mb-4';

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
                              const link = document.createElement('a');
                              link.href = `/files/${person.id}/${compVal.path}`;
                              link.target = '_blank';
                              link.textContent = compVal.name || 'Download File';
                              valueDisplay = link;
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
            container.appendChild(sectionCard);
        }
    }
}