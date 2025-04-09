export function renderFieldValue(value, type) {
    if (!value) return document.createTextNode('');

    // ✅ Structured object with components (like name or linkedin)
    if (typeof value === 'object' && !Array.isArray(value)) {
        const container = document.createElement('div');

        for (const [key, val] of Object.entries(value)) {
            const row = document.createElement('div');
            row.classList.add('mb-2');

            const label = document.createElement('span');
            label.classList.add('text-muted');
            label.textContent = `${key}: `;

            const content = renderFieldValue(val, type);  // ← recurse for component type rendering
            row.appendChild(label);
            row.appendChild(content);

            container.appendChild(row);
        }

        return container;
    }

    // ✅ Simple values
    if (type === 'email') {
        const link = document.createElement('a');
        link.href = `mailto:${value}`;
        link.textContent = value;
        return link;
    }

    if (type === 'url') {
        const link = document.createElement('a');
        link.href = value.startsWith('http') ? value : `http://${value}`;
        link.target = '_blank';
        link.textContent = value;
        return link;
    }

    if (type === 'date') {
        const [year, month, day] = value.split('-');
        const date = new Date(Date.UTC(year, month - 1, day));
        return document.createTextNode(date.toLocaleDateString());
    }

    return document.createTextNode(value.toString());
}



function renderSingleValue(val, type) {
    if (!val) return '';

    switch (type) {
        case 'email':
            return `<a href="mailto:${val}">${val}</a>`;
        case 'url':
            return `<a href="${val}" target="_blank">${val}</a>`;
        case 'date':
            return new Date(val).toLocaleDateString();
        default:
            return val;
    }
}

// Function to get primary name of a person
export function getPrimaryName(person) {
    const names = person?.profile?.core?.name;

    if (Array.isArray(names) && names.length > 0) {
        const name = names[0];
        return {
            first_name: name.first_name || name.first || '',
            middle_name: name.middle_name || name.middle || '',
            last_name: name.last_name || name.last || ''
        };
    }

    return { first_name: '', middle_name: '', last_name: '' };
}

export function getDisplayName(person) {
    const name = getPrimaryName(person);
    return `${name.first_name} ${name.middle_name ? name.middle_name + ' ' : ''}${name.last_name}`.trim() || 'Unnamed Person';
}


// Function to calculate and format the basset age
export function calculateBassetAge(createdAt) {
    if (!createdAt) return { shortDisplay: 'N/A', fullDisplay: 'No timestamp available' };
    
    const created = new Date(createdAt);
    if (isNaN(created.getTime())) return { shortDisplay: 'N/A', fullDisplay: 'Invalid timestamp' };
    
    const now = new Date();
    const diffMs = now - created;
    
    const minutes = Math.floor(diffMs / (1000 * 60));
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const weeks = Math.floor(days / 7);
    const months = Math.floor(days / 30);
    const years = Math.floor(days / 365);
    
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


export function createInputElement(field, name, value = '', component = null) {
    const wrapper = document.createElement('div');
    wrapper.classList.add('mb-2');

    const label = document.createElement('label');
    label.classList.add('form-label');

    // Use component name if available, otherwise field name/id
    label.textContent = component?.name || component?.id || field.name || field.id;
    label.setAttribute('for', name);

    const input = document.createElement('input');
    input.classList.add('form-control');
    input.name = name;

    const typeMap = {
        string: 'text',
        email: 'email',
        url: 'url',
        date: 'date',
        number: 'number',
        password: 'password'
    };

    input.type = typeMap[component?.type || field.type] || 'text';
    input.value = value || '';

    if (field.required) {
        input.required = true;
    }

    wrapper.appendChild(label);
    wrapper.appendChild(input);

    return wrapper;
}


export function getSectionById(config, sectionId) {
    return config.sections.find(section => section.id === sectionId) || null;
}


export function ensureHttps(url) {
    if (!url) return '';
    if (!/^https?:\/\//i.test(url)) {
        return `https://${url}`;
    }
    return url;
}