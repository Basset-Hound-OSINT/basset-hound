// ui-person-details.js - Manages person profile and detail views

import { fetchPerson, updatePerson, deletePerson } from './api.js';
import { ensureHttps, ensureTwitterUrl, ensureInstagramUrl } from './utils.js';
import { addNameField, addField, collectFormData } from './ui-form-handlers.js';
import { renderPeopleList } from './ui-people-list.js';

// Function to select and display a person
async function selectPerson(personId) {
    window.selectedPersonId = personId;
    renderPeopleList(window.people, personId);
    
    const person = await fetchPerson(personId);
    
    document.getElementById('no-selection').style.display = 'none';
    document.getElementById('person-profile').style.display = 'block';
    
    // Update profile name
    const primaryName = person.names && person.names.length > 0 ? person.names[0] : { first_name: '', middle_name: '', last_name: '' };
    document.getElementById('profile-name').textContent = `${primaryName.first_name} ${primaryName.middle_name ? primaryName.middle_name + ' ' : ''}${primaryName.last_name}`;
    
    // Display all names
    renderNames(person);
    
    // Display dates of birth
    renderDatesOfBirth(person);
    
    // Display emails
    const hasEmail = renderEmails(person);
    
    // Show/hide contact section based on if any field is populated
    document.getElementById('contact-info-section').style.display = hasEmail ? 'block' : 'none';
    
    // Handle social media links
    const hasSocialMedia = renderSocialMedia(person);
    
    // Show/hide social media section based on if any field is populated
    document.getElementById('social-links-section').style.display = hasSocialMedia ? 'block' : 'none';
    
    // Populate edit form fields
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