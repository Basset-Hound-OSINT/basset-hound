/**
 * Network Statistics Dashboard Plugin for Basset Hound
 *
 * Analyzes and displays comprehensive network metrics including:
 * - Degree centrality, betweenness, closeness
 * - Clustering coefficient
 * - Network density
 * - Component analysis
 */

class NetworkStatisticsPlugin extends PluginAPIBridge {
    async execute(graphData, options = {}) {
        try {
            const { nodes, edges, stats } = graphData;

            if (!nodes || !edges) {
                return {
                    status: 'error',
                    error: 'Invalid graph data format',
                };
            }

            // Calculate network metrics
            const metrics = this.calculateMetrics(nodes, edges, options);

            // Generate dashboard HTML
            const html = this.generateDashboardHTML(metrics, options);

            return {
                status: 'success',
                data: {
                    html,
                    metrics: {
                        nodes: metrics.nodeCount,
                        edges: metrics.edgeCount,
                        density: metrics.density.toFixed(3),
                        avgDegree: metrics.avgDegree.toFixed(2),
                        components: metrics.components,
                    },
                },
            };

        } catch (error) {
            this.log('error', 'Dashboard generation failed', error);
            return {
                status: 'error',
                error: error.message,
            };
        }
    }

    /**
     * Calculate network metrics
     */
    calculateMetrics(nodes, edges, options) {
        const nodeCount = nodes.length;
        const edgeCount = edges.length;

        // Build adjacency list
        const adjacencyList = {};
        nodes.forEach(node => {
            adjacencyList[node.id] = [];
        });

        edges.forEach(edge => {
            adjacencyList[edge.source]?.push(edge.target);
            adjacencyList[edge.target]?.push(edge.source); // Undirected
        });

        // Calculate degree metrics
        const degrees = Object.values(adjacencyList).map(neighbors => neighbors.length);
        const avgDegree = degrees.length > 0 ? degrees.reduce((a, b) => a + b, 0) / degrees.length : 0;
        const maxDegree = Math.max(...degrees, 0);
        const minDegree = Math.min(...degrees, 0);

        // Calculate density
        const maxPossibleEdges = (nodeCount * (nodeCount - 1)) / 2;
        const density = maxPossibleEdges > 0 ? edgeCount / maxPossibleEdges : 0;

        // Calculate clustering coefficient
        const clusteringCoefficients = [];
        nodes.forEach(node => {
            const neighbors = adjacencyList[node.id] || [];
            if (neighbors.length >= 2) {
                let connectedNeighbors = 0;
                for (let i = 0; i < neighbors.length; i++) {
                    for (let j = i + 1; j < neighbors.length; j++) {
                        if (adjacencyList[neighbors[i]]?.includes(neighbors[j])) {
                            connectedNeighbors++;
                        }
                    }
                }
                const possibleConnections = (neighbors.length * (neighbors.length - 1)) / 2;
                clusteringCoefficients.push(connectedNeighbors / possibleConnections);
            }
        });

        const avgClusteringCoefficient = clusteringCoefficients.length > 0
            ? clusteringCoefficients.reduce((a, b) => a + b, 0) / clusteringCoefficients.length
            : 0;

        // Find connected components using DFS
        const visited = new Set();
        let components = 0;
        const dfs = (nodeId) => {
            visited.add(nodeId);
            (adjacencyList[nodeId] || []).forEach(neighbor => {
                if (!visited.has(neighbor)) {
                    dfs(neighbor);
                }
            });
        };

        nodes.forEach(node => {
            if (!visited.has(node.id)) {
                components++;
                dfs(node.id);
            }
        });

        // Node types distribution
        const typeDistribution = {};
        nodes.forEach(node => {
            const type = node.type || 'Unknown';
            typeDistribution[type] = (typeDistribution[type] || 0) + 1;
        });

        // Top nodes by degree
        const topNodes = nodes
            .map(node => ({
                name: node.name || node.id,
                degree: (adjacencyList[node.id] || []).length,
                type: node.type,
            }))
            .sort((a, b) => b.degree - a.degree)
            .slice(0, 10);

        return {
            nodeCount,
            edgeCount,
            avgDegree,
            maxDegree,
            minDegree,
            density,
            avgClusteringCoefficient,
            components,
            typeDistribution,
            topNodes,
        };
    }

