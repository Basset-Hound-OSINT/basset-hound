// ui-person-details.js - Manages person profile and detail views

import { fetchPerson, updatePerson, deletePerson } from './api.js';
import { ensureHttps, ensureTwitterUrl, ensureInstagramUrl } from './utils.js';
import { addNameField, addField, collectFormData } from './ui-form-handlers.js';
import { renderPeopleList } from './ui-people-list.js';

// Add to ui-person-details.js

// Function to calculate and format the basset age
function calculateBassetAge(createdAt) {
    if (!createdAt) return { shortDisplay: 'N/A', fullDisplay: 'No timestamp available' };
    
    const created = new Date(createdAt);
    // Check if date is valid
    if (isNaN(created.getTime())) return { shortDisplay: 'N/A', fullDisplay: 'Invalid timestamp' };
    
    const now = new Date();
    const diffMs = now - created;
    
    // Convert to different time units
    const minutes = Math.floor(diffMs / (1000 * 60));
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const weeks = Math.floor(days / 7);
    const months = Math.floor(days / 30);
    const years = Math.floor(days / 365);
    
    // Determine largest unit for short display
    let shortDisplay;
    if (years > 0) {
        shortDisplay = `${years}y`;
    } else if (months > 0) {
        shortDisplay = `${months}m`;
    } else if (weeks > 0) {
        shortDisplay = `${weeks}w`;
    } else if (days > 0) {
        shortDisplay = `${days}d`;
    } else if (hours > 0) {
        shortDisplay = `${hours}h`;
    } else {
        shortDisplay = `${minutes}m`;
    }
    
    // Create full display format
    const remainingMonths = months - (years * 12);
    const remainingWeeks = Math.floor((days - (months * 30)) / 7);
    const remainingDays = days - (months * 30) - (remainingWeeks * 7);
    const remainingHours = hours - (days * 24);
    const remainingMinutes = minutes - (hours * 60);
    
    let fullDisplay = [];
    if (years > 0) fullDisplay.push(`${years} year${years > 1 ? 's' : ''}`);
    if (remainingMonths > 0) fullDisplay.push(`${remainingMonths} month${remainingMonths > 1 ? 's' : ''}`);
    if (remainingWeeks > 0) fullDisplay.push(`${remainingWeeks} week${remainingWeeks > 1 ? 's' : ''}`);
    if (remainingDays > 0) fullDisplay.push(`${remainingDays} day${remainingDays > 1 ? 's' : ''}`);
    if (remainingHours > 0) fullDisplay.push(`${remainingHours} hour${remainingHours > 1 ? 's' : ''}`);
    if (remainingMinutes > 0) fullDisplay.push(`${remainingMinutes} minute${remainingMinutes > 1 ? 's' : ''}`);
    
    if (fullDisplay.length === 0) {
        fullDisplay = ['Just added (less than a minute)'];
    }
    
    return {
        shortDisplay,
        fullDisplay: fullDisplay.join(', ')
    };
}

// Update the selectPerson function to add the basset age
async function selectPerson(personId) {
    window.selectedPersonId = personId;
    renderPeopleList(window.people, personId);
    
    // Get the person object and its ID
    const personObj = window.people[personId];
    
    // Fetch the complete person data
    const person = await fetchPerson(personObj.id);
    
    document.getElementById('no-selection').style.display = 'none';
    document.getElementById('person-profile').style.display = 'block';
    
    // Update profile name
    const primaryName = person.names && person.names.length > 0 ? person.names[0] : { first_name: '', middle_name: '', last_name: '' };
    document.getElementById('profile-name').textContent = `${primaryName.first_name} ${primaryName.middle_name ? primaryName.middle_name + ' ' : ''}${primaryName.last_name}`;
    
    // Create a container for ID and Basset Age if it doesn't exist
    if (!document.getElementById('profile-id-container')) {
        const container = document.createElement('div');
        container.id = 'profile-id-container';
        container.className = 'd-flex align-items-center';
        
        const idElement = document.getElementById('profile-id');
        // Clone the ID element if it exists, otherwise create new
        const newIdElement = idElement ? idElement.cloneNode(true) : document.createElement('div');
        newIdElement.id = 'profile-id';
        newIdElement.className = 'person-id';
        
        container.appendChild(newIdElement);
        
        // Replace the existing ID element with our container
        if (idElement && idElement.parentNode) {
            idElement.parentNode.replaceChild(container, idElement);
        } else {
            document.querySelector('.profile-name-container').appendChild(container);
        }
    }
    
    // Update profile ID
    document.getElementById('profile-id').textContent = `ID: ${person.id || 'Unknown'}`;
    document.getElementById('profile-id').style.display = 'block';
    
    // Add basset age
    const bassetAgeData = calculateBassetAge(person.created_at);
    const container = document.getElementById('profile-id-container');
    
    // Remove existing basset age element if it exists
    const existingBassetAge = document.getElementById('basset-age');
    if (existingBassetAge) {
        container.removeChild(existingBassetAge);
    }
    
    // Create new basset age element
    const bassetAgeElement = document.createElement('div');
    bassetAgeElement.id = 'basset-age';
    bassetAgeElement.className = 'basset-age';
    bassetAgeElement.innerHTML = `Basset Age: <span class="basset-age-value">${bassetAgeData.shortDisplay}</span>`;
    bassetAgeElement.title = bassetAgeData.fullDisplay;
    bassetAgeElement.style.cursor = 'pointer';
    
    // Add click handler to show full basset age
    bassetAgeElement.addEventListener('click', function() {
        alert(`Detailed Basset Age: ${bassetAgeData.fullDisplay}`);
    });
    
    // Add to profile-id-container
    container.appendChild(bassetAgeElement);
    
    // Rest of your existing code...
    renderNames(person);
    renderDatesOfBirth(person);
    const hasEmail = renderEmails(person);
    document.getElementById('contact-info-section').style.display = hasEmail ? 'block' : 'none';
    const hasSocialMedia = renderSocialMedia(person);
    document.getElementById('social-links-section').style.display = hasSocialMedia ? 'block' : 'none';
    populateEditForm(person);
}

