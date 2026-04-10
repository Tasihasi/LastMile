# Planner Guide

## Dashboard

After logging in as a planner, you see the management dashboard instead of the map.

### Layout

- **Unassigned column**: Routes not assigned to any biker
- **Split Routes section**: Parent sessions that have been clustered into sub-routes (click to review)
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

Routes with more than 48 stops display a **Split into Routes** banner above the session card. Click it to trigger KMeans clustering -- a spinner shows while clustering is in progress. The actual number of sub-routes depends on how many stops were successfully geocoded, so the banner label stays generic.

After splitting, the parent route moves to the **Split Routes** section and its status changes to `split`. The child sub-routes appear in the cluster review view.

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
3. Click the banner -- KMeans clustering runs on the geocoded stops
4. The parent session moves to the **Split Routes** section with status `split`

The number of sub-routes is auto-calculated: `ceil(stop_count / 48)`. Each sub-route respects the ORS 48-stop optimization limit. Non-geocoded stops are skipped during clustering and reported in the review view.

### Cluster Review View

Click a split parent session in the **Split Routes** section to open the cluster review. This view shows:

**Header:**
- Session name and cluster summary stats (total stops, number of routes, skipped stops)
- **Undo Split** button -- reverts clustering, restores all stops to the parent session
- **Back to Dashboard** button

**Color-coded Map:**
- Each sub-route's stops are shown in a distinct color (10 colors: red, blue, green, purple, orange, teal, pink, brown, indigo, cyan)
- Click a marker to see stop details and which sub-route it belongs to
- Route geometry is drawn when a sub-route is optimized

**Sub-route Cards (sidebar):**
- One collapsible card per sub-route, color-coded to match the map
- Shows stop count, optimization status, and assignment
- Click the card header to expand and see the stop list
- **Optimize** button: run VROOM optimization on this sub-route
- **Assign** dropdown: assign this sub-route to a biker
- **Move stop** controls: move individual stops to a different sub-route
- Empty sub-routes show a warning and a **Delete** button

**Optimize All:**
- An **Optimize All** button appears at the top to optimize every sub-route in one click

### Moving Stops Between Sub-routes

In the cluster review, each stop in an expanded sub-route card has a move control. Select a target sub-route from the dropdown and click the move button. The stop is transferred immediately and both stop counts update.

This is useful for fine-tuning cluster boundaries -- for example, moving a stop that's geographically closer to a different sub-route.

### Undo Split

Click **Undo Split** in the cluster review header to revert the clustering. A confirmation dialog appears first (`"This will delete all sub-routes and restore stops to the parent. Continue?"`) because the action is destructive.

After confirming:
- All child sub-routes are deleted
- Stops are restored to the parent session
- Parent status resets to `not_started`
- A toast confirms the undo

> **Blocked if active:** Undo is blocked if any sub-route has status `in_progress` (a biker is actively delivering). You must wait for all active sub-routes to finish before undoing. The server returns a 409 and the UI surfaces an error toast.

### Compact Optimize All button

On narrow viewports (below 480px) the **Optimize All** button shrinks to a compact "Optimize (N)" label where N is the number of sub-routes that still need optimization. This keeps the remaining-count visible even when the cluster review sidebar is cramped.

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