    /**
     * Generate dashboard HTML
     */
    generateDashboardHTML(metrics, options = {}) {
        const width = options.width || 1000;
        const height = options.height || 700;

        let html = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">`;
        html += '<defs><style>';
        html += '.stat-title { font-size: 14px; font-weight: bold; fill: #333; }';
        html += '.stat-value { font-size: 24px; font-weight: bold; fill: #0066cc; }';
        html += '.stat-label { font-size: 11px; fill: #666; }';
        html += '.bar { fill: #4ECDC4; }';
        html += '.chart-title { font-size: 13px; font-weight: bold; fill: #333; }';
        html += '</style></defs>';

        let yPos = 20;
        const rowHeight = 80;
        const colWidth = width / 2;

        // Title
        html += `<text x="10" y="${yPos}" style="font-size: 18px; font-weight: bold;">Network Statistics Dashboard</text>`;
        yPos += 30;

        // Main metrics row 1
        html += this.drawStatBox(10, yPos, 'Nodes', metrics.nodeCount.toString(), '');
        html += this.drawStatBox(colWidth, yPos, 'Edges', metrics.edgeCount.toString(), '');

        // Main metrics row 2
        yPos += rowHeight;
        html += this.drawStatBox(10, yPos, 'Density', metrics.density.toFixed(3), 'Network edge density');
        html += this.drawStatBox(colWidth, yPos, 'Avg Degree', metrics.avgDegree.toFixed(2), 'Average connections per node');

        // Main metrics row 3
        yPos += rowHeight;
        html += this.drawStatBox(10, yPos, 'Clustering', metrics.avgClusteringCoefficient.toFixed(3), 'Average clustering coefficient');
        html += this.drawStatBox(colWidth, yPos, 'Components', metrics.components.toString(), 'Connected components');

        // Degree range
        yPos += rowHeight;
        html += `<text x="10" y="${yPos + 15}" class="chart-title">Degree Range</text>`;
        html += `<text x="10" y="${yPos + 35}" class="stat-label">Min: ${metrics.minDegree} | Max: ${metrics.maxDegree}</text>`;

        // Entity type distribution
        yPos += 60;
        html += `<text x="10" y="${yPos}" class="chart-title">Entity Type Distribution</text>`;
        yPos += 20;

        let typeX = 10;
        Object.entries(metrics.typeDistribution).slice(0, 5).forEach(([type, count]) => {
            const barHeight = Math.max(1, (count / Math.max(...Object.values(metrics.typeDistribution))) * 40);
            const barY = yPos + 40 - barHeight;

            html += `<rect x="${typeX}" y="${barY}" width="15" height="${barHeight}" class="bar" />`;
            html += `<text x="${typeX + 8}" y="${yPos + 50}" text-anchor="middle" class="stat-label">${type.substring(0, 3)}</text>`;
            html += `<text x="${typeX + 8}" y="${yPos + 35}" text-anchor="middle" class="stat-label" font-size="10">${count}</text>`;

            typeX += 25;
        });

        // Top nodes
        yPos += 80;
        html += `<text x="10" y="${yPos}" class="chart-title">Top 5 Most Connected Nodes</text>`;
        yPos += 20;

        metrics.topNodes.slice(0, 5).forEach((node, idx) => {
            const y = yPos + idx * 20;
            html += `<text x="10" y="${y}" class="stat-label" style="font-size: 12px;">${idx + 1}. ${node.name.substring(0, 30)} (degree: ${node.degree})</text>`;
        });

        html += '</svg>';

        return html;
    }

    /**
     * Draw a statistic box
     */
    drawStatBox(x, y, label, value, description) {
        const boxWidth = 250;
        const boxHeight = 60;

        let html = `<g>`;
        html += `<rect x="${x}" y="${y}" width="${boxWidth}" height="${boxHeight}" fill="#f5f5f5" stroke="#ddd" stroke-width="1" />`;
        html += `<text x="${x + 10}" y="${y + 20}" class="stat-title">${label}</text>`;
        html += `<text x="${x + 10}" y="${y + 45}" class="stat-value">${value}</text>`;
        if (description) {
            html += `<text x="${x + 10}" y="${y + 57}" class="stat-label">${description}</text>`;
        }
        html += `</g>`;

        return html;
    }
}

// Export plugin for browser environment
if (typeof window !== 'undefined') {
    if (window.PluginAPIBridge) {
        const plugin = new NetworkStatisticsPlugin();

        PluginAPIBridge.prototype.execute = function(graphData, options) {
            return plugin.execute(graphData, options);
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = NetworkStatisticsPlugin;
}
