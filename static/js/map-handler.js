/**
 * Map Handler for Basset Hound
 *
 * Renders an interactive network graph of entity relationships
 * centered on a specific entity using Cytoscape.js.
 *
 * Features:
 * - Interactive layout switching (COSE, Breadthfirst, Circle, Grid)
 * - Depth control (1-5 hops) with real-time re-fetching
 * - Entity type coloring (Person, Organization, Location, Group)
 * - Export to GraphML format
 * - Node/edge styling with relationship labels
 * - Hover tooltips with full entity names
 * - Click navigation to entity subgraph
 * - Responsive design for multiple screen sizes
 */

// Entity type color mapping
const ENTITY_TYPE_COLORS = {
    'person': '#3498DB',           // Blue
    'organization': '#27AE60',     // Green
    'location': '#E74C3C',         // Red
    'group': '#9B59B6',            // Purple
    'event': '#F39C12',            // Orange
    'document': '#9B59B6',         // Purple
    'other': '#95A5A6'             // Gray
};

// Cache for graph data
let cachedGraphData = null;
let cachedProjectName = null;
let cachedEntityId = null;

/**
 * Get color for entity type
 */
function getEntityTypeColor(entityType) {
    if (!entityType) return ENTITY_TYPE_COLORS['other'];
    const normalized = entityType.toLowerCase();
    return ENTITY_TYPE_COLORS[normalized] || ENTITY_TYPE_COLORS['other'];
}

/**
 * Truncate text to specified length
 */
function truncateText(text, maxLength = 15) {
    if (text.length > maxLength) {
        return text.substring(0, maxLength - 1) + '…';
    }
    return text;
}

/**
 * Calculate node degree (number of connections)
 */
function calculateNodeDegrees(elements) {
    const degrees = {};

    elements.edges.forEach(edge => {
        const source = edge.data.source;
        const target = edge.data.target;
        degrees[source] = (degrees[source] || 0) + 1;
        degrees[target] = (degrees[target] || 0) + 1;
    });

    return degrees;
}

/**
 * Create cytoscape style rules based on entity data
 */
function createStyleRules(entityId, degrees) {
    // Base styles
    const styles = [
        {
            selector: 'node',
            style: {
                'background-color': function(node) {
                    const entityType = node.data('properties')?.entity_type || 'person';
                    return getEntityTypeColor(entityType);
                },
                'label': function(node) {
                    return truncateText(node.data('label'), 15);
                },
                'text-valign': 'bottom',
                'text-halign': 'center',
                'font-size': '11px',
                'text-margin-y': 5,
                'width': function(node) {
                    // Size proportional to centrality score if available, otherwise degree
                    const centralityScore = node.data('centrality_score');
                    if (centralityScore !== undefined) {
                        // Centrality score is typically 0-1, scale it up
                        return 30 + (centralityScore * 40);
                    }
                    const degree = degrees[node.id()] || 0;
                    return 30 + Math.min(degree * 3, 25);
                },
                'height': function(node) {
                    // Size proportional to centrality score if available, otherwise degree
                    const centralityScore = node.data('centrality_score');
                    if (centralityScore !== undefined) {
                        return 30 + (centralityScore * 40);
                    }
                    const degree = degrees[node.id()] || 0;
                    return 30 + Math.min(degree * 3, 25);
                },
                'border-width': 2,
                'border-color': '#333',
                'text-wrap': 'wrap',
                'overlay-padding': 5,
                'overlay-opacity': 0
            }
        },
        {
            // Highlight the center entity
            selector: `node[id = "${entityId}"]`,
            style: {
                'background-color': '#F39C12',
                'border-color': '#D68910',
                'border-width': 3,
                'width': 60,
                'height': 60,
                'font-weight': 'bold',
                'font-size': '12px',
                'z-index': 10,
                'overlay-padding': 8,
                'overlay-color': '#FFD700',
                'overlay-opacity': 0.3
            }
        },
        {
            selector: 'edge',
            style: {
                'width': function(edge) {
                    // Vary width based on properties
                    const confidence = edge.data('properties')?.confidence || 'medium';
                    if (confidence === 'high') return 3;
                    if (confidence === 'low') return 1;
                    return 2;
                },
                'line-color': function(edge) {
                    const confidence = edge.data('properties')?.confidence || 'medium';
                    if (confidence === 'high') return '#27AE60';
                    if (confidence === 'low') return '#BDC3C7';
                    return '#95A5A6';
                },
                'target-arrow-color': '#7F8C8D',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'label': function(edge) {
                    // Display relationship type formatted
                    return formatRelationshipType(edge.data('label') || edge.data('type') || '');
                },
                'font-size': '10px',
                'font-weight': 500,
                'text-rotation': 'autorotate',
                'text-margin-y': -10,
                'color': '#333',
                'text-background-color': '#FFF',
                'text-background-opacity': 0.9,
                'text-background-padding': '3px',
                'text-border-color': '#999',
                'text-border-width': '0.5px'
            }
        },
        {
            selector: 'node:selected',
            style: {
                'border-width': 4,
                'border-color': '#2ECC71',
                'overlay-opacity': 0.5,
                'overlay-color': '#2ECC71'
            }
        },
        {
            selector: 'edge:selected',
            style: {
                'line-color': '#2ECC71',
                'width': 4
            }
        },
        {
            selector: 'node:hover',
            style: {
                'border-width': 3,
                'border-color': '#2ECC71',
                'overlay-opacity': 0.3,
                'overlay-color': '#2ECC71'
            }
        }
    ];

    return styles;
}

async function fetchGraphData(projectSafeName, entityId, depth = 2) {
    // Check cache first
    if (cachedGraphData && cachedProjectName === projectSafeName &&
        cachedEntityId === entityId) {
        return cachedGraphData;
    }

    try {
        // Fetch centrality analysis to identify important nodes
        const centralityResponse = await fetch(
            `/api/v1/projects/${projectSafeName}/graph/analytics/centrality?algorithm=BETWEENNESS&limit=${Math.min(depth * 10, 50)}`
        );
        if (!centralityResponse.ok) {
            throw new Error(`Failed to fetch centrality data: ${centralityResponse.statusText}`);
        }
        const centralityData = await centralityResponse.json();

        // Collect all entity IDs to fetch paths for (center + top central entities)
        const entityIds = new Set([entityId]);
        if (centralityData.data && centralityData.data.results) {
            centralityData.data.results.slice(0, Math.min(depth * 5, 20)).forEach(result => {
                entityIds.add(result.entity_id);
            });
        }

        // Fetch the center entity's subgraph as the base
        const subgraphResponse = await fetch(
            `/api/v1/projects/${projectSafeName}/graph/entity/${entityId}?format=cytoscape&depth=${depth}`
        );
        if (!subgraphResponse.ok) {
            throw new Error(`Failed to fetch subgraph data: ${subgraphResponse.statusText}`);
        }
        const subgraphData = await subgraphResponse.json();

        // Enhance the subgraph with centrality scores
        if (centralityData.data && centralityData.data.results) {
            const centralityMap = {};
            centralityData.data.results.forEach(result => {
                centralityMap[result.entity_id] = result.score;
            });

            // Augment nodes with centrality scores
            if (subgraphData.elements && subgraphData.elements.nodes) {
                subgraphData.elements.nodes.forEach(node => {
                    if (centralityMap[node.data.id]) {
                        node.data.centrality_score = centralityMap[node.data.id];
                    }
                });
            }
        }

        // Cache the data
        cachedGraphData = subgraphData;
        cachedProjectName = projectSafeName;
        cachedEntityId = entityId;

        return subgraphData;

    } catch (error) {
        // Fallback: try the direct entity endpoint if new endpoints fail
        console.warn('New graph endpoints failed, trying fallback:', error.message);
        try {
            const response = await fetch(
                `/api/v1/projects/${projectSafeName}/graph/entity/${entityId}?format=cytoscape&depth=${depth}`
            );
            if (!response.ok) {
                throw new Error(`Failed to fetch graph data: ${response.statusText}`);
            }

            const data = await response.json();
            cachedGraphData = data;
            cachedProjectName = projectSafeName;
            cachedEntityId = entityId;

            return data;
        } catch (fallbackError) {
            throw new Error(`Graph data fetch failed: ${error.message}, Fallback failed: ${fallbackError.message}`);
        }
    }
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

/**
 * Debounce function for depth slider changes
 */
function debounce(func, delay) {
    let timeoutId = null;
    return function(...args) {
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => {
            func.apply(this, args);
        }, delay);
    };
}

/**
 * Clamp a number between min and max
 */
function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

/**
 * Export graph to GraphML format
 */
async function exportGraphML(projectSafeName) {
    try {
        const response = await fetch(
            `/api/v1/projects/${projectSafeName}/export/graphml`,
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    include_properties: true
                })
            }
        );
        if (!response.ok) {
            throw new Error(`Export failed: ${response.statusText}`);
        }

        // Get filename from headers if available
        const contentDisposition = response.headers.get('content-disposition');
        let filename = 'graph.graphml';
        if (contentDisposition) {
            const matches = contentDisposition.match(/filename="([^"]+)"/);
            if (matches) filename = matches[1];
        }

        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

    } catch (error) {
        console.error('Export failed:', error);
        alert(`Export failed: ${error.message}`);
    }
}

/**
 * Format relationship type for display
 */
function formatRelationshipType(relType) {
    if (!relType) return '';
    // Convert SNAKE_CASE to Title Case
    return relType
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ');
}

/**
 * Change graph layout
 */
function changeLayout(cy, layoutName) {
    const layout = cy.layout({
        name: layoutName,
        animate: true,
        animationDuration: 500,
        fit: true,
        padding: 50,
        ...(layoutName === 'cose' && {
            nodeRepulsion: function(node) { return 8000; },
            idealEdgeLength: function(edge) { return 100; },
            edgeElasticity: function(edge) { return 100; },
            gravity: 0.25,
            numIter: 1000
        }),
        ...(layoutName === 'breadthfirst' && {
            directed: false,
            roots: false
        }),
        ...(layoutName === 'circle' && {
            radius: 300
        }),
        ...(layoutName === 'grid' && {
            condense: true,
            rows: 5
        })
    });

    layout.run();
}

/**
 * Center view on entity
 */
function centerView(cy, entityId) {
    const centerNode = cy.getElementById(entityId);
    if (centerNode.length > 0) {
        cy.animate({
            center: { eles: centerNode },
            zoom: 1.2
        }, {
            duration: 300
        });
    }
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
        if (!graphData.elements || !graphData.elements.nodes || graphData.elements.nodes.length === 0) {
            container.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#666;">No connections found for this entity.</div>';
            return;
        }

        // Calculate node degrees for sizing
        const degrees = calculateNodeDegrees(graphData.elements);

        // Initialize Cytoscape with the graph data
        const cy = cytoscape({
            container: container,
            elements: graphData.elements,
            style: createStyleRules(entityId, degrees),
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
            centerView(cy, entityId);
        });

        // Add click handler to navigate to entity details
        cy.on('tap', 'node', function(evt) {
            const node = evt.target;
            const nodeId = node.id();
            if (nodeId) {
                // If center node is clicked, open entity detail panel
                if (nodeId === entityId) {
                    // Open entity detail in the entity detail page/panel
                    window.location.href = `/dashboard.html?entityId=${nodeId}&project=${projectSafeName}`;
                } else {
                    // Navigate to the clicked entity's map view
                    window.location.href = `/map.html?project=${projectSafeName}&personId=${nodeId}&depth=${depth}`;
                }
            }
        });

        // Add hover effect - show tooltip on hover
        cy.on('mouseover', 'node', function(evt) {
            document.body.style.cursor = 'pointer';
            const node = evt.target;
            const fullName = node.data('label');
            const entityType = node.data('properties')?.entity_type || 'unknown';

            // Create and show tooltip
            const tooltip = document.createElement('div');
            tooltip.className = 'graph-tooltip';
            tooltip.textContent = `${fullName} (${entityType.charAt(0).toUpperCase() + entityType.slice(1)})`;
            tooltip.style.position = 'fixed';
            tooltip.style.backgroundColor = '#333';
            tooltip.style.color = '#fff';
            tooltip.style.padding = '8px 12px';
            tooltip.style.borderRadius = '4px';
            tooltip.style.fontSize = '12px';
            tooltip.style.zIndex = '1000';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.whiteSpace = 'nowrap';
            tooltip.id = 'graph-tooltip';

            document.body.appendChild(tooltip);

            // Position tooltip at mouse position
            document.addEventListener('mousemove', function positionTooltip(e) {
                tooltip.style.left = (e.clientX + 10) + 'px';
                tooltip.style.top = (e.clientY + 10) + 'px';
            });
        });

        cy.on('mouseout', 'node', function(evt) {
            document.body.style.cursor = 'default';
            const tooltip = document.getElementById('graph-tooltip');
            if (tooltip) {
                tooltip.remove();
            }
        });

        // Setup controls
        setupControls(cy, projectSafeName, entityId, depth);

        // Add title with entity name
        const entityName = await fetchEntityName(projectSafeName, entityId);
        document.title = `Network Map: ${entityName}`;

    } catch (error) {
        console.error('Error rendering graph:', error);
        container.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#c00;">Error loading graph: ${error.message}</div>`;
    }
}

/**
 * Setup the controls panel
 */
function setupControls(cy, projectSafeName, entityId, currentDepth) {
    const controlsPanel = document.getElementById('controls-panel');

    // Depth slider
    const depthSlider = document.getElementById('depth-slider');
    depthSlider.value = currentDepth;

    const debouncedDepthChange = debounce(async (newDepth) => {
        // Update URL
        const newUrl = `/map.html?project=${projectSafeName}&personId=${entityId}&depth=${newDepth}`;
        window.history.pushState({}, '', newUrl);

        // Re-render graph
        await renderGraph(projectSafeName, entityId, newDepth);
    }, 500);

    depthSlider.addEventListener('change', (e) => {
        const newDepth = parseInt(e.target.value, 10);
        document.getElementById('depth-value').textContent = newDepth;
        debouncedDepthChange(newDepth);
    });

    depthSlider.addEventListener('input', (e) => {
        document.getElementById('depth-value').textContent = e.target.value;
    });

    // Layout selector
    const layoutSelector = document.getElementById('layout-selector');
    layoutSelector.addEventListener('change', (e) => {
        changeLayout(cy, e.target.value);
    });

    // Center button
    document.getElementById('center-btn').addEventListener('click', () => {
        centerView(cy, entityId);
    });

    // Export button
    document.getElementById('export-btn').addEventListener('click', async () => {
        const btn = document.getElementById('export-btn');
        const originalText = btn.textContent;
        btn.textContent = 'Exporting...';
        btn.disabled = true;
        try {
            await exportGraphML(projectSafeName);
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    });

    // Reset view button
    document.getElementById('reset-view-btn').addEventListener('click', () => {
        cy.fit(cy.elements(), 50);
    });

    // Fullscreen button
    document.getElementById('fullscreen-btn').addEventListener('click', () => {
        const graphContainer = document.getElementById('graph-container');
        if (!document.fullscreenElement) {
            graphContainer.requestFullscreen().catch(err => {
                console.error(`Error attempting to enable fullscreen: ${err.message}`);
            });
        } else {
            document.exitFullscreen();
        }
    });
}

/**
 * Open map view centered on a specific entity
 * This can be called from entity detail panels
 */
window.openEntityInGraph = function(entityId, projectSafeName, depth = 2) {
    if (!entityId) {
        console.error('openEntityInGraph: Missing entityId');
        return;
    }
    const project = projectSafeName || 'default';
    const d = clamp(depth, 1, 5);
    window.location.href = `/map.html?project=${project}&personId=${entityId}&depth=${d}`;
};

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