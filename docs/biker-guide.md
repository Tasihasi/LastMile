# Biker Guide

## Route List

After logging in, you see your assigned routes. Routes are sorted with active (in-progress) routes at the top.

- **In-progress routes** show a pulsing green dot and progress (e.g., "3/7 stops done")
- **Not-started routes** show creation date and route stats
- **Finished routes** are collapsed under a toggle at the bottom

Click any route to open it on the map.

## Starting a Delivery Route

Once a route is optimized, a green **Start Route** button appears at the bottom of the sidebar.

Tapping it:
- Changes the route status to "In Progress"
- Highlights the first stop as your current destination
- Shows a progress banner: "Route in progress -- X/Y stops done"

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

When all stops have been marked (no pending stops remain), the route automatically finishes. You'll see a "Route completed" banner.

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
- Product code, recipient name, phone number
- Geocoding status

The phone number is tappable (opens dialer) and has a copy button.

## Uploading Your Own Route

Click **New Route** in the route list, then select a file. See [File Format Reference](file-formats.md) for supported formats.
