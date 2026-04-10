# Getting Started

## Logging In

Open the app and enter your name. Choose your role:

- **Biker** -- you deliver packages and see only your assigned routes
- **Planner** -- you manage all routes, assign them to bikers, and track progress

No password is needed. If the username doesn't exist yet, an account is created automatically. Your session is stored in the browser via a token -- you stay logged in until you explicitly log out.

## Your First Route (Biker)

### 1. Upload a file

Click **New Route** and select a file. Supported formats: CSV, XLSX, TXT (tab-delimited), XML.

Your file needs at minimum a `name` column and either an `address` column or `lat`/`lng` columns. See [File Format Reference](file-formats.md) for details.

The route is automatically named after the file (e.g., `monday_deliveries.csv` becomes "Monday Deliveries").

On mobile, a **Back** button appears to return to the map/session view without uploading.

### 2. Geocode addresses

If any stops have addresses instead of coordinates, a **Geocode Addresses** button appears. Click it and watch pins appear on the map one by one as each address is resolved via NDJSON streaming.

Stops that already have coordinates skip this step automatically.

> The geocode button only appears for routes that haven't been started yet. Once a route is in progress, geocoding is locked.

### 3. Optimize the route

Click **Optimize Route** to calculate the best delivery order. The app uses the VROOM algorithm to find the shortest path and draws the route on the map following actual roads.

After optimization you'll see:
- Numbered stops in the optimized order
- A route line on the map following real roads
- Total duration, distance, and a time window estimate

> The optimize button is only available for routes in `not_started` status. For in-progress routes, a subtle **Re-optimize Route** button appears instead -- clicking it shows a confirmation prompt before re-running optimization.

### 4. Configure settings (optional)

Click the gear icon to adjust:

- **Home/Depot** -- set a start and end point for the route
- **Start time** -- when the route begins (default: 09:00)
- **Dwell time** -- minutes spent at each stop (default: 3 min)
- **Travel speed** -- walk (5 km/h), bike (15 km/h), or car (40 km/h)

Changes affect arrival time estimates. You can re-optimize after changing the depot. Settings are persisted in the browser across sessions.

### 5. Share (optional)

Click **Share** in the route summary bar to copy a public link. Anyone with the link can view the route read-only, without logging in. The shared view shows the full map, stop list, and route geometry.

## Your First Route (Planner)

Planners start on the **Dashboard** instead of the map view.

### 1. Upload a route

Click **Upload Route** in the dashboard header. The route appears in the **Unassigned** column.

### 2. Geocode and optimize

Click the eye icon on a route card to open it on the map. From there, geocode and optimize as described above. Click **Dashboard** in the header to return.

### 3. Assign to a biker

Drag the route card to a biker's column, or click the person icon and select a biker from the dropdown.

### 4. Large uploads (50+ stops)

Routes with more than 48 stops show a **Split into Routes** banner above the card. Click it to cluster stops into geographic sub-routes using KMeans. Review the clusters on a color-coded map, then optimize and assign each sub-route individually. See [Planner Guide](planner-guide.md) for details.

## Switching Themes

Click the sun/moon icon in the header to toggle between light and dark mode. Your preference is saved in the browser. The app also respects your OS theme preference on first visit.

## Mobile Navigation

On mobile devices:
- The **sidebar** collapses by default -- tap the toggle button to show/hide it
- The **dashboard** columns stack vertically and are centered for easy scrolling
- All buttons are touch-friendly (minimum 32px targets)
- Drag handles are hidden on mobile (use the assign button instead)

## Logging Out

Click the user icon in the header and select **Logout**. This deletes your auth token on the server.
