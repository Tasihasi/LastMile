# Biker Guide

## Route List

After logging in, you see your assigned routes. Routes are sorted with active (in-progress) routes at the top.

- **In-progress routes** show a pulsing green dot and progress (e.g., "3/7 stops done")
- **Not-started routes** show creation date and route stats
- **Finished routes** are collapsed under a toggle at the bottom

Routes produced by splitting a large upload appear exactly like any other route -- they carry the parent name with a numeric suffix (e.g. `big_monday_delivery_2`) and behave identically once assigned.

Click any route to open it on the map.

> **Auto-select on login:** If you have exactly one in-progress route when you sign in, the app drops you straight into that route's map view so you can resume delivering without clicking through the list.

## Uploading Your Own Route

Click **New Route** in the route list, then select a file. See [File Format Reference](file-formats.md) for supported formats.

On mobile, a **Back** button appears to return to the route list without uploading.

## Starting a Delivery Route

Once a route is optimized, a green **Start Route** button appears at the bottom of the sidebar.

Tapping it:
- Changes the route status to "In Progress"
- Highlights the first stop as your current destination
- Shows a progress banner: "Route in progress -- X/Y stops done"

> **Note:** Once a route is started or finished, the **Start Route** button disappears. A started route cannot be restarted. The **Start Over** button in the header is also hidden during active and finished routes to prevent accidentally navigating away.

## Delivering Stops

Your current stop is highlighted on both the map and the sidebar:
- On the **map**: a large pulsing marker
- In the **sidebar**: highlighted row with action buttons

### Marking a stop

Three buttons appear below the current stop:

| Button | Color | Meaning |
|--------|-------|---------|
| Delivered | Green | Package delivered successfully |
| Not Received | Red | Recipient unavailable or refused |
| Skip | Gray | Skip this stop for now |

After marking a stop:
- The next pending stop becomes your current destination
- The map marker changes (small green checkmark for delivered, red X for not received, gray dash for skipped)
- Progress counter updates

### Auto-finish

When all stops have been marked (no pending stops remain), the route automatically finishes. You'll see a "Route completed" banner with delivery stats.

## Re-optimizing an Active Route

If you need to change the route order while delivering (e.g., road closure, priority change), a subtle **Re-optimize Route** button is available for in-progress routes.

Clicking it shows a confirmation prompt: "Re-optimize will change the route order. Continue?" Click **Re-optimize** to confirm or **Cancel** to dismiss. This re-runs the VROOM optimization on remaining stops without affecting already-delivered stops.

> The full Geocode and Optimize buttons are only available before a route is started. Once in progress, only re-optimize is available.

## Map Markers

| Marker | Meaning |
|--------|---------|
| Large pulsing circle | Your current stop |
| Numbered indigo circle | Upcoming stop (pending) |
| Small green (checkmark) | Delivered |
| Small red (X) | Not received |
| Small gray (dash) | Skipped |
| Gold house icon | Depot / home location |

## Stop Details

Click any stop in the sidebar or tap a marker on the map to see details:

- Arrival time estimate
- Travel time from previous stop
- Address and coordinates
- Product code, recipient name, phone number (if included in the upload file)
- Geocoding status (success, failed, skipped)

The phone number is tappable (opens dialer) and has a copy button.

> Press **Esc** or tap outside the popup to close it. The same shortcut closes the finished-route stats panel.

### Stop order

Once a route is optimized, the sidebar list is re-sorted to match the numbered markers on the map -- so the first stop in the list is always the first stop you'll visit.

### Phone number in sidebar

If stops have phone numbers, they also appear directly in the sidebar stop list (no need to open the detail popup). Each phone number shows:
- A phone icon
- A clickable link (opens dialer)
- A copy-to-clipboard button

## Settings

Click the gear icon in the header to configure:

- **Home/Depot** -- starting and ending point for route optimization
- **Start time** -- when you begin the route (affects arrival estimates)
- **Dwell time** -- minutes spent at each stop (default: 3 min)
- **Travel speed** -- walk (5 km/h), bike (15 km/h), or car (40 km/h)

Settings are saved in your browser and persist across sessions.

> On mobile, tapping the gear while the sidebar is collapsed auto-opens the sidebar so the settings panel is visible.

## Header Menu (Kebab)

The header has a **kebab** (`⋮`) button that opens a dropdown with:

- **Help & Documentation** -- opens the in-app docs
- **Theme toggle** -- switch between light and dark mode (the map tiles adjust brightness automatically)
- **Sign Out** -- shows your username and signs you out of the app

On very narrow viewports (below 380px) the entire header collapses to this kebab so Sign Out never gets clipped off-screen. Your theme preference is saved in the browser and respects your OS preference on first visit.

## Sharing

Click **Share** in the route summary bar to generate a public link. Anyone with the link can view the route read-only without logging in.
