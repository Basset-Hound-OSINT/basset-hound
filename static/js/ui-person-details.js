import { getDisplayName, calculateBassetAge, renderFieldValue } from './utils.js';
import { editPerson, deletePerson } from './ui-form-handlers.js';
import { openTagModal } from './tag-handler.js'; // Add this import
import { generateReport } from './report-handler.js'; // Add this import
import { openFileExplorer } from './file_explorer.js';

export async function renderPersonDetails(container, person) {
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
    const profilePicData = person.profile?.["Profile Picture Section"]?.profilepicturefile || 
                         person.profile?.profile?.profile_picture;
    let profilePicEl;

    if (profilePicData && profilePicData.path && profilePicData.name) {
        profilePicEl = document.createElement('img');
        const fileOwnerId = profilePicData.person_id || person.id;
        profilePicEl.src = `/projects/${window.currentProjectId}/people/${fileOwnerId}/files/${profilePicData.path}`;
        profilePicEl.alt = "Profile Picture";
        profilePicEl.className = "rounded-circle";
        profilePicEl.style.width = "100px";
        profilePicEl.style.height = "100px";
        profilePicEl.style.objectFit = "cover";
        
        profilePicEl.onerror = function() {
            console.log(`Failed to load image from ${this.src}. Trying fallback...`);
            this.onerror = null;
            const icon = document.createElement('i');
            icon.className = 'fas fa-user-circle text-muted';
            icon.style.fontSize = '5rem';
            this.parentNode.replaceChild(icon, this);
        };
    } else {
        profilePicEl = document.createElement('i');
        profilePicEl.className = 'fas fa-user-circle text-muted';
        profilePicEl.style.fontSize = '5rem';
        profilePicEl.title = 'Click to upload a profile picture';
        profilePicEl.style.cursor = 'pointer';

        profilePicEl.addEventListener('click', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.style.display = 'none';

            input.addEventListener('change', async () => {
                const file = input.files[0];
                if (!file) return;

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
                    renderPersonDetails(container, updated);
                }
            });

            document.body.appendChild(input);
            input.click();
        });
    }

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

    const osintBtn = document.createElement('button');
        osintBtn.className = 'btn btn-secondary';
        osintBtn.innerHTML = '<i class="fas fa-search"></i> OSINT';
        osintBtn.addEventListener('click', () => {
            window.open(`/osint.html?personId=${person.id}`, '_blank');
        });
    actionsCol.appendChild(osintBtn);
    
    const tagBtn = document.createElement('button');
    tagBtn.className = 'btn btn-info';
    tagBtn.innerHTML = '<i class="fas fa-tags"></i> Tag';
    tagBtn.addEventListener('click', () => openTagModal(person.id));
    actionsCol.appendChild(tagBtn);

    const mapBtn = document.createElement('button');
        mapBtn.className = 'btn btn-secondary';
        mapBtn.innerHTML = '<i class="fas fa-map"></i> Map';
        mapBtn.addEventListener('click', () => {
            window.open(`/map.html?personId=${person.id}`, '_blank');
    });
    actionsCol.appendChild(mapBtn);

    const reportBtn = document.createElement('button');
    reportBtn.className = 'btn btn-secondary';
    reportBtn.innerHTML = '<i class="fas fa-file-alt"></i> Report';
    reportBtn.addEventListener('click', () => generateReport(person.id));
    actionsCol.appendChild(reportBtn);

    const filesBtn = document.createElement('button');
    filesBtn.className = 'btn btn-secondary';
    filesBtn.innerHTML = '<i class="fas fa-folder-open"></i> Files';
    filesBtn.addEventListener('click', () => openFileExplorer(person.id));
    actionsCol.appendChild(filesBtn);

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

            if (sectionId === "Tagged People") continue; // <-- Skip generic rendering for this section
            if (sectionId === "Transitive Relationships") continue; // (if you have this as a section)

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
                                    valueDisplay = document.createElement('span');
                                    valueDisplay.textContent = '••••••••';
                                    copyText = compVal;
                                } else if (component.type === 'file' && compVal && compVal.path) {
                                    const fileOwnerId = compVal.person_id || person.id;
                                    valueDisplay = document.createElement('div');
                                
                                    if (compVal.id) {
                                        const fileId = document.createElement('div');
                                        fileId.className = 'text-muted small';
                                        fileId.textContent = `ID: ${compVal.id}`;
                                        valueDisplay.appendChild(fileId);
                                    }
                                
                                    const link = document.createElement('a');
                                    link.href = `/projects/${window.currentProjectId}/people/${fileOwnerId}/files/${compVal.path}`;
                                    link.target = '_blank';
                                    link.textContent = compVal.name || compVal.path;
                                    valueDisplay.appendChild(link);
                                
                                    copyText = compVal.name || compVal.path;
                                } else if (typeof compVal === 'object') {
                                    // Handle object values
                                    if (component.id === 'first_name' || component.id === 'last_name' || component.id === 'middle_name') {
                                        valueDisplay = document.createTextNode(compVal);
                                        copyText = compVal;
                                    } else {
                                        valueDisplay = document.createTextNode(JSON.stringify(compVal, null, 2));
                                        copyText = JSON.stringify(compVal);
                                    }
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

                        let copyText = '';
                        let valueEl;

                        if (field?.type === 'file') {
                            if (typeof value === 'object' && value.path) {
                                const fileOwnerId = value.person_id || person.id;
                                copyText = value.name || value.path;
                                valueEl = document.createElement('div');
                                
                                if (value.id) {
                                    const fileId = document.createElement('div');
                                    fileId.className = 'text-muted small';
                                    fileId.textContent = `ID: ${value.id}`;
                                    valueEl.appendChild(fileId);
                                }
                                
                                const link = document.createElement('a');
                                link.href = `/projects/${window.currentProjectId}/people/${fileOwnerId}/files/${value.path}`;
                                link.target = '_blank';
                                link.textContent = value.name || value.path;
                                valueEl.appendChild(link);
                            } else if (typeof value === 'string') {
                                copyText = value.split('/').pop() || value;
                                valueEl = document.createElement('a');
                                valueEl.href = `/projects/${window.currentProjectId}/people/${person.id}/files/${value}`;
                                valueEl.target = '_blank';
                                valueEl.textContent = copyText;
                            } else {
                                valueEl = document.createTextNode('Invalid file reference');
                            }
                        } else if (fieldId === 'name' && typeof value === 'object') {
                            // Special handling for name objects
                            const displayName = getDisplayName({ profile: { [sectionId]: { [fieldId]: value } } });
                            valueEl = document.createTextNode(displayName);
                            copyText = displayName;
                        } else if (typeof value === 'object') {
                            // Handle other object values
                            valueEl = document.createTextNode(JSON.stringify(value, null, 2));
                            copyText = JSON.stringify(value);
                        } else {
                            valueEl = renderFieldValue(value, field?.type, person.id);  
                            copyText = typeof value === 'string' ? value : '';
                            if (typeof valueEl === 'string') {
                                const span = document.createElement('span');
                                span.textContent = valueEl;
                                valueEl = span;
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
    
    container.appendChild(sectionsContainer);
    await renderTaggedPeopleSection(sectionsContainer, person.id);
    await renderTransitivePeopleSection(sectionsContainer, person.id);
    await renderAssociatedFilesSection(sectionsContainer, person.id);
    await renderToolReportsSection(sectionsContainer, person.id);
}

async function renderTaggedPeopleSection(container, personId) {
    // Create the card section
    const section = document.createElement('div');
    section.className = 'card mb-3';
    section.innerHTML = `<div class="card-header"><h5><i class="fas fa-tags me-2"></i>Tagged People</h5></div>`;
    const body = document.createElement('div');
    body.className = 'card-body';

    // Fetch the latest person data to get tags
    const res = await fetch(`/get_person/${personId}`);
    const person = await res.json();

    // Find the tagged people field (adjust as needed for your schema)
    const taggedSection = person.profile?.["Tagged People"];
    const taggedIds = taggedSection?.tagged_people || [];

    if (!Array.isArray(taggedIds) || taggedIds.length === 0) return; // Only render if there are tags

    // Fetch all people to resolve names
    const peopleRes = await fetch('/get_people');
    const allPeople = await peopleRes.json();

    // Build a map for quick lookup
    const peopleMap = {};
    allPeople.forEach(p => { peopleMap[p.id] = p; });

    // Build the list
    const ul = document.createElement('ul');
    ul.className = 'list-group';
    taggedIds.forEach(taggedId => {
        const taggedPerson = peopleMap[taggedId];
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex align-items-center';
        if (taggedPerson) {
            li.innerHTML = `<span class="text-muted small me-2">ID: ${taggedPerson.id}</span>
                <a href="#" class="tagged-person-link" data-id="${taggedPerson.id}">${getDisplayName(taggedPerson)}</a>`;
        } else {
            li.innerHTML = `<span class="text-danger">Unknown Person (ID: ${taggedId})</span>`;
        }
        ul.appendChild(li);
    });
    body.appendChild(ul);
    section.appendChild(body);
    container.appendChild(section);

    // Optional: Add click handler to view tagged person
    ul.querySelectorAll('.tagged-person-link').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            const id = link.getAttribute('data-id');
            // You may want to call a function to show that person's details
            // For example: renderPersonDetails(container, peopleMap[id]);
        });
    });
}

