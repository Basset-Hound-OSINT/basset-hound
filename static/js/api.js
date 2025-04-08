// api.js - Handles all API calls to the server

// Function to fetch all people
async function fetchPeople() {
    const response = await fetch('/get_people');
    return await response.json();
}

// Function to fetch a single person's details
async function fetchPerson(personId) {
    // If personId is a number (index), get the ID from people array
    if (typeof personId === 'number') {
        const id = window.people[personId].id;
        const response = await fetch(`/get_person/${id}`);
        return await response.json();
    } else {
        // Otherwise use the ID directly
        const response = await fetch(`/get_person/${personId}`);
        return await response.json();
    }
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