/**
 * Heat Map Plugin for Basset Hound
 *
 * Visualizes entity activity and connection density using color-coded heat maps
 * to identify high-activity areas and clusters in the network.
 */

class HeatMapPlugin extends PluginAPIBridge {
    async execute(graphData, options = {}) {
        try {
            const { nodes, edges } = graphData;

            if (!nodes || !edges) {
                return {
                    status: 'error',
                    error: 'Invalid graph data format',
                };
            }

            // Calculate activity metrics
            const heatmapData = this.calculateHeatMap(nodes, edges, options);

            // Generate heatmap HTML
            const html = this.generateHeatmapHTML(heatmapData, options);

            return {
                status: 'success',
                data: {
                    html,
                    hotspots: heatmapData.hotspots.length,
                    maxActivity: heatmapData.maxActivity,
                    avgActivity: heatmapData.avgActivity,
                },
            };

        } catch (error) {
            this.log('error', 'Heat map generation failed', error);
            return {
                status: 'error',
                error: error.message,
            };
        }
    }

    /**
     * Calculate activity metrics for heatmap
     */
    calculateHeatMap(nodes, edges, options) {
        // Calculate activity for each node
        const activityMap = {};

        nodes.forEach(node => {
            activityMap[node.id] = {
                node: node.name || node.id,
                type: node.type,
                inDegree: 0,
                outDegree: 0,
                connections: 0,
                weight: 0,
            };
        });

        // Count relationships
        edges.forEach(edge => {
            if (activityMap[edge.source]) {
                activityMap[edge.source].outDegree++;
                activityMap[edge.source].weight += edge.weight || 1;
            }
            if (activityMap[edge.target]) {
                activityMap[edge.target].inDegree++;
                activityMap[edge.target].weight += edge.weight || 1;
            }
        });

        // Calculate total activity
        const activities = Object.values(activityMap).map(a => {
            a.activity = a.inDegree + a.outDegree + (a.weight || 0);
            return a;
        });

        const activityValues = activities.map(a => a.activity);
        const maxActivity = Math.max(...activityValues, 1);
        const avgActivity = activityValues.reduce((a, b) => a + b, 0) / activityValues.length;

        // Identify hotspots (top 20% by activity)
        const sorted = [...activities].sort((a, b) => b.activity - a.activity);
        const hotspotThreshold = sorted[Math.floor(sorted.length * 0.2)]?.activity || 0;
        const hotspots = activities.filter(a => a.activity >= hotspotThreshold);

        // Create grid representation
        const entityTypes = [...new Set(nodes.map(n => n.type))];
        const grid = this.createGrid(activities, entityTypes, maxActivity);

        return {
            activities: activityMap,
            grid,
            hotspots,
            maxActivity,
            avgActivity,
            entityTypes,
        };
    }

    /**
     * Create grid for heatmap visualization
     */
    createGrid(activities, entityTypes, maxActivity) {
        const grid = [];
        const cellSize = Math.ceil(Math.sqrt(activities.length / entityTypes.length));

        let row = [];
        activities.forEach((activity, idx) => {
            row.push({
                ...activity,
                intensity: activity.activity / maxActivity,
            });

            if (row.length >= cellSize || idx === activities.length - 1) {
                grid.push(row);
                row = [];
            }
        });

        return grid;
    }

    /**
     * Generate HTML for heatmap visualization
     */
    generateHeatmapHTML(data, options = {}) {
        const cellSize = options.cellSize || 20;
        const cols = Math.max(...data.grid.map(r => r.length));
        const rows = data.grid.length;
        const width = cols * cellSize + 200;
        const height = rows * cellSize + 100;

        let html = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">`;
        html += '<defs><style>';
        html += '.heatmap-cell { stroke: #eee; stroke-width: 1; cursor: pointer; }';
        html += '.heatmap-cell:hover { opacity: 0.8; stroke: #333; }';
        html += '.heatmap-label { font-size: 9px; }';
        html += '.heatmap-title { font-size: 14px; font-weight: bold; }';
        html += '</style></defs>';

        // Title
        html += `<text x="10" y="20" class="heatmap-title">Entity Activity Heat Map</text>`;

        // Draw grid
        const padding = 20;
        data.grid.forEach((row, rowIdx) => {
            row.forEach((cell, colIdx) => {
                const x = padding + colIdx * cellSize;
                const y = padding + 30 + rowIdx * cellSize;

                // Get color based on intensity
                const color = this.getHeatColor(cell.intensity);

                // Draw cell
                html += `<rect x="${x}" y="${y}" width="${cellSize}" height="${cellSize}" fill="${color}" class="heatmap-cell" />`;

                // Show value if enabled
                if (options.showValues && cellSize > 25) {
                    const value = Math.round(cell.activity);
                    html += `<text x="${x + cellSize / 2}" y="${y + cellSize / 2 + 4}" text-anchor="middle" class="heatmap-label">${value}</text>`;
                }
            });
        });

        // Draw legend
        this.drawLegend(html, data, cellSize, padding, width);

        // Draw statistics
        const statsY = padding + 30 + (rows + 2) * cellSize;
        html += `<text x="${padding}" y="${statsY}" style="font-size: 12px;">`;
        html += `Max Activity: ${data.maxActivity.toFixed(1)} | `;
        html += `Avg Activity: ${data.avgActivity.toFixed(1)} | `;
        html += `Hotspots: ${data.hotspots.length}`;
        html += '</text>';

        html += '</svg>';

        return html;
    }

    /**
     * Draw legend for heat map
     */
    drawLegend(html, data, cellSize, padding, width) {
        const legendY = padding + 30;
        const legendX = width - 180;

        html += `<g>`;
        html += `<text x="${legendX}" y="${legendY}" style="font-size: 12px; font-weight: bold;">Legend</text>`;

        // Draw gradient legend
        const steps = 5;
        for (let i = 0; i < steps; i++) {
            const intensity = i / (steps - 1);
            const color = this.getHeatColor(intensity);
            const y = legendY + 20 + i * 15;

            html += `<rect x="${legendX}" y="${y}" width="15" height="12" fill="${color}" stroke="#ccc" />`;
            html += `<text x="${legendX + 20}" y="${y + 10}" style="font-size: 10px;">${(intensity * 100).toFixed(0)}%</text>`;
        }

        html += `</g>`;

        return html;
    }

    /**
     * Get heat color based on intensity (0-1)
     */
    getHeatColor(intensity) {
        // Viridis color scheme (purple to yellow)
        const colors = [
            '#440154', // deep purple
            '#31688e', // blue
            '#35b779', // green
            '#fde724', // yellow
        ];

        const index = Math.floor(intensity * (colors.length - 1));
        return colors[Math.min(index, colors.length - 1)];
    }
}

// Export plugin for browser environment
if (typeof window !== 'undefined') {
    if (window.PluginAPIBridge) {
        const plugin = new HeatMapPlugin();

        PluginAPIBridge.prototype.execute = function(graphData, options) {
            return plugin.execute(graphData, options);
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = HeatMapPlugin;
}
