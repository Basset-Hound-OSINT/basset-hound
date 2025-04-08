// api.js - Handles all API calls to the server

// Function to fetch all people
async function fetchPeople() {
    const response = await fetch('/get_people');
    return await response.json();
}

// Function to fetch a single person's details
async function fetchPerson(personId) {
    const response = await fetch(`/get_person/${personId}`);
    return await response.json();
}

// Function to update a person
async function updatePerson(personId, formData) {
    return fetch(`/update_person/${personId}`, {
        method: 'POST',
        body: formData
    });
}

// Function to delete a person
async function deletePerson(personId) {
    return fetch(`/delete_person/${personId}`, {
        method: 'POST'
    });
}

export { fetchPeople, fetchPerson, updatePerson, deletePerson };