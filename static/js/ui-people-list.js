// ui-people-list.js - Handles people list rendering and interaction

import { selectPerson } from './ui-person-details.js';

// Function to render the people list
function renderPeopleList(people, selectedPersonId) {
    const personList = document.getElementById('person-list');
    personList.innerHTML = '';
    
    people.forEach((person, index) => {
        const primaryName = person.names && person.names.length > 0 ? person.names[0] : { first_name: '', last_name: '' };
        const displayName = `${primaryName.first_name} ${primaryName.last_name}`.trim() || 'Unnamed Person';
        
        const li = document.createElement('li');
        li.className = 'person-item' + (index === selectedPersonId ? ' active' : '');
        
        // Create name element
        const nameElement = document.createElement('div');
        nameElement.className = 'person-name';
        nameElement.textContent = displayName;
        
        // Create ID element
        const idElement = document.createElement('div');
        idElement.className = 'person-id text-muted small';
        idElement.textContent = `ID: ${person.id || 'Unknown'}`;
        
        // Add elements to list item
        li.appendChild(nameElement);
        li.appendChild(idElement);
        
        li.addEventListener('click', () => selectPerson(index));
        personList.appendChild(li);
    });
}

// Setup search functionality
function setupSearch(people) {
    document.getElementById('search-input').addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const personList = document.getElementById('person-list');
        personList.innerHTML = '';
        
        people.forEach((person, index) => {
            // Check if any of the person's data contains the search term
            let matches = false;
            
            // Check ID
            if (person.id && person.id.toLowerCase().includes(searchTerm)) {
                matches = true;
            }
            
            // Check names
            if (!matches && person.names) {
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
                li.className = 'person-item' + (index === window.selectedPersonId ? ' active' : '');
                
                // Create name element
                const nameElement = document.createElement('div');
                nameElement.className = 'person-name';
                nameElement.textContent = displayName;
                
                // Create ID element
                const idElement = document.createElement('div');
                idElement.className = 'person-id text-muted small';
                idElement.textContent = `ID: ${person.id || 'Unknown'}`;
                
                // Add elements to list item
                li.appendChild(nameElement);
                li.appendChild(idElement);
                
                li.addEventListener('click', () => selectPerson(index));
                personList.appendChild(li);
            }
        });
    });
}

export { renderPeopleList, setupSearch };