async function fetchProfileData(personId) {
    try {
        const response = await fetch(`/get_person/${personId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch profile data');
        }
        const profileData = await response.json();
        document.getElementById('profile-data').textContent = JSON.stringify(profileData, null, 4);
    } catch (error) {
        console.error('Error fetching profile data:', error);
        document.getElementById('profile-data').textContent = 'Error loading profile data.';
    }
}

// Get the personId from the query parameters
const urlParams = new URLSearchParams(window.location.search);
const personId = urlParams.get('personId');

// Fetch and display the profile data
if (personId) {
    fetchProfileData(personId);
} else {
    document.getElementById('profile-data').textContent = 'No person ID provided.';
}