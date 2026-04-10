# Biker Guide

## Route List

After logging in, you see your assigned routes. Routes are sorted with active (in-progress) routes at the top.

- **In-progress routes** show a pulsing green dot and progress (e.g., "3/7 stops done")
- **Not-started routes** show creation date and route stats
- **Finished routes** are collapsed under a toggle at the bottom
- **Split routes** (parent sessions that have been clustered) are hidden from the biker view -- you only see the individual sub-routes assigned to you

Click any route to open it on the map.

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

## Theme

Click the sun/moon icon in the header to toggle between light and dark mode. Your preference is saved in the browser. The map tiles automatically adjust brightness in dark mode.

## Sharing

Click **Share** in the route summary bar to generate a public link. Anyone with the link can view the route read-only without logging in.
