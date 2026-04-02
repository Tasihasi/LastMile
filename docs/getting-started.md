# Getting Started

## Logging In

Open the app and enter your name. Choose your role:

- **Biker** -- you deliver packages and see only your assigned routes
- **Planner** -- you manage all routes, assign them to bikers, and track progress

No password is needed. If the username doesn't exist yet, an account is created automatically.

## Your First Route

### 1. Upload a file

Click **Upload Route** (planner) or **New Route** (biker) and select a file. Supported formats: CSV, XLSX, TXT (tab-delimited), XML.

Your file needs at minimum a `name` column and either an `address` column or `lat`/`lng` columns. See [File Format Reference](file-formats.md) for details.

The route is automatically named after the file (e.g., `monday_deliveries.csv` becomes "Monday Deliveries").

### 2. Geocode addresses

If any stops have addresses instead of coordinates, a **Geocode Addresses** button appears. Click it and watch pins appear on the map one by one as each address is resolved.

Stops that already have coordinates skip this step automatically.

### 3. Optimize the route

Click **Optimize Route** to calculate the best delivery order. The app uses the VROOM algorithm to find the shortest path and draws the route on the map following actual roads.

After optimization you'll see:
- Numbered stops in the optimized order
- A route line on the map
- Total duration, distance, and a time window estimate

The Optimize button disappears after the route is optimized -- there is no need to re-optimize.

### 4. Configure settings (optional)

Click the gear icon to adjust:

- **Home/Depot** -- set a start and end point for the route
- **Start time** -- when the route begins (default: 09:00)
- **Dwell time** -- minutes spent at each stop (default: 3 min)
- **Travel speed** -- walk (5 km/h), bike (15 km/h), or car (40 km/h)

Changes affect arrival time estimates. You can re-optimize after changing the depot.

### 5. Share (optional)

Click **Share** in the route summary bar to copy a public link. Anyone with the link can view the route read-only, without logging in.

## Switching Themes

Click the sun/moon icon in the header to toggle between light and dark mode. Your preference is saved in the browser.

## Logging Out

Click the user icon in the header and select **Logout**.
