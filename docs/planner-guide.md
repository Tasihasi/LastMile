# Planner Guide

## Dashboard

After logging in as a planner, you see the management dashboard instead of the map.

### Layout

- **Unassigned column**: Routes not assigned to any biker (including sub-routes produced by clustering a large upload)
- **Biker columns**: One column per registered biker, showing their assigned routes
- **Finished section**: Finished routes (collapsed by default)

On iPad-portrait viewports (640-768px) the dashboard shows a **2-column** layout. Below 640px columns stack vertically and are centered (max-width 480px) for easy scrolling. Drag handles are hidden on mobile -- use the assign button instead.

> **Action feedback:** rename, delete, assign/unassign, share-link creation, and undo-split all now show a toast notification in the lower-right corner so you know the action actually succeeded. Errors surface as red toasts.

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

### Split Banner

Routes with more than 48 stops display a **Split into Routes** banner above the session card. Click it to open the **Split Planner** -- a dialog where you choose which bikers share the route, roughly how many stops each should get (fewer for a half-day shift), and optionally lock a biker to a single city district. The actual number of sub-routes depends on how many stops were successfully geocoded, so the banner label stays generic.

After splitting, the parent route disappears from the dashboard and each sub-route appears as an independent route card named `{parent_name}_1`, `{parent_name}_2`, etc. -- already assigned to the biker you picked, or in the **Unassigned** column for automatic splits. Sub-routes behave like any other route -- assign, optimize, rename, or delete them individually from the kanban.

## Assigning Routes

### Drag and drop

Drag a route card from one column to another. The route is reassigned to the target biker. You can also drag a route back to the **Unassigned** column to unassign it.

> Drag handles are hidden on mobile. Use the assign button instead.

### Assign button

Click the person icon on a route card to open a dropdown of all bikers. Select a biker to assign the route.

### Unassigning a route

Two ways to unassign a route from a biker:
- **Drag** the route card to the Unassigned column
- **Click the assign button** and select **Unassign** at the bottom of the dropdown (only appears when the route is currently assigned)

## Uploading Routes

Click **Upload Route** in the dashboard header. To upload directly for a specific biker, use the upload button within that biker's column.

## Renaming Routes

Click the pencil icon on a route card. The name becomes an editable text field. Press **Enter** to save or **Escape** to cancel. Long names scroll to the start automatically so you can see the beginning of the name while editing. A toast confirms the rename.

## Deleting Routes

Click the trash icon on a route card. A confirmation dialog appears. This permanently deletes the route and all its stops.

## Viewing a Route

Click the eye icon on a route card to open the full map view for that route. From there you can geocode, optimize, adjust settings, and share -- just like the biker view. A **Dashboard** button appears in the header to return to the management view.

---

## Bulk Clustering

For large uploads (50+ stops), LastMile splits deliveries into manageable sub-routes using geographic clustering.

### Triggering a Split

1. Upload a file with more than 48 stops
2. A **Split into Routes** banner appears above the route card in the Unassigned column
3. Click the banner -- the **Split Planner** dialog opens
4. Pick the bikers who work that day, adjust each biker's approximate stop count (e.g. fewer stops for a half-day shift), and optionally toggle **Single district** to restrict a biker to one city district (districts are derived from the Budapest postal codes in the stop addresses)
5. Click **Split** -- weighted KMeans clustering runs on the geocoded stops and each sub-route is created already assigned to its biker

Deselecting all bikers falls back to automatic splitting: `ceil(stop_count / 48)` sub-routes, all landing in the **Unassigned** column. Non-geocoded stops are skipped during clustering. If every selected biker is district-locked, stops outside those districts go into an extra unassigned sub-route so nothing is lost.

### Split Review

After splitting, the app opens the **Split Review** screen: every sub-route on one map, color-coded, with a sidebar listing stops per route. From here you can:

- **Move a stop** to a sibling route (click a stop, pick the target route in the popup)
- **Remove a stop** from the plan entirely (the × next to a stop, or "Remove stop" in the popup)
- **Optimize** routes individually or all at once
- **Assign / reassign** each sub-route to a biker
- **Undo the split**, deleting all sub-routes and restoring the original session

The review screen stays reachable after the fact: sub-route cards on the dashboard have a **split review** action that reopens it for more precise planning.

### Working with sub-routes

Sub-routes are first-class routes. From the kanban you can:

- **Assign** to a biker (drag-and-drop or the assign dropdown)
- **Optimize** individually by opening the route view
- **Rename** or **delete** via the card action icons
- **Track** progress once a biker starts one

---

## Live Map

When any routes are in progress, a **Live Map** button appears in the dashboard header showing the number of active routes (e.g., "Live Map (3)").

The live map shows:
- All active biker routes on one map
- Each biker has a distinct color (shown in the legend)
- Route lines drawn in the biker's color
- Small dots for completed/pending stops
- Large pulsing marker at each biker's current stop (with biker's initial)

### Auto-refresh

The map refreshes every 30 seconds by polling `GET /api/sessions/active/`. Click the refresh button for a manual update.

### Interacting with markers

Click a biker's current-stop marker to see a popup with:
- Biker name
- Route name
- Current destination ("Heading to: ...")
- Progress (e.g., "5/10 stops done")
- Route stats

Click **View Route** in the popup to jump directly to that biker's route on the map.

---

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