async function renderTransitivePeopleSection(container, personId) {
    // Fetch all people and this person's tags
    const peopleRes = await fetch('/get_people');
    const allPeople = await peopleRes.json();

    // Build a map for quick lookup
    const peopleMap = {};
    allPeople.forEach(p => { peopleMap[p.id] = p; });

    // BFS to find transitive relationships and hops FROM this person
    const visited = {};
    const hops = {};
    const queue = [];
    visited[personId] = true;
    hops[personId] = 0;
    queue.push(personId);

    while (queue.length > 0) {
        const currentId = queue.shift();
        const currentPerson = peopleMap[currentId];
        const directTags = currentPerson?.profile?.["Tagged People"]?.tagged_people || [];
        for (const tagId of directTags) {
            if (!visited[tagId]) {
                visited[tagId] = true;
                hops[tagId] = hops[currentId] + 1;
                queue.push(tagId);
            }
        }
    }

    // Remove direct tags and self; only keep those with hops > 1 (transitive)
    let transitiveIds = Object.keys(hops)
        .filter(id => id !== personId && hops[id] > 1);

    // Now, for symmetry, check if this person is in anyone else's transitive relationships
    allPeople.forEach(otherPerson => {
        if (otherPerson.id === personId) return;
        // BFS from otherPerson
        const otherVisited = {};
        const otherHops = {};
        const otherQueue = [];
        otherVisited[otherPerson.id] = true;
        otherHops[otherPerson.id] = 0;
        otherQueue.push(otherPerson.id);

        while (otherQueue.length > 0) {
            const currentId = otherQueue.shift();
            const currentPerson = peopleMap[currentId];
            const directTags = currentPerson?.profile?.["Tagged People"]?.tagged_people || [];
            for (const tagId of directTags) {
                if (!otherVisited[tagId]) {
                    otherVisited[tagId] = true;
                    otherHops[tagId] = otherHops[currentId] + 1;
                    otherQueue.push(tagId);
                }
            }
        }
        // If this person is in otherPerson's transitive relationships (but not direct), add otherPerson
        if (otherHops[personId] > 1 && !transitiveIds.includes(otherPerson.id)) {
            transitiveIds.push(otherPerson.id);
            hops[otherPerson.id] = otherHops[personId]; // Store the hop count from their perspective
        }
    });

    if (!transitiveIds.length) return;

    const section = document.createElement('div');
    section.className = 'card mb-3';
    section.innerHTML = `<div class="card-header"><h5><i class="fas fa-project-diagram me-2"></i>Transitive Relationships</h5></div>`;
    const body = document.createElement('div');
    body.className = 'card-body';

    const ul = document.createElement('ul');
    ul.className = 'list-group';
    transitiveIds.forEach(id => {
        const relatedPerson = peopleMap[id];
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex align-items-center';
        if (relatedPerson) {
            li.innerHTML = `<span class="text-muted small me-2">ID: ${relatedPerson.id}</span>
                <a href="#" class="tagged-person-link" data-id="${relatedPerson.id}">${getDisplayName(relatedPerson)}</a>
                <span class="badge bg-info ms-2">${hops[id]} hops</span>`;
        } else {
            li.innerHTML = `<span class="text-danger">Unknown Person (ID: ${id})</span>`;
        }
        ul.appendChild(li);
    });
    body.appendChild(ul);
    section.appendChild(body);
    container.appendChild(section);

    // Optional: Add click handler to view tagged person
    ul.querySelectorAll('.tagged-person-link').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            const id = link.getAttribute('data-id');
            // You may want to call a function to show that person's details
            // For example: renderPersonDetails(container, peopleMap[id]);
        });
    });
}