// Function to render person names
function renderNames(person) {
    const namesElement = document.getElementById('view-names');
    namesElement.innerHTML = '';
    if (person.names && person.names.length > 0) {
        person.names.forEach(name => {
            const nameDiv = document.createElement('div');
            nameDiv.textContent = `${name.first_name} ${name.middle_name ? name.middle_name + ' ' : ''}${name.last_name}`;
            namesElement.appendChild(nameDiv);
        });
    }
}

// Function to render dates of birth
function renderDatesOfBirth(person) {
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
}

// Function to render email addresses
function renderEmails(person) {
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
    return hasEmail;
}

// Function to render social media
function renderSocialMedia(person) {
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
    
    return hasSocialMedia;
}

// Function to populate edit form
function populateEditForm(person) {
    // Add hidden input for the ID
    const idInput = document.getElementById('edit-person-id') || document.createElement('input');
    idInput.type = 'hidden';
    idInput.id = 'edit-person-id';
    idInput.name = 'person_id';
    idInput.value = person.id || '';
    
    // Add it to the form if it doesn't already exist
    const form = document.getElementById('edit-person-form');
    if (!document.getElementById('edit-person-id')) {
        form.appendChild(idInput);
    }
    
    // Populate name fields
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
    
    // Populate social media fields
    populateSocialMediaFields(person);
}

// Function to populate social media fields
function populateSocialMediaFields(person) {
    // LinkedIn
    const linkedinContainer = document.getElementById('edit-linkedin-container');
    linkedinContainer.innerHTML = '';
    if (person.linkedin && person.linkedin.length > 0) {
        person.linkedin.forEach((profile, index) => {
            addField(linkedinContainer, 'linkedin', profile, 'LinkedIn', 'text', index > 0, 'LinkedIn profile URL');
        });
    } else {
        addField(linkedinContainer, 'linkedin', '', 'LinkedIn', 'text', false, 'LinkedIn profile URL');
    }
    
    // Twitter
    const twitterContainer = document.getElementById('edit-twitter-container');
    twitterContainer.innerHTML = '';
    if (person.twitter && person.twitter.length > 0) {
        person.twitter.forEach((profile, index) => {
            addField(twitterContainer, 'twitter', profile, 'Twitter', 'text', index > 0, 'Twitter handle or URL');
        });
    } else {
        addField(twitterContainer, 'twitter', '', 'Twitter', 'text', false, 'Twitter handle or URL');
    }
    
    // Facebook
    const facebookContainer = document.getElementById('edit-facebook-container');
    facebookContainer.innerHTML = '';
    if (person.facebook && person.facebook.length > 0) {
        person.facebook.forEach((profile, index) => {
            addField(facebookContainer, 'facebook', profile, 'Facebook', 'text', index > 0, 'Facebook profile URL');
        });
    } else {
        addField(facebookContainer, 'facebook', '', 'Facebook', 'text', false, 'Facebook profile URL');
    }
    
    // Instagram
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

// Setup event listeners for person details actions
function setupPersonDetailsListeners() {
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
        const formData = collectFormData('#edit-person-form');
        
        updatePerson(window.selectedPersonId, formData).then(() => {
            window.location.reload();
        });
    });
    
    // Delete person button
    document.getElementById('delete-person-btn').addEventListener('click', function() {
        if (confirm('Are you sure you want to delete this person?')) {
            deletePerson(window.selectedPersonId).then(() => {
                window.location.reload();
            });
        }
    });
}

export { selectPerson, setupPersonDetailsListeners };