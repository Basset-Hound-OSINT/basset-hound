/**
 * Timeline Visualization Plugin for Basset Hound
 *
 * Visualizes entities and their relationships along a timeline
 * showing temporal progression and event sequencing.
 */

class TimelineVisualizationPlugin extends PluginAPIBridge {
    async execute(graphData, options = {}) {
        try {
            const { nodes, edges, stats } = graphData;

            if (!nodes || !edges) {
                return {
                    status: 'error',
                    error: 'Invalid graph data format',
                };
            }

            // Extract temporal data
            const timelineData = this.extractTimelineData(nodes, edges, options);

            // Generate timeline HTML
            const html = this.generateTimelineHTML(timelineData, options);

            return {
                status: 'success',
                data: {
                    html,
                    eventCount: timelineData.events.length,
                    timeRange: {
                        start: timelineData.minTime,
                        end: timelineData.maxTime,
                    },
                    entities: timelineData.entities.length,
                },
            };

        } catch (error) {
            this.log('error', 'Timeline generation failed', error);
            return {
                status: 'error',
                error: error.message,
            };
        }
    }

    /**
     * Extract temporal data from graph
     */
    extractTimelineData(nodes, edges, options) {
        // Extract entities with creation/modification dates
        const events = [];
        const entities = [];

        nodes.forEach(node => {
            if (node.created_at || node.updated_at) {
                entities.push(node);

                if (node.created_at) {
                    events.push({
                        id: node.id,
                        timestamp: new Date(node.created_at).getTime(),
                        type: 'creation',
                        entity: node.name || node.id,
                        entityType: node.type,
                        description: `Created: ${node.name || node.id}`,
                    });
                }

                if (node.updated_at) {
                    events.push({
                        id: `${node.id}_update`,
                        timestamp: new Date(node.updated_at).getTime(),
                        type: 'update',
                        entity: node.name || node.id,
                        entityType: node.type,
                        description: `Updated: ${node.name || node.id}`,
                    });
                }
            }
        });

        // Extract relationship dates
        edges.forEach(edge => {
            if (edge.created_at) {
                events.push({
                    id: edge.id,
                    timestamp: new Date(edge.created_at).getTime(),
                    type: 'relationship',
                    entity: `${edge.source} → ${edge.target}`,
                    entityType: edge.type,
                    description: `${edge.type}: ${edge.source} to ${edge.target}`,
                });
            }
        });

        // Sort by timestamp
        events.sort((a, b) => a.timestamp - b.timestamp);

        // Calculate time range
        const minTime = events.length > 0 ? events[0].timestamp : Date.now();
        const maxTime = events.length > 0 ? events[events.length - 1].timestamp : Date.now();

        return {
            events,
            entities,
            minTime,
            maxTime,
        };
    }

    /**
     * Generate HTML for timeline visualization
     */
    generateTimelineHTML(data, options = {}) {
        const width = options.width || 1000;
        const height = options.height || 400;
        const padding = 50;
        const contentWidth = width - 2 * padding;
        const contentHeight = height - 2 * padding;

        let html = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">`;
        html += '<defs><style>';
        html += '.timeline-line { stroke: #333; stroke-width: 2; }';
        html += '.timeline-tick { stroke: #999; stroke-width: 1; }';
        html += '.timeline-event { cursor: pointer; }';
        html += '.timeline-event:hover { opacity: 0.8; }';
        html += '.timeline-label { font-size: 11px; text-anchor: middle; }';
        html += '.timeline-date { font-size: 10px; fill: #666; }';
        html += '</style></defs>';

        // Draw timeline axis
        const yAxis = padding + contentHeight / 2;
        html += `<line x1="${padding}" y1="${yAxis}" x2="${width - padding}" y2="${yAxis}" class="timeline-line" />`;

        // Draw events
        if (data.events.length > 0) {
            const timeRange = data.maxTime - data.minTime || 1;

            data.events.forEach((event, idx) => {
                const ratio = (event.timestamp - data.minTime) / timeRange;
                const x = padding + ratio * contentWidth;

                // Alternate events above and below axis
                const yOffset = idx % 2 === 0 ? -40 : 40;
                const y = yAxis + yOffset;

                // Draw tick
                html += `<line x1="${x}" y1="${yAxis - 5}" x2="${x}" y2="${yAxis + 5}" class="timeline-tick" />`;

                // Draw event circle
                const color = this.getEventColor(event.type);
                html += `<circle cx="${x}" cy="${yAxis}" r="4" fill="${color}" class="timeline-event" />`;

                // Draw label
                const date = new Date(event.timestamp);
                const dateStr = date.toLocaleDateString();
                html += `<text x="${x}" y="${y}" class="timeline-label">${event.entity.substring(0, 15)}</text>`;
                html += `<text x="${x}" y="${y + 15}" class="timeline-date">${dateStr}</text>`;

                // Draw connector line
                html += `<line x1="${x}" y1="${yAxis}" x2="${x}" y2="${y + 5}" stroke="${color}" stroke-width="1" opacity="0.5" />`;
            });
        }

        // Draw legend
        html += '<g transform="translate(10, 10)">';
        const eventTypes = ['creation', 'update', 'relationship'];
        eventTypes.forEach((type, idx) => {
            const y = idx * 20;
            const color = this.getEventColor(type);
            html += `<circle cx="6" cy="${y + 6}" r="4" fill="${color}" />`;
            html += `<text x="20" y="${y + 10}" style="font-size: 12px;">${type}</text>`;
        });
        html += '</g>';

        // Add title
        html += `<text x="${width / 2}" y="20" style="font-size: 14px; font-weight: bold; text-anchor: middle;">Timeline of Events (${data.events.length} events)</text>`;

        html += '</svg>';

        return html;
    }

    /**
     * Get color for event type
     */
    getEventColor(type) {
        const colorMap = {
            'creation': '#4ECDC4',
            'update': '#FFE66D',
            'relationship': '#FF6B6B',
        };

        return colorMap[type] || '#999999';
    }
}

// Export plugin for browser environment
if (typeof window !== 'undefined') {
    if (window.PluginAPIBridge) {
        const plugin = new TimelineVisualizationPlugin();

        PluginAPIBridge.prototype.execute = function(graphData, options) {
            return plugin.execute(graphData, options);
        };
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = TimelineVisualizationPlugin;
}