async function renderAssociatedFilesSection(container, personId) {
    const res = await fetch(`/person/${personId}/explore?path=files`);
    const data = await res.json();
    const files = (data.entries || []).filter(e => e.type === 'file');
    if (!files.length) return; // <-- Only render if files exist

    const section = document.createElement('div');
    section.className = 'card mb-3';
    section.innerHTML = `<div class="card-header"><h5><i class="fas fa-paperclip me-2"></i>Associated Files</h5></div>`;
    const body = document.createElement('div');
    body.className = 'card-body';

    const ul = document.createElement('ul');
    ul.className = 'list-group';
    files.forEach(file => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex align-items-center';
        li.innerHTML = `<a href="${file.url}" target="_blank">${file.name || file.path}</a>
            <span class="text-muted small ms-2">${file.id ? 'ID: ' + file.id : ''}</span>`;
        ul.appendChild(li);
    });
    body.appendChild(ul);
    section.appendChild(body);
    container.appendChild(section);
}

async function renderToolReportsSection(container, personId) {
    const res = await fetch(`/person/${personId}/explore?path=reports`);
    const data = await res.json();
    const files = (data.entries || []).filter(e => e.type === 'file' && e.name.endsWith('.md'));
    if (!files.length) return; // <-- Only render if reports exist

    const section = document.createElement('div');
    section.className = 'card mb-3';
    section.innerHTML = `<div class="card-header"><h5><i class="fas fa-file-alt me-2"></i>Tool Reports</h5></div>`;
    const body = document.createElement('div');
    body.className = 'card-body';

    const ul = document.createElement('ul');
    ul.className = 'list-group';
    files.forEach(file => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex align-items-center';
        li.innerHTML = `<a href="${file.url}" target="_blank">${file.name || file.path}</a>
            <span class="text-muted small ms-2">${file.id ? 'ID: ' + file.id : ''}</span>`;
        ul.appendChild(li);
    });
    body.appendChild(ul);
    section.appendChild(body);
    container.appendChild(section);
}