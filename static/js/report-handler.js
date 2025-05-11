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
        const reportContent = generateMarkdownReport(person, displayName);

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

function generateMarkdownReport(person, displayName) {
    let report = `# OSINT Report for ${displayName}\n\n`;
    report += `## Basic Information\n`;
    report += `- **ID:** ${person.id}\n`;
    report += `- **Created At:** ${new Date(person.created_at).toLocaleString()}\n\n`;

    if (person.profile) {
        for (const sectionId in person.profile) {
            const sectionTitle = sectionId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
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

    // Add tagged people section if they exist
    if (person.profile?.["Tagged People"]?.tagged_people?.length > 0) {
        report += `## Tagged Connections\n\n`;
        report += `This person is connected to:\n\n`;
        person.profile["Tagged People"].tagged_people.forEach(id => {
            const taggedPerson = tagState.allPeople.find(p => p.id === id);
            if (taggedPerson) {
                report += `- ${getDisplayName(taggedPerson)} (${id})\n`;
            }
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