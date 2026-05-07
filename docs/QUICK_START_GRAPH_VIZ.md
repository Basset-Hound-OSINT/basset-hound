# Quick Start: Graph Visualization

## What Was Built

An interactive network graph visualization showing entity relationships in Basset Hound using **Cytoscape.js**.

## Key Features

- **Depth Control**: Slider to explore 1-5 hops of relationships
- **4 Layout Types**: Force-Directed, Breadth-First, Circle, Grid
- **Interactive Nodes**: Click to navigate, hover for details
- **Color Coding**: By entity type (Person, Organization, Location, Group)
- **Relationship Labels**: Shows type of connection
- **Export**: Download graph as GraphML format
- **Responsive**: Works on mobile, tablet, desktop
- **Dark Mode**: Automatic dark mode support

## Getting Started

### 1. Start Docker
```bash
cd /home/devel/basset-hound
docker compose up -d
```

Wait ~30 seconds for services to be healthy.

### 2. Create Test Data
```bash
python test_graph_visualization.py
```

This creates:
- 1 test project
- 15 test entities
- 15 relationships

### 3. View Graph
The test script provides a URL like:
```
http://localhost:8080/map.html?project=test-graph-viz&personId=<id>&depth=2
```

Open it in your browser.

## Using the Visualization

### Controls (Top-Left Panel)

**Depth Slider**
- Adjust from 1 to 5 hops
- Graph re-fetches automatically
- Shows 1-5 levels of relationships

**Layout Dropdown**
- **Force-Directed**: Default, spreads nodes naturally
- **Breadth-First**: Level-based layout
- **Circle**: Circular arrangement
- **Grid**: Regular grid pattern

**Buttons**
- **Center**: Focus on main entity
- **Reset**: Fit all nodes in view
- **Export**: Download as GraphML
- **Full**: Fullscreen mode

### Interactions

**Hover a Node**
- See tooltip with entity name and type
- Cursor changes to pointer

**Click a Node**
- Center node: Opens entity detail
- Other node: Shows subgraph from that node

**Pan & Zoom**
- Drag to pan
- Scroll to zoom
- Right-click drag to rotate (some layouts)

## Color Legend

- 🔵 **Blue**: Person
- 🟢 **Green**: Organization
- 🔴 **Red**: Location
- 🟣 **Purple**: Group
- ⚫ **Gray**: Other
- 🟠 **Orange**: Center entity (highlighted)

## Examples

### Example 1: Explore Connections
1. Open graph with depth=2
2. Click a node to see what it connects to
3. Increase depth slider to see further connections

### Example 2: Change Layout
1. Select "Circle" from dropdown
2. Watch nodes rearrange in a circle
3. Try "Grid" to see a different pattern

### Example 3: Export Network
1. Click "Export" button
2. GraphML file downloads
3. Open in network analysis tools

## URL Parameters

```
/map.html?project={project_name}&personId={entity_id}&depth={1-5}
```

Example:
```
/map.html?project=my-project&personId=abc-123&depth=3
```

You can bookmark these URLs for quick access.

## From Entity Detail

In the entity detail panel (dashboard), click the **"Map" button** to:
- Open graph centered on that entity
- Opens in new browser tab
- Preserves current project

## Responsive Design

- **Mobile**: Single-column layout, stacked buttons
- **Tablet**: Flexible layout, readable controls
- **Desktop**: Full-featured layout, optimal spacing

## Performance Tips

- **10-50 nodes**: Any layout works great
- **50-100 nodes**: Stick with Force-Directed or Breadth-First
- **100+ nodes**: Use Grid or Circle layouts
- **Very large graphs**: Increase depth limit to reduce initial load

## Troubleshooting

### Graph Not Loading
1. Check URL has `personId` parameter
2. Check browser console (F12)
3. Verify service is running: `docker compose ps`

### Nodes Overlapping
1. Try different layout (Grid/Circle)
2. Increase animation duration
3. Adjust window size

### Tooltip Not Showing
1. Hover carefully on node center
2. Check browser zoom level (100%)
3. Verify CSS loaded properly

### Export Fails
1. Check project name is correct
2. Try with smaller depth (1-2)
3. Check browser download settings

## Files

**User-facing**:
- `templates/map.html` - Visualization page
- `static/js/map-handler.js` - Graph logic
- `static/css/map-controls.css` - Styling

**Testing**:
- `test_graph_visualization.py` - Test suite
- `GRAPH_VISUALIZATION_GUIDE.md` - Full documentation
- `STREAM_5_COMPLETION_REPORT.md` - Technical details

## Next Steps

1. **Deploy**: Use `docker compose up -d`
2. **Test**: Run `python test_graph_visualization.py`
3. **Explore**: Open the URLs provided
4. **Integrate**: Add to your workflow
5. **Customize**: Modify colors/layouts as needed

## Browser Support

- Chrome ✓
- Firefox ✓
- Safari ✓
- Edge ✓
- Mobile browsers ✓

## Keyboard Shortcuts

- Press 'Escape' to deselect nodes
- Use arrow keys to zoom/pan (in some cases)
- Ctrl+Plus/Minus to zoom

## Keyboard Navigation

- Tab: Navigate controls
- Enter: Click focused button
- Space: Toggle dropdown

## API Endpoints Used

```
GET /api/v1/projects/{name}/graph/entity/{id}?format=cytoscape&depth={1-5}
POST /api/v1/projects/{name}/visualization/export/graphml
```

## Questions?

See `GRAPH_VISUALIZATION_GUIDE.md` for detailed documentation.

---

**Happy exploring!** 📊
