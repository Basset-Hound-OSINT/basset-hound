// api.js - Handles all API calls to the server

// Function to fetch all people
async function fetchPeople() {
    const response = await fetch('/get_people');
    return await response.json();
}

// Function to fetch a single person's details
async function fetchPerson(personId) {
    // If personId is a string (actual ID), use it directly
    const response = await fetch(`/get_person/${personId}`);
    return await response.json();
}

// Function to update a person
export async function updatePerson(personId, profileData) {
  return fetch(`/update_person/${personId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ profile: profileData })
  });
}


// Function to delete a person
async function deletePerson(personId) {
    return fetch(`/delete_person/${personId}`, {
        method: 'POST'
    });
}

export { fetchPeople, fetchPerson, deletePerson };