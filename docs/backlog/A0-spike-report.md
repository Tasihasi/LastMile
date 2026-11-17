# A0 spike report — is zone-first, zip-atomic allocation feasible?

**Verdict: GO.** Zip-atomic allocation is a small, well-understood packing problem, and it is
much simpler than the current KMeans approach. It can be built in A2 with no new dependencies.

## Why it is feasible
Stops are grouped by `postal_code` (already stored, A0 fixtures cover 34 zips). Treat each zip as
an indivisible item whose weight is its stop count (later: estimated minutes, A5/B2). Each biker is
a bin with a capacity. This is bin packing / multiway partitioning, with at most ~34 items and
3–5 bins, so even brute-force-ish heuristics finish in milliseconds.

## Algorithms considered
| Option | Idea | Verdict |
|---|---|---|
| Greedy LPT | Sort zips by size desc; put each into the biker with the most remaining capacity | **Recommended for A2.** Simple, deterministic, within ~4/3 of optimal balance. |
| Geo-aware greedy | LPT, but break ties / prefer the bike whose assigned zips are nearest (centroid distance) | **Recommended for A5.** Keeps routes compact; the zone sheet (A1) groups neighbouring zips. |
| Exact bin packing (ILP / DP) | Optimal balance | Overkill for ≤34 items; adds a dependency. Not needed. |
| Current KMeans | Splits zips arbitrarily | Violates the minimum criterion; replaced. |

## Worst cases
- **One zip larger than any biker's capacity** (`REALISTIC_DAY` has 1138 with 56 stops > 48): it cannot stay atomic.
  Spec'd behaviour: A2 keeps zips whole and flags the oversize zip (A3 validator warning); A6 splits only that zip,
  geographically, into the minimum number of parts.
- More zips than bikers fit evenly: balance degrades gracefully, a biker may get one extra small zip.
- Stops without a postal code or not geocoded: put in an "unassigned" bucket and surfaced as a warning, never silently dropped.

## Recommendation
1. **A2:** zip-atomic greedy LPT by stop count.
2. **A3/A4:** validator + manual "move a zip" override handle anything the heuristic gets wrong.
3. **A5/A6:** weight by estimated time, prefer geographic neighbours, split only unavoidable oversize zips.

**Fallback if this proves insufficient:** zip-atomic only + manual override (A2–A4), which already meets
Gergő's stated minimum, and defer A5/A6.
