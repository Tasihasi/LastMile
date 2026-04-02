# LastMile - Biker User Guide

> Complete guide for delivery bikers: viewing assigned routes, navigating stops, and marking deliveries.

## 1. Getting Started

### 1.1 Logging In

1. Open LastMile in your browser (on your phone or computer).
2. You see the **Login Screen**.
3. Type your **username** into the text field.
4. Tap the **"Biker"** role button. It highlights to confirm your selection.
5. Tap **"Sign In"**.
6. A brief loading spinner appears.
7. You are taken to your **Route List**.

> **Tip:** Your login persists even if you close the browser. You'll stay logged in until you tap "Logout".

### 1.2 Understanding Your Home Screen

After logging in, you see your **Route List** -- this shows every route assigned to you.

**What you see:**

| Area | Description |
|------|-------------|
| **Header** | App name, theme toggle, your username, logout button |
| **"New Route" button** | Upload your own delivery file |
| **Active Routes** | Routes you haven't finished yet (not started + in progress) |
| **Finished Routes** | Completed routes (collapsible section) |

---

## 2. Your Route List

### 2.1 Viewing Assigned Routes

Your planner assigns routes to you. When they do, the route appears in your **Active Routes** list.

Each route card shows:

| Info | Example | Meaning |
|------|---------|---------|
| **Status dot** | Spinning dot | Route is in progress |
| **Status dot** | Solid dot | Route hasn't been started yet |
| **Route name** | "Monday AM Downtown" | Name given by the planner |
| **Progress** | "3/10 stops done" | How many stops you've completed |
| **Created** | "Apr 2, 2026 09:15" | When the route was created |
| **Duration** | "2h 15m" | Estimated total route time |
| **Distance** | "45 km" | Estimated total distance |
| **Stop count** | "10 stops" | Total number of deliveries |

### 2.2 Active vs. Finished Routes

**Active Routes** (top section):
- Routes with status **"Not Started"** or **"In Progress"**.
- In-progress routes appear at the **top** with a spinning status indicator.
- Tap any route to open it.

**Finished Routes** (bottom section):
- Collapsed by default. Tap to expand.
- Shows routes you've fully completed.
- Tap any finished route to review it.

### 2.3 Creating Your Own Route

If your planner hasn't assigned you a route, or you need to create one yourself:

1. Tap the **"New Route"** button at the top of the Route List.
2. This opens the file upload screen (see [Section 7](#7-uploading-your-own-route)).

---

## 3. Preparing a Route

### 3.1 Opening a Route

1. On your Route List, tap the route you want to open.
2. The app loads the route and switches to the **Map View**.
3. You see:
   - **Left sidebar** with the stop list (on desktop; swipe or use the hamburger menu on mobile).
   - **Map** showing all delivery stops as numbered markers.

### 3.2 Geocoding Addresses

If stops have street addresses but no map coordinates, they need to be geocoded first.

**How to tell:** The sidebar shows a stats bar. If "Located" is less than "Total", some stops need geocoding.

1. Look for the **"Geocode Addresses"** button in the sidebar.
2. Tap it.
3. A progress bar appears: **"Geocoding 1/12..."**, **"Geocoding 2/12..."** and so on.
4. Watch as markers appear on the map one by one in real-time.
5. When done, check the stats:
   - Green markers = successfully located.
   - Red markers = address not found (these will be excluded from the route).

> **If all stops already have coordinates** (provided in the file), this step is skipped automatically. You'll see a blue "Has coords" badge on each stop.

### 3.3 Adjusting Route Settings

Tap the **gear icon** in the header to open the Settings Panel.

| Setting | What it does | Default |
|---------|-------------|---------|
| **Home location** | Start/end point for your route (depot) | Not set |
| **Start time** | When you plan to depart | 09:00 |
| **Time at each stop** | Minutes you spend per delivery | 3 min |
| **Travel speed** | Your expected travel speed | 15 km/h (Bike) |

See [Section 8](#8-settings) for detailed instructions on each setting.

> **Tip:** Set these **before** optimizing so arrival times are accurate.

### 3.4 Optimizing the Route

Optimization calculates the best stop order so you ride the shortest total distance.

1. Make sure at least **2 stops** have coordinates.
2. Tap the **"Optimize Route"** button in the sidebar.
3. A spinner shows **"Optimizing..."**.
4. When done:
   - The stop list **reorders** to show the optimal sequence.
   - An **indigo route line** appears on the map following actual roads.
   - A **route summary** appears at the top of the sidebar:
     - Total duration (e.g., "2h 15m")
     - Total distance (e.g., "45 km")
     - Time window (e.g., "09:00 - 11:15")
   - Each stop now shows its **estimated arrival time**.
   - Between stops, you'll see the **travel time** and **distance** for each segment.

> **If a depot is set:** The route starts and ends at your depot. A "Return Home" entry appears at the bottom of the stop list.

---

## 4. Reading the Map

### 4.1 Understanding Markers

Each delivery stop appears as a **numbered circle** on the map. The number matches the stop's position in the sequence.

| Marker appearance | What it means |
|-------------------|--------------|
| **Gray circle** | Stop is pending geocoding (address not yet resolved) |
| **Red circle** | Geocoding failed (address couldn't be found) |
| **Green circle** | Stop has been geocoded successfully |
| **Indigo/blue circle** | Stop is part of an optimized route |
| **Large indigo circle with pulsing glow** | Your **current stop** -- where you're heading next |
| **Small green circle (semi-transparent)** | Stop you've delivered successfully |
| **Small red circle (semi-transparent)** | Stop marked as "Not Received" |
| **Small gray circle (semi-transparent)** | Stop you skipped |
| **Gold circle with house icon** | Your depot / home location |

### 4.2 The Route Line

After optimization, an **indigo line** connects all stops in order. This line follows **actual roads**, not straight lines, so it shows your real riding path.

- The route goes from your depot (if set) through each stop in optimal order and back to depot.
- The line weight is 4px with slight transparency so you can still see the map underneath.

### 4.3 Viewing Stop Details

**Tap a stop** in the sidebar list **or** tap its marker on the map to open the **Stop Detail Panel** on the right side.

The detail panel shows:
- **Stop name** (header)
- **Expected arrival time** (if route is optimized)
- **Travel info** from previous stop (time and distance)
- **Address**
- **Coordinates** (latitude, longitude)
- **Product code** (if provided, shown in a code badge)
- **Recipient name** (if provided)
- **Recipient phone** (if provided -- tappable to call)

To close the panel, tap the **X** in the top-right corner.

---

## 5. Running Your Delivery Route

### 5.1 Starting the Route

Once your route is optimized and you're ready to ride:

1. In the sidebar, find the **"Start Route"** button. It appears below the route summary.
2. Tap **"Start Route"**.
3. The route status changes to **"In Progress"**.
4. The first stop in the sequence becomes your **current stop**, marked with a **large pulsing indigo marker** on the map.
5. A status banner appears at the top of the sidebar: **"Route in progress -- 0/10 stops done"**.

> **Important:** Once started, the "Start Route" button disappears. You're now in delivery mode.

### 5.2 Marking Stops as Delivered

When you arrive at a stop and successfully complete the delivery:

1. Your **current stop** is highlighted in the sidebar list with action buttons visible.
2. Tap the **green checkmark button** ("Delivered").
3. The stop is marked as delivered:
   - Its marker on the map becomes **small and green** with a checkmark overlay.
   - A green **"Delivered"** badge appears next to it in the list.
4. The app **automatically advances** to the next pending stop in the sequence.
5. The progress counter updates (e.g., "1/10 stops done").

### 5.3 Marking Stops as Not Received

If the recipient is unavailable or refuses the delivery:

1. On your current stop in the sidebar, tap the **red X button** ("Not Received").
2. The stop is marked as not received:
   - Its marker on the map becomes **small and red** with an X overlay.
   - A red **"Not Received"** badge appears in the list.
3. The app advances to the next pending stop.

### 5.4 Skipping a Stop

If you need to skip a stop entirely (e.g., can't access the building):

1. On your current stop in the sidebar, tap the **gray dash button** ("Skip").
2. The stop is marked as skipped:
   - Its marker becomes **small and gray** with a dash overlay.
   - A gray **"Skipped"** badge appears in the list.
3. The app advances to the next pending stop.

### 5.5 Completing the Route

The route **automatically completes** when you've marked every stop (delivered, not received, or skipped).

- The status banner changes to: **"Route completed"** with a checkmark.
- The route moves to your **Finished Routes** list.
- You return to the Route List to see your remaining routes or start a new one.

To return to your Route List at any time, tap the **"Start Over"** button in the header.

---

## 6. Stop Details & Contact Info

### 6.1 Viewing Full Stop Information

When you're at a delivery and need more details:

1. Tap the **stop** in the sidebar list, or tap its **marker** on the map.
2. The **Stop Detail Panel** slides in from the right.
3. Here you'll find everything about this delivery:

| Field | Description |
|-------|-------------|
| **Stop name** | Business or location name |
| **Arrival time** | When you're expected to arrive |
| **Travel from previous** | How long and how far from the last stop |
| **Address** | Full street address |
| **Coordinates** | Exact lat/lng (5 decimal places) |
| **Product code** | The item code (shown in a gray code badge) |
| **Recipient name** | Who to hand the delivery to |
| **Recipient phone** | Their phone number |

### 6.2 Calling the Recipient

If the stop has a phone number:

1. Open the Stop Detail Panel (tap the stop).
2. Find the **phone number** at the bottom.
3. Tap the phone number directly -- it's a clickable link.
4. Your phone's dialer opens with the number pre-filled.

### 6.3 Copying the Phone Number

If you need to paste the number elsewhere (e.g., into a messaging app):

1. Open the Stop Detail Panel.
2. Next to the phone number, tap the **copy button** (clipboard icon).
3. A brief **"Copied!"** confirmation appears for 1.5 seconds.
4. The number is on your clipboard -- paste it anywhere.

---

## 7. Uploading Your Own Route

### 7.1 Supported File Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| CSV | `.csv` | Comma-separated values with a header row |
| Excel | `.xlsx` | Reads the first sheet |
| Tab-delimited | `.txt` | Tab-separated values with a header row |
| XML | `.xml` | Each delivery as an XML element |

### 7.2 File Requirements

Your file must have a **header row** with these columns (names are case-insensitive):

| Column | Required? | Description |
|--------|-----------|-------------|
| `name` | **Yes** | Name of the stop (restaurant, shop, address label) |
| `address` | **Yes*** | Street address to look up on the map |
| `lat` | **Yes*** | Latitude, if you already have coordinates |
| `lng` | **Yes*** | Longitude, if you already have coordinates |
| `product_code` | No | Product or package identifier |
| `recipient_name` | No | Person receiving the delivery |
| `recipient_phone` | No | Their phone number |

> *Each row needs **either** an `address` **or** both `lat` and `lng`. You can mix both in the same file.

**Example CSV file:**

```csv
name,address,recipient_name,recipient_phone
Pizza King,"Andrassy ut 12, Budapest",John Doe,+36201234567
Burger Place,"Vaci utca 5, Budapest",Jane Smith,+36209876543
```

### 7.3 Upload Step by Step

1. From your Route List, tap **"New Route"**.
2. You see the upload screen with a large drop zone:
   - **"Drop your file here or click to browse"**
   - Supported format tags: `.csv`, `.xlsx`, `.txt`, `.xml`
3. **On desktop:** Drag your file onto the zone, or click to open the file picker.
4. **On mobile:** Tap the zone to open the file picker and select your file.
5. A loading spinner appears: **"Processing file..."**
6. Once processed, you're taken to the Map View with your stops loaded.
7. Continue with [geocoding](#32-geocoding-addresses) and [optimizing](#34-optimizing-the-route).

---

## 8. Settings

Open settings by tapping the **gear icon** in the header (visible when you have a route loaded).

### 8.1 Setting a Home/Depot Location

Your depot is where your route starts and ends (e.g., your warehouse or office).

**To set a depot:**
1. Open Settings (gear icon).
2. In the **"Home / Depot Location"** section, type an address (e.g., "Rakoczi ut 1, Budapest").
3. Tap the **search icon** (magnifying glass).
4. The address is looked up. If found, a **"Set" badge** appears and a **gold house marker** shows on the map.

**To remove a depot:**
1. Open Settings.
2. Next to the set address, tap the **X button**.
3. The depot is cleared. Routes will no longer start/end at a fixed location.

### 8.2 Setting Your Start Time

1. Open Settings.
2. Find the **"Start Time"** field.
3. Tap it and select your departure time (e.g., 08:30).
4. Arrival times for all stops recalculate automatically.

> **Default:** 09:00

### 8.3 Adjusting Time at Each Stop

This is how many minutes you typically spend at each delivery (parking, finding the entrance, handing over).

1. Open Settings.
2. Find the **"Time at Each Stop"** slider.
3. Drag it to your preferred duration (0 to 15 minutes).
4. The current value is shown in a badge next to the slider.

> **Default:** 3 minutes

### 8.4 Setting Your Travel Speed

1. Open Settings.
2. Find the **"Travel Speed"** section.
3. **Quick pick:** Tap one of the preset buttons:
   - **Walk** (5 km/h) -- walking figure icon
   - **Bike** (15 km/h) -- bicycle icon (default)
   - **Car** (40 km/h) -- car icon
4. **Custom speed:** Use the slider to set any speed from 3 to 60 km/h.
5. Travel time estimates between stops update accordingly.

> **All settings save automatically** and persist even if you close the app.

---

## 9. Interface Reference

### 9.1 Screen Layout

**Route List (Home Screen):**

```
+------------------------------------------+
| [Logo] LastMile     [Theme] [Username v] |
+------------------------------------------+
|                                          |
|  Recent Routes              [New Route]  |
|                                          |
|  * Monday AM Downtown                    |
|    In Progress - 5/12 stops done         |
|    2h 15m / 45 km                        |
|                                          |
|  * Tuesday Deliveries                    |
|    Not started - 0/8 stops               |
|    1h 30m / 22 km                        |
|                                          |
|  > Finished Routes (3)                   |
+------------------------------------------+
```

**Map View (Active Route):**

```
+------------------------------------------+
| [Start Over] [=]      [Settings] [Theme] |
+------------------------------------------+
| Sidebar        |  Map                    |
|                |                         |
| Route in       |     [2]---[3]           |
| progress       |    /        \           |
| 5/12 done      |  [>>1]     [4]--[5]    |
|                |  (depot)      \         |
| 1. Pizza King  |              [6]        |
|   DELIVERED    |                         |
|                |                         |
| 2. Burger Pl   |     Stop Detail:        |
|   DELIVERED    |     Burger Place    [X]  |
|                |     Arrive: 09:23       |
| >> 3. Sushi    |     5 min from Pizza K  |
|  [Delivered]   |     Recipient: Jane     |
|  [Not Recv]    |     Phone: +3620... [C] |
|  [Skip]        |                         |
|                |                         |
| 4. Taco Hut    |                         |
|   pending      |                         |
+------------------------------------------+
```

### 9.2 Marker Colors Guide

| What you see | What it means |
|-------------|--------------|
| **Gray numbered circle** | Waiting to be geocoded |
| **Red numbered circle** | Address lookup failed |
| **Green numbered circle** | Successfully geocoded |
| **Indigo numbered circle** | Part of optimized route |
| **Large indigo circle (pulsing)** | Your current stop -- go here next! |
| **Small faded green circle** | You delivered this one |
| **Small faded red circle** | Marked "Not Received" |
| **Small faded gray circle** | You skipped this one |
| **Gold circle with house** | Your depot / home base |

### 9.3 Status Badges Guide

**Geocoding status:**

| Badge | Color | Meaning |
|-------|-------|---------|
| Pending | Gray | Hasn't been geocoded yet |
| Geocoded | Green | Address found on map |
| Failed | Red | Address couldn't be found |
| Has coords | Blue | Coordinates were in the file (no geocoding needed) |

**Delivery status:**

| Badge | Color | Meaning |
|-------|-------|---------|
| Pending | Gray | You haven't visited this stop yet |
| Delivered | Green | Successfully delivered |
| Not Received | Red | Recipient wasn't available |
| Skipped | Gray | You chose to skip this stop |

### 9.4 Theme Toggle

- Tap the **sun icon** (in light mode) or **moon icon** (in dark mode) in the header.
- Switches between Light and Dark themes.
- Default follows your device's system setting.
- Your preference is saved automatically.

---

## 10. Troubleshooting

| Problem | What to do |
|---------|-----------|
| **I don't see any routes** | Your planner hasn't assigned you any yet. Ask them, or tap "New Route" to upload your own. |
| **"Geocode Addresses" button missing** | All stops already have coordinates -- you're good to go. Check the stats bar. |
| **"Optimize Route" button missing** | You need at least 2 stops with coordinates. Run geocoding first if needed. |
| **Some stops are red after geocoding** | Those addresses couldn't be found. Ask your planner to check the spelling and re-upload. |
| **"Start Route" button missing** | Either the route isn't optimized yet (optimize first), or it's already started. |
| **I can't mark a stop** | Only your **current stop** (the one with the pulsing marker) shows action buttons. Complete stops in order. |
| **The route line doesn't show** | The route needs to be optimized first. Tap "Optimize Route". |
| **The app logged me out** | Your session may have expired. Log in again with your username and "Biker" role. |
| **My settings disappeared** | Settings are stored in your browser. If you cleared browser data or switched devices, re-enter them. |
| **Phone number won't dial** | Make sure you're on a device with phone capabilities (mobile). On desktop, copy the number instead. |
