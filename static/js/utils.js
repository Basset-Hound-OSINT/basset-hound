// utils.js - Helper functions used across multiple files

// Helper function to ensure URL has https://
function ensureHttps(url) {
    if (!url) return '#';
    if (url.startsWith('http://') || url.startsWith('https://')) {
        return url;
    }
    return 'https://' + url;
}

// Helper function to ensure Twitter URL
function ensureTwitterUrl(handle) {
    if (!handle) return '#';
    if (handle.includes('twitter.com') || handle.includes('x.com')) {
        return handle;
    }
    // Remove @ if present
    const cleanHandle = handle.startsWith('@') ? handle.substring(1) : handle;
    return 'https://twitter.com/' + cleanHandle;
}

// Helper function to ensure Instagram URL
function ensureInstagramUrl(handle) {
    if (!handle) return '#';
    if (handle.includes('instagram.com')) {
        return handle;
    }
    // Remove @ if present
    const cleanHandle = handle.startsWith('@') ? handle.substring(1) : handle;
    return 'https://instagram.com/' + cleanHandle;
}

// Function to show or hide a field based on value
function toggleField(containerId, valueElementId, value) {
    const container = document.getElementById(containerId);
    const valueElement = document.getElementById(valueElementId);
    
    if (value && value.trim() !== '') {
        container.style.display = 'flex';
        valueElement.textContent = value;
        return true;
    } else {
        container.style.display = 'none';
        return false;
    }
}

export { ensureHttps, ensureTwitterUrl, ensureInstagramUrl, toggleField };