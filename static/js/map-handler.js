/**
 * Map Handler for Basset Hound
 *
 * Renders an interactive network graph of entity relationships
 * centered on a specific entity using Cytoscape.js.
 */

async function fetchGraphData(projectSafeName, entityId, depth = 2) {
    const response = await fetch(
        `/api/v1/projects/${projectSafeName}/graph/entity/${entityId}?format=cytoscape&depth=${depth}`
    );
    if (!response.ok) {
        throw new Error(`Failed to fetch graph data: ${response.statusText}`);
    }
    return response.json();
}

async function fetchEntityName(projectSafeName, entityId) {
    try {
        const response = await fetch(`/api/v1/projects/${projectSafeName}/people/${entityId}`);
        if (response.ok) {
            const entity = await response.json();
            return entity.profile?.core?.name || entity.id;
        }
    } catch (e) {
        console.warn('Could not fetch entity name:', e);
    }
    return entityId;
}

async function renderGraph(projectSafeName, entityId, depth = 2) {
    const container = document.getElementById('graph-container');

    // Show loading state
    container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#666;">Loading graph...</div>';

    try {
        const graphData = await fetchGraphData(projectSafeName, entityId, depth);

        // Clear container for Cytoscape
        container.innerHTML = '';

        // Handle empty graph
        if (!graphData.elements || graphData.elements.length === 0) {
            container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#666;">No connections found for this entity.</div>';
            return;
        }

        // Initialize Cytoscape with the graph data
        const cy = cytoscape({
            container: container,
            elements: graphData.elements,
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': '#4A90D9',
                        'label': 'data(label)',
                        'text-valign': 'bottom',
                        'text-halign': 'center',
                        'font-size': '11px',
                        'text-margin-y': 5,
                        'width': 40,
                        'height': 40,
                        'border-width': 2,
                        'border-color': '#2E5D8C'
                    }
                },
                {
                    // Highlight the center entity
                    selector: `node[id = "${entityId}"]`,
                    style: {
                        'background-color': '#E67E22',
                        'border-color': '#D35400',
                        'width': 55,
                        'height': 55,
                        'font-weight': 'bold',
                        'font-size': '13px',
                        'z-index': 10
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#95A5A6',
                        'target-arrow-color': '#7F8C8D',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': '9px',
                        'text-rotation': 'autorotate',
                        'text-margin-y': -10,
                        'color': '#555'
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'border-width': 4,
                        'border-color': '#2ECC71'
                    }
                }
            ],
            layout: {
                name: 'cose',
                animate: true,
                animationDuration: 500,
                fit: true,
                padding: 50,
                nodeRepulsion: function(node) { return 8000; },
                idealEdgeLength: function(edge) { return 100; },
                edgeElasticity: function(edge) { return 100; },
                gravity: 0.25,
                numIter: 1000
            },
            minZoom: 0.2,
            maxZoom: 3,
            wheelSensitivity: 0.3
        });

        // After layout completes, center on the target entity
        cy.on('layoutstop', () => {
            const centerNode = cy.getElementById(entityId);
            if (centerNode.length > 0) {
                cy.animate({
                    center: { eles: centerNode },
                    zoom: 1.2
                }, {
                    duration: 300
                });
            }
        });

        // Add click handler to navigate to entity details
        cy.on('tap', 'node', function(evt) {
            const nodeId = evt.target.id();
            if (nodeId && nodeId !== entityId) {
                // Navigate to the clicked entity's map view
                window.location.href = `/map.html?project=${projectSafeName}&personId=${nodeId}&depth=${depth}`;
            }
        });

        // Add hover effects
        cy.on('mouseover', 'node', function(evt) {
            document.body.style.cursor = 'pointer';
            evt.target.style({
                'border-width': 4
            });
        });

        cy.on('mouseout', 'node', function(evt) {
            document.body.style.cursor = 'default';
            const isCenter = evt.target.id() === entityId;
            evt.target.style({
                'border-width': isCenter ? 2 : 2
            });
        });

        // Add title with entity name
        const entityName = await fetchEntityName(projectSafeName, entityId);
        document.title = `Network Map: ${entityName}`;

    } catch (error) {
        console.error('Error rendering graph:', error);
        container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#c00;">Error loading graph: ${error.message}</div>`;
    }
}

// Get parameters from URL query string
const urlParams = new URLSearchParams(window.location.search);
const personId = urlParams.get('personId');
const projectSafeName = urlParams.get('project') || 'default';
const depth = parseInt(urlParams.get('depth') || '2', 10);

if (personId) {
    renderGraph(projectSafeName, personId, depth);
} else {
    document.getElementById('graph-container').innerHTML =
        '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#c00;">Error: No personId specified in URL</div>';
}