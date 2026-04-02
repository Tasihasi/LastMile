# LastMile - Planner User Guide

> Complete guide for route planners: uploading delivery lists, optimizing routes, assigning bikers, and tracking live progress.

## 1. Getting Started

### 1.1 Logging In

1. Open LastMile in your browser.
2. You will see the **Login Screen** with a username field and role selector.
3. Type your **username** into the text field.
4. Click the **"Planner"** role button. It will highlight to confirm your selection.
5. Click **"Sign In"**.
6. A brief loading spinner appears while your account is created or verified.
7. You are taken to the **Planner Dashboard**.

> **Note:** If you already have an account, logging in again with your username and the "Planner" role will restore your session. Your login persists across browser sessions until you explicitly log out.

### 1.2 Understanding the Dashboard

After logging in, you land on the **Planner Dashboard**. This is your command center.

**What you see:**

| Area | Location | Purpose |
|------|----------|---------|
| **Header bar** | Top of screen | Upload button, Live Map button, theme toggle, your username, logout |
| **Unassigned Routes** | Left column | Routes that haven't been assigned to any biker yet |
| **Biker Columns** | Right of unassigned | One column per registered biker, showing their assigned routes |
| **Finished Routes** | Bottom section (collapsible) | Completed deliveries with analytics |

Each route appears as a **card** showing:
- Route name
- Status badge ("In Progress" or "Done")
- Stop count and progress (e.g., "5/10 stops")
- Duration and distance (if the route has been optimized)
- Current heading (if in progress)
- Warning badge for any undelivered items

---

## 2. Uploading a Route

### 2.1 Preparing Your File

LastMile accepts four file formats:

| Format | Extension | Notes |
|--------|-----------|-------|
| CSV | `.csv` | Comma-separated, with header row |
| Excel | `.xlsx` | First sheet is read |
| Tab-delimited | `.txt` | Tab-separated, with header row |
| XML | `.xml` | Each record as an XML element |

**Required columns** (column names are case-insensitive):

| Column | Required? | Description |
|--------|-----------|-------------|
| `name` | Yes | Name of the delivery stop (e.g., restaurant, shop) |
| `address` | Yes* | Street address to geocode |
| `lat` | Yes* | Latitude (if you already have coordinates) |
| `lng` | Yes* | Longitude (if you already have coordinates) |
| `product_code` | No | SKU or product identifier |
| `recipient_name` | No | Name of the person receiving the delivery |
| `recipient_phone` | No | Contact phone number |

> *Each row needs **either** an `address` **or** both `lat` and `lng`. You can mix rows that have addresses with rows that have coordinates in the same file.

**Example CSV:**

```csv
name,address,product_code,recipient_name,recipient_phone
Pizza King,"Andrassy ut 12, Budapest",PKG-001,John Doe,+36201234567
Burger Place,"Vaci utca 5, Budapest",BRG-002,Jane Smith,+36209876543
Sushi Bar,,SHB-003,Bob Wilson,+36205551234
```

### 2.2 Uploading to the General Pool

This creates an **unassigned route** that you can assign to a biker later.

1. On the Dashboard, click the **"Upload Route"** button in the top-right header area.
2. A file picker dialog opens.
3. Select your file (`.csv`, `.xlsx`, `.txt`, or `.xml`).
4. A loading spinner appears with the text **"Processing file..."**.
5. Once processed, the new route card appears in the **Unassigned Routes** column.
6. The route is automatically named after the uploaded filename.

> **Alternative:** You can also drag a file directly onto the upload drop zone if one is visible.

### 2.3 Uploading Directly to a Biker

This creates a route and immediately assigns it to a specific biker.

1. Find the biker's column on the Dashboard.
2. Click the **"Upload for [Biker Name]"** button at the bottom of their column.
3. Select your file from the file picker.
4. The route appears directly in that biker's column, already assigned.

---

## 3. Planning a Route

After uploading, your route has raw addresses that need to be converted to map coordinates, and the stop order needs to be optimized. You can do this before or after assigning to a biker.

### 3.1 Geocoding Addresses

