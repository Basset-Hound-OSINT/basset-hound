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
        const zipFile = new File([blob], `${personId}.zip`);
        downloadFile(zipFile);
    } catch (error) {
        console.error('Error generating report:', error);
        alert('An error occurred while generating the report.');
    }
}

function generateMarkdownReport(person, displayName) {
    let report = `# Report for ${displayName}\n\n`;
    report += `**ID:** ${person.id}\n`;
    report += `**Created At:** ${person.created_at}\n\n`;

    if (person.profile) {
        for (const sectionId in person.profile) {
            report += `## ${sectionId}\n\n`;
            const sectionData = person.profile[sectionId];
            for (const fieldId in sectionData) {
                const fieldValue = sectionData[fieldId];
                report += `- **${fieldId}:** ${JSON.stringify(fieldValue, null, 2)}\n`;
            }
            report += '\n';
        }
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