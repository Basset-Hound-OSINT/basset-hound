import { getDisplayName, calculateBassetAge, renderFieldValue } from './utils.js';
import { editPerson, deletePerson } from './ui-form-handlers.js';

export function renderPersonDetails(container, person) {
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
            sectionHeader.innerHTML = `<h5>${section.name || sectionId}</h5>`;
            sectionCard.appendChild(sectionHeader);

            const sectionBody = document.createElement('div');
            sectionBody.className = 'card-body';

            for (const fieldId in sectionData) {
                const fieldValue = sectionData[fieldId];
                if (!fieldValue || (Array.isArray(fieldValue) && fieldValue.length === 0)) continue;

                const field = section.fields.find(f => f.id === fieldId);
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'mb-3';

                const fieldLabel = document.createElement('h6');
                fieldLabel.textContent = field.name || fieldId;
                fieldDiv.appendChild(fieldLabel);

                const values = Array.isArray(fieldValue) ? fieldValue : [fieldValue];

                if (field.components) {
                    values.forEach((entry, idx) => {
                        const entryDiv = document.createElement('div');
                        entryDiv.classList.add('mb-2');

                        field.components.forEach(component => {
                            const compVal =
                                entry[component.id] ||
                                entry[component.id.replace('_name', '')] ||
                                entry[component.id.replace('name', '')];

                            if (!compVal) return;

                            const compRow = document.createElement('div');
                            compRow.classList.add('mb-2', 'd-flex', 'align-items-center', 'gap-2');

                            const copyIcon = document.createElement('i');
                            copyIcon.className = 'fas fa-copy text-secondary';
                            copyIcon.style.cursor = 'pointer';
                            copyIcon.title = `Copy ${component.name || component.id}`;

                            const label = document.createElement('span');
                            label.classList.add('text-muted', 'me-1');
                            label.textContent = `${component.name || component.id}: `;

                            let valueDisplay;
                            let copyText = compVal;

                            if (component.type === 'password') {
                                const masked = document.createElement('span');
                                masked.textContent = '••••••••';

                                const real = document.createElement('span');
                                real.textContent = compVal;
                                real.style.display = 'none';

                                const toggleBtn = document.createElement('i');
                                toggleBtn.className = 'fas fa-eye text-secondary';
                                toggleBtn.style.cursor = 'pointer';
                                toggleBtn.title = 'Show password';
                                toggleBtn.addEventListener('click', () => {
                                    const showing = masked.style.display === 'none';
                                    masked.style.display = showing ? 'inline' : 'none';
                                    real.style.display = showing ? 'none' : 'inline';
                                    toggleBtn.className = showing ? 'fas fa-eye' : 'fas fa-eye-slash';
                                });

                                valueDisplay = document.createElement('span');
                                valueDisplay.appendChild(masked);
                                valueDisplay.appendChild(real);
                                valueDisplay.appendChild(toggleBtn);
                            } else {
                                valueDisplay = renderFieldValue(compVal, component.type);
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

                        if (idx > 0) fieldDiv.appendChild(document.createElement('hr'));
                        fieldDiv.appendChild(entryDiv);
                    });
                } else {
                    values.forEach((value, idx) => {
                        const wrapper = document.createElement('div');
                        wrapper.classList.add('mb-2', 'd-flex', 'align-items-center', 'gap-2');

                        const copyIcon = document.createElement('i');
                        copyIcon.className = 'fas fa-copy text-secondary';
                        copyIcon.style.cursor = 'pointer';
                        copyIcon.title = `Copy ${field.name || field.id}`;

                        let valueEl = renderFieldValue(value, field.type);
                        let copyText = value;

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