Geocoding converts street addresses into map coordinates (latitude/longitude).

1. Click the **eye icon** on a route card to open it in the **Map View**.
2. In the left sidebar, you'll see the **address list** with a stats bar showing:
   - **Total** stops
   - **Located** (already have coordinates)
   - **Failed** (if any)
3. If any stops need geocoding, the **"Geocode Addresses"** button appears.
4. Click **"Geocode Addresses"**.
5. A progress bar appears: **"Geocoding 1/12..."**, **"Geocoding 2/12..."**, etc.
6. Markers appear on the map in real-time as each address is resolved.
7. When complete, the stats bar updates. Check the counts:
   - **Green** markers = successfully geocoded
   - **Red** markers = failed (address not found)

> **What if geocoding fails for some stops?** Failed stops show a red "Failed" badge. They will be excluded from route optimization. You may need to correct the address in the source file and re-upload.

> **Stops that already have coordinates** (lat/lng provided in the file) skip geocoding and show a blue "Has coords" badge.

### 3.2 Configuring Route Settings

Before optimizing, you can adjust route parameters. Click the **gear icon** in the header to open the **Settings Panel**.

**Home / Depot Location:**
- Type a depot address into the text field and click the **search icon**.
- The address is geocoded and a gold house marker appears on the map.
- If set, the optimized route will start from and return to this depot.
- To remove it, click the **X** button next to the set address.

**Start Time:**
- Set the departure time using the time picker (default: **09:00**).
- This is used to calculate estimated arrival times at each stop.

**Time at Each Stop (Dwell Time):**
- Use the slider to set how many minutes the biker spends at each stop (0-15 minutes, default: **3 minutes**).
- This affects arrival time calculations for subsequent stops.

**Travel Speed:**
- Choose a preset: **Walk** (5 km/h), **Bike** (15 km/h), or **Car** (40 km/h).
- Or use the custom slider to set any speed between 3-60 km/h.
- This affects travel time estimates between stops.

> **All settings save automatically** and persist across sessions.

### 3.3 Optimizing the Route

Optimization calculates the most efficient stop order using the VROOM algorithm.

1. Ensure at least **2 stops** have coordinates (geocoded or pre-provided).
2. Click the **"Optimize Route"** button in the sidebar. It appears highlighted in accent color on first use.
3. A spinner shows **"Optimizing..."** while the algorithm runs.
4. When complete:
   - Stops reorder in the sidebar to show the **optimal sequence**.
   - The map draws an **indigo polyline** following actual roads.
   - A **route summary** appears showing total **duration**, **distance**, and **estimated time window** (e.g., "09:00 - 11:15").
   - Each stop in the list now shows an **estimated arrival time** and the **travel time/distance** to the next stop.
5. If a depot is set, the route starts and ends there, with a **"Return Home"** entry at the bottom of the list.

> **Re-optimizing:** After the first optimization, the button label changes to **"Re-optimize Route"**. Click it if you've changed settings (depot, speed, etc.) and want to recalculate.

---

## 4. Assigning Routes to Bikers

### 4.1 Drag-and-Drop Assignment

The fastest way to assign routes:

1. On the Dashboard, find the route card in the **Unassigned Routes** column.
2. Click and hold the route card.
3. Drag it to the target **biker's column**.
4. Release to drop. The card moves to that biker's column.

> You can also drag routes **between biker columns** to reassign them.

### 4.2 Using the Assign Button

1. On the route card, click the **person+ icon** (assign button).
2. A dropdown appears listing all registered bikers.
3. Click a biker's name.
4. The route card moves to that biker's column.

### 4.3 Uploading Directly for a Biker

See [Section 2.3](#23-uploading-directly-to-a-biker) above.

---

## 5. Managing Routes

### 5.1 Viewing a Route on the Map

1. On the Dashboard, find the route card you want to inspect.
2. Click the **eye icon** on the card.
3. The view switches from the Dashboard to the **Map View**, showing:
   - Left sidebar with the stop list, stats, and action buttons.
   - Map showing all stop markers and the route line (if optimized).
4. To return to the Dashboard, click the **"Dashboard"** button in the top-left header.

### 5.2 Renaming a Route

1. On the route card, click the **pencil icon** (or double-click the route name).
2. The name becomes an editable text field.
3. Type the new name.
4. Press **Enter** to confirm, or **Escape** to cancel.

### 5.3 Deleting a Route

1. On the route card, click the **trash icon**.
2. A confirmation dialog appears.
3. Confirm to permanently delete the route and all its stops.

> **Warning:** Deletion is permanent and cannot be undone.

### 5.4 Sharing a Route

Share a read-only view of any optimized route with anyone -- no login required.

1. Open the route in Map View (click the eye icon on the card).
2. In the route summary area (visible after optimization), click the **"Share"** button.
3. A shareable URL is **copied to your clipboard**. A brief confirmation message appears.
4. Send the link to anyone. They can open it in their browser to see:
   - The full stop list (read-only)
   - The route on the map
   - No editing or action capabilities

---

## 6. Tracking Live Deliveries

### 6.1 Opening the Live Map

1. On the Dashboard header, look for the **"Live Map"** button. It appears **only when at least one route is in progress**.
2. The button shows a count of active routes (e.g., "Live Map (3)").
3. Click it to open the **Live Map View**.

### 6.2 Reading the Live Map

The Live Map shows all in-progress routes simultaneously on a single map.

**What you see:**

- **Each biker has a distinct color** (drawn from an 8-color palette).
- **Route polylines** in each biker's color show the planned path.
- **Small colored dots** (12px) represent completed and pending stops.
- **Large pulsing circle** (36px) with the biker's initial marks their **current stop** (where they're heading next).
- A **legend** on the right side lists each biker with their color and progress (e.g., "Anna: 4/10 stops").

**Auto-refresh:** The map updates automatically every **30 seconds**. You can also click the **refresh button** in the header for an immediate update.

**Clicking a current-stop marker** opens a popup showing:
- Biker's name (bold)
- Route name
- "Heading to: [stop name]"
- Progress: "X/Y stops done"
- Route duration and distance
- A **"View Route"** button

### 6.3 Drilling into a Specific Route

1. On the Live Map, click the large pulsing marker for a biker.
2. In the popup, click **"View Route"**.
3. You switch to the full **Map View** for that specific route, showing every stop detail, arrival times, and delivery statuses.
4. Click **"Dashboard"** in the header to return, then **"Live Map"** to go back to the overview.

---

## 7. Reviewing Finished Routes

### 7.1 Finding Finished Routes

**On the Dashboard:**
1. Scroll to the bottom of the page.
2. Find the **"Finished Routes"** section. It's collapsible and shows a count (e.g., "Finished Routes (7)").
3. Click to expand it.
4. Click any finished route card to open the **Finished Route Detail** panel.

### 7.2 Reading the Delivery Report

The Finished Route Detail panel provides post-delivery analytics:

**Summary metrics at the top:**

| Metric | What it shows |
|--------|--------------|
| **Success rate** | Percentage of stops successfully delivered |
| **Delivered** | Count of stops marked as delivered |
| **Not received** | Count of stops where recipient was unavailable |
| **Skipped** | Count of stops that were skipped (if any) |

**Timeline:**

| Field | Description |
|-------|-------------|
| **Started** | When the biker tapped "Start Route" |
| **Finished** | When the last stop was marked |
| **Duration** | Total elapsed time |

**Stop-by-stop breakdown:**
- Each stop shows its **sequence number**, **delivery status icon** (checkmark / X / dash), **stop name**, **recipient name**, **address**, and a **status badge** (Delivered / Not Received / Skipped).

**"View on Map" button:** Opens the route in Map View to see the geographic context of completed deliveries.

---

## 8. Interface Reference

### 8.1 Dashboard Layout

```
+------------------------------------------------------------------+
| [Logo] Route Planner      [Live Map (2)] [Upload Route] [Theme] [User v] |
+------------------------------------------------------------------+
|                                                                  |
|  Unassigned        Anna (2 routes)       Ben (1 route)           |
|  +-----------+     +-----------+         +-----------+           |
|  | Route A   |     | Route C   |         | Route E   |           |
|  | 10 stops  |     | In Progress|        | 8 stops   |           |
|  | [eye][del]|     | 5/12 stops |        | [eye][del]|           |
|  +-----------+     +-----------+         +-----------+           |
|  | Route B   |     | Route D   |                                 |
|  | 5 stops   |     | 7 stops   |                                 |
|  +-----------+     +-----------+                                 |
|                    [Upload for Anna]     [Upload for Ben]         |
|                                                                  |
|  > Finished Routes (3)                                           |
+------------------------------------------------------------------+
```

### 8.2 Map View Layout

```
+------------------------------------------------------------------+
| [Dashboard] [Sidebar Toggle]                [Settings] [Theme] [User v] |
+------------------------------------------------------------------+
|  Sidebar (Left)          |  Map (Right)                          |
|                          |                                       |
|  Stats: 12 total, 10 ok |    [2]----[3]                         |
|  [Re-optimize Route]     |   /         \                         |
|                          |  [1]        [4]----[5]                |
|  Duration: 2h 15m        |  [Depot]       \                     |
|  Distance: 45 km         |                [6]                    |
|  09:00 - 11:15 [Share]   |                                       |
|                          |                                       |
|  1. Pizza King  09:12    |                                       |
|     > 8 min, 2.1 km      |                                       |
|  2. Burger Place 09:23   |                                       |
|     > 5 min, 1.4 km      |          [Stop Detail Panel]         |
|  3. Sushi Bar   09:31    |          | Sushi Bar           [X]|  |
|  ...                     |          | Arrival: 09:31       |  |
|                          |          | 1.4 km from Burger   |  |
|  Return Home   11:15     |          | Recipient: Bob       |  |
|                          |          | Phone: +3620...  [Copy]| |
+------------------------------------------------------------------+
```

### 8.3 Marker Colors & Icons

| State | Color | Size | Description |
|-------|-------|------|-------------|
| Pending geocode | Gray | Normal | Stop has an address but hasn't been geocoded yet |
| Failed geocode | Red | Normal | Address could not be found |
| Geocoded | Green | Normal | Address successfully converted to coordinates |
| Optimized | Indigo/Blue | Normal | Stop is part of an optimized route |
| Current stop | Indigo | Large + pulsing | The biker's next delivery target |
| Delivered | Green | Small, semi-transparent | Stop successfully delivered (checkmark overlay) |
| Not received | Red | Small, semi-transparent | Recipient unavailable (X overlay) |
| Skipped | Gray | Small, semi-transparent | Stop was skipped (dash overlay) |
| Depot / Home | Amber/Gold | Normal | Start/end point with house icon |

### 8.4 Theme & Display

- Click the **sun/moon icon** in the header to toggle between **Light** and **Dark** mode.
- The default follows your operating system's theme preference.
- Your choice is saved and persists across sessions.

---

## Quick Reference: Keyboard & Mouse Shortcuts

| Action | How |
|--------|-----|
| Select a stop | Click it in the sidebar list **or** click its marker on the map |
| Close detail panel | Click the **X** button or click outside the panel |
| Rename a route | Double-click the route name on its card, or click the pencil icon |
| Confirm rename | Press **Enter** |
| Cancel rename | Press **Escape** |
| Toggle sidebar (mobile) | Click the hamburger menu icon in the header |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Geocode Addresses" button not visible | All stops already have coordinates. Check the stats bar. |
| "Optimize Route" button not visible | You need at least 2 geocoded stops. Run geocoding first. |
| Some stops show red "Failed" badges | The address couldn't be found. Check spelling and try re-uploading with corrected addresses. |
| Live Map button not visible | No routes are currently in progress. A biker must tap "Start Route" first. |
| Route line not showing on map | The route hasn't been optimized yet. Click "Optimize Route". |
| Shared link doesn't work | Make sure the full URL was copied. The link is public and works without login. |
