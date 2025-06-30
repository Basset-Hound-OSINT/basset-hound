import { getDisplayName } from './utils.js';

export async function generateReport(personId) {
    try {
        // Fetch the person's data
        const person = await fetch(`/get_person/${personId}`).then(res => {
            if (!res.ok) throw new Error('Failed to fetch person data');
            return res.json();
        });

        if (!person || !person.profile) {
            alert('Person data not found.');
            return;
        }

        // Generate the Markdown content
        const displayName = getDisplayName(person);
        const reportContent = await generateMarkdownReport(person, displayName);

        // Send the Markdown content to the Flask endpoint
        const response = await fetch(`/zip_user_files/${personId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'text/plain',
            },
            body: reportContent,
        });

        if (!response.ok) {
            throw new Error('Failed to generate zip file');
        }

        // Download the zip file
        const blob = await response.blob();
        const zipFile = new File([blob], `${displayName.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_report.zip`);
        downloadFile(zipFile);
    } catch (error) {
        console.error('Error generating report:', error);
        alert('An error occurred while generating the report.');
    }
}

async function generateMarkdownReport(person, displayName) {
    let report = `# OSINT Report for ${displayName}\n\n`;
    report += `## Basic Information\n`;
    report += `- **ID:** ${person.id}\n`;
    report += `- **Created At:** ${new Date(person.created_at).toLocaleString()}\n\n`;

    // Add all sections and fields
    if (person.profile) {
        for (const sectionId in person.profile) {
            const sectionTitle = sectionId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            // Skip tagged_people and transitive_relationships fields (handled as tables below)
            if (
                    (sectionId === "Tagged People")
                ) {
                    continue;
                }
            report += `## ${sectionTitle}\n\n`;
            
            const sectionData = person.profile[sectionId];
            for (const fieldId in sectionData) {

                const fieldTitle = fieldId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                const fieldValue = sectionData[fieldId];
                
                if (!fieldValue || (Array.isArray(fieldValue) && fieldValue.length === 0)) continue;
                
                report += `### ${fieldTitle}\n`;
                
                const values = Array.isArray(fieldValue) ? fieldValue : [fieldValue];
                values.forEach(value => {
                    if (typeof value === 'object') {
                        report += '```json\n';
                        report += JSON.stringify(value, null, 2);
                        report += '\n```\n\n';
                    } else {
                        report += `- ${value}\n`;
                    }
                });
                report += '\n';
            }
        }
    }

    // Fetch all people to resolve names and compute relationships
    let allPeople = [];
    try {
        allPeople = await fetch('/get_people').then(r => r.json());
    } catch (e) {
        // fallback: just show IDs
        allPeople = [];
    }
    const peopleMap = {};
    allPeople.forEach(p => { peopleMap[p.id] = p; });

    // Tagged People Table
    const taggedIds = person.profile?.["Tagged People"]?.tagged_people || [];
    if (taggedIds.length > 0) {
        report += `## Tagged People\n\n`;
        report += `| Name | ID |\n|---|---|\n`;
        taggedIds.forEach(id => {
            const taggedPerson = peopleMap[id];
            const name = taggedPerson ? getDisplayName(taggedPerson) : "Unknown";
            report += `| ${name} | ${id} |\n`;
        });
        report += '\n';
    }

    // Transitive Relationships Table (mirrored, with hops)
    // BFS to find transitive relationships and hops FROM this person
    const visited = {};
    const hops = {};
    const queue = [];
    visited[person.id] = true;
    hops[person.id] = 0;
    queue.push(person.id);

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

    let transitiveIds = Object.keys(hops)
        .filter(id => id !== person.id && hops[id] > 1);

    // Symmetric: check if this person is in anyone else's transitive relationships
    allPeople.forEach(otherPerson => {
        if (otherPerson.id === person.id) return;
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
        if (otherHops[person.id] > 1 && !transitiveIds.includes(otherPerson.id)) {
            transitiveIds.push(otherPerson.id);
            hops[otherPerson.id] = otherHops[person.id];
        }
    });

    if (transitiveIds.length > 0) {
        report += `## Transitive Relationships\n\n`;
        report += `| Name | ID | Hops |\n|---|---|---|\n`;
        transitiveIds.forEach(id => {
            const relatedPerson = peopleMap[id];
            const name = relatedPerson ? getDisplayName(relatedPerson) : "Unknown";
            report += `| ${name} | ${id} | ${hops[id]} |\n`;
        });
        report += '\n';
    }

    return report;
}

function downloadFile(file) {
    const url = URL.createObjectURL(file);
    const a = document.createElement('a');
    a.href = url;
    a.download = file.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}