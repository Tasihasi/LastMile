# Planner Guide

## Dashboard

After logging in as a planner, you see the management dashboard instead of the map.

### Layout

- **Left column**: Unassigned routes (not assigned to any biker)
- **Biker columns**: One column per registered biker, showing their assigned routes
- **Bottom section**: Finished routes (collapsed by default)

### Filtering Bikers

The dashboard header has a filter with three options:

| Filter | Shows |
|--------|-------|
| **Active Bikers** (default) | Only bikers with at least one in-progress route |
| **Inactive Bikers** | Only bikers with no active routes |
| **All Bikers** | Every registered biker |

### Route Cards

Each card shows:
- Route name (editable)
- Stop count
- Duration and distance (if optimized)
- Status badge: "In Progress" (with pulsing dot) or status indicator
- Progress: "Heading to: Stop Name" and "X/Y stops done" for active routes
- **Estimated return time**: "Back by ~14:30" on in-progress routes (calculated from start time + route duration + dwell time per stop)
- **Not received count**: warning badge on finished routes if any stops were not received

## Assigning Routes

### Drag and drop

Drag a route card from one column to another. The route is reassigned to the target biker. You can also drag a route back to the **Unassigned** column to unassign it.

### Assign button

Click the person icon on a route card to open a dropdown of all bikers. Select a biker to assign the route.

### Unassigning a route

Two ways to unassign a route from a biker:
- **Drag** the route card to the Unassigned column
- **Click the assign button** and select **Unassign** at the bottom of the dropdown (only appears when the route is currently assigned)

## Uploading Routes

Click **Upload Route** in the dashboard header. To upload directly for a specific biker, use the upload button within that biker's column.

## Renaming Routes

Click the pencil icon on a route card. The name becomes an editable text field. Press **Enter** to save or **Escape** to cancel.

## Deleting Routes

Click the trash icon on a route card. A confirmation dialog appears. This permanently deletes the route and all its stops.

## Viewing a Route

Click the eye icon on a route card to open the full map view for that route. A **Back to Dashboard** button appears in the header to return.

From the map view you can geocode, optimize, adjust settings, and share -- just like the biker view. A **Dashboard** button appears in the header to return to the management view.

## Live Map

When any routes are in progress, a **Live Map** button appears in the dashboard header showing the number of active routes.

The live map shows:
- All active biker routes on one map
- Each biker has a distinct color (shown in the legend)
- Route lines drawn in the biker's color
- Small dots for completed/pending stops
- Large pulsing marker at each biker's current stop (with biker's initial)

### Auto-refresh

The map refreshes every 30 seconds. Click the refresh button for a manual update.

### Interacting with markers

Click a biker's current-stop marker to see a popup with:
- Biker name
- Route name
- Current destination ("Heading to: ...")
- Progress (e.g., "5/10 stops done")
- Route stats

Click **View Route** in the popup to jump directly to that biker's route on the map.

## Finished Routes

Expand the **Finished Routes** section at the bottom of the dashboard. Click any finished route card to open the stats panel.

### Stats Panel

The detail panel shows:

**Summary metrics:**
- Success rate (percentage of delivered stops)
- Delivered count
- Not received count
- Skipped count (if any)

**Timeline:**
- When the route was started
- When it was finished
- Total elapsed time
- Planned route distance and duration

**Stop-by-stop breakdown:**
- Every stop listed with sequence number, status icon, name, recipient, address, and delivery status badge
- Not-received stops are highlighted in red

Click **View on Map** to see the route geographically.
