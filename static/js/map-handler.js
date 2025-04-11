async function fetchGraphData(personId) {
    const response = await fetch(`/get_connections/${personId}`);
    return response.json();
}

async function renderGraph(personId) {
    const graphData = await fetchGraphData(personId);

    const elements = graphData.map(connection => ({
        data: { id: connection.id }
    }));

    const edges = graphData.flatMap(connection => connection.edges);

    const cy = cytoscape({
        container: document.getElementById('graph-container'),
        elements: [...elements, ...edges],
        style: [
            { selector: 'node', style: { 'background-color': '#0074D9', label: 'data(id)' } },
            { selector: 'edge', style: { 'line-color': '#FF4136' } }
        ]
    });
}

// Get personId from query parameters
const urlParams = new URLSearchParams(window.location.search);
const personId = urlParams.get('personId');
renderGraph(personId);