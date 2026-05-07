/**
 * Sankey Diagram Plugin for Basset Hound
 *
 * Visualizes entity flow and relationships using a Sankey diagram
 * showing how entities connect and interact.
 */

class SankeyDiagramPlugin extends PluginAPIBridge {
    async execute(graphData, options = {}) {
        try {
            const { nodes, edges, stats } = graphData;

            if (!nodes || !edges) {
                return {
                    status: 'error',
                    error: 'Invalid graph data format',
                };
            }

            // Transform graph data to Sankey format
            const sankeyData = this.transformToSankey(nodes, edges);

            // Generate Sankey diagram
            const html = this.generateSankeyHTML(sankeyData, options);

            return {
                status: 'success',
                data: {
                    html,
                    nodeCount: nodes.length,
                    edgeCount: edges.length,
                    flowCount: sankeyData.flows.length,
                },
            };

        } catch (error) {
            this.log('error', 'Execution failed', error);
            return {
                status: 'error',
                error: error.message,
            };
        }
    }

    /**
     * Transform graph data to Sankey format
     */
    transformToSankey(nodes, edges) {
        // Group nodes by entity type
        const nodesByType = {};
        nodes.forEach(node => {
            const type = node.type || 'Unknown';
            if (!nodesByType[type]) {
                nodesByType[type] = [];
            }
            nodesByType[type].push(node);
        });

        // Create flows from edges
        const flows = edges.map(edge => ({
            source: edge.source,
            target: edge.target,
            value: edge.weight || 1,
            type: edge.type || 'relationship',
        }));

        // Aggregate flows by type
        const aggregatedFlows = {};
        flows.forEach(flow => {
            const key = `${flow.source}-${flow.target}`;
            if (!aggregatedFlows[key]) {
                aggregatedFlows[key] = { ...flow, count: 0 };
            }
            aggregatedFlows[key].count++;
            aggregatedFlows[key].value = Math.max(aggregatedFlows[key].value, flow.value);
        });

        return {
            nodesByType,
            flows: Object.values(aggregatedFlows),
            totalNodes: nodes.length,
            totalFlows: flows.length,
        };
    }

    /**
     * Generate HTML for Sankey visualization
     */
    generateSankeyHTML(data, options = {}) {
        const width = options.width || 800;
        const height = options.height || 600;
        const colors = options.colors || ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8'];

        // Create SVG structure
        let html = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">`;
        html += '<defs><style>.sankey-label { font-size: 12px; } .sankey-flow { opacity: 0.5; }</style></defs>';

        // Calculate layout
        const nodeTypes = Object.keys(data.nodesByType);
        const xSpacing = width / (nodeTypes.length + 1);
        const positions = {};

        let colorIndex = 0;
        nodeTypes.forEach((type, idx) => {
            const x = xSpacing * (idx + 1);
            const nodesOfType = data.nodesByType[type];
            const ySpacing = height / (nodesOfType.length + 1);

            nodesOfType.forEach((node, nodeIdx) => {
                const y = ySpacing * (nodeIdx + 1);
                positions[node.id] = { x, y, type };

                // Draw node
                const color = colors[colorIndex % colors.length];
                html += `<circle cx="${x}" cy="${y}" r="8" fill="${color}" />`;
                html += `<text x="${x + 15}" y="${y + 4}" class="sankey-label">${node.name || node.id}</text>`;
            });

            colorIndex++;
        });

        // Draw flows
        data.flows.slice(0, Math.min(data.flows.length, 50)).forEach(flow => {
            const source = positions[flow.source];
            const target = positions[flow.target];

            if (source && target) {
                const color = this.getFlowColor(flow.type);
                const opacity = Math.min(0.8, flow.value / 10);

                // Draw bezier curve for flow
                const cp1x = (source.x + target.x) / 2;
                const cp1y = source.y;
                const cp2x = (source.x + target.x) / 2;
                const cp2y = target.y;

                html += `<path d="M ${source.x} ${source.y} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${target.x} ${target.y}" `;
                html += `stroke="${color}" stroke-width="${Math.max(1, flow.value / 5)}" fill="none" opacity="${opacity}" class="sankey-flow" />`;
            }
        });

        // Add legend
        html += `<g transform="translate(10, 10)">`;
        nodeTypes.forEach((type, idx) => {
            const y = idx * 20;
            const color = colors[idx % colors.length];
            html += `<rect x="0" y="${y}" width="12" height="12" fill="${color}" />`;
            html += `<text x="20" y="${y + 10}" class="sankey-label">${type}</text>`;
        });
        html += '</g>';

        html += '</svg>';

        return html;
    }

    /**
     * Get color for flow type
     */
    getFlowColor(type) {
        const colorMap = {
            'knows': '#FF6B6B',
            'works_with': '#4ECDC4',
            'owns': '#45B7D1',
            'located_in': '#FFA07A',
            'created_by': '#98D8C8',
        };

        return colorMap[type] || '#999999';
    }
}

// Export plugin for browser environment
if (typeof window !== 'undefined') {
    // When running in plugin sandbox
    if (window.PluginAPIBridge) {
        // Create plugin instance
        const plugin = new SankeyDiagramPlugin();

        // Override execute method on plugin bridge
        PluginAPIBridge.prototype.execute = function(graphData, options) {
            return plugin.execute(graphData, options);
        };
    }
}

// Export for Node.js/build tools
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SankeyDiagramPlugin;
}
