# Release 11.09.2026

## mafgame.org: fix missing tournaments beyond page 1

### Bug

`mafgame.org` had a real, visible, approved tournament (#710, Mafia World Championship 2026, starts 12.09) that never showed on the site despite being within the ±2-day window.

### Root cause

`mafgame.org`'s `/tournaments` search endpoint ignores our `date_from`/`date_to`/`per_page` query params server-side — a ±2-day request returned tournaments spanning a full year, capped at 10 results per page regardless of the requested `per_page`. `api_tournaments()` only fetched page 1 and applied the date filter client-side, so any in-window tournament ranked beyond position 10 by mafgame's own (non-date) ordering silently vanished. Tournament #710 sat on page 2 of 9.

### Fix

`api_tournaments()` now loops through all pages (via the response's `last_page`) before applying the client-side date filter. Verified via Flask `test_client` against live `mafgame.org`: #710 now present in `/api/tournaments`; confirmed again on the live prod endpoint after deploy.

No UI/template changes — API/data-fetching only.
