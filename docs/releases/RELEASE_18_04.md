# Release 18.04.2026

## Mobile UX fixes + cancelled tournaments filter

### Mobile: seating badge is icon-only

The "✓ seating ready" badge was consuming horizontal space on mobile and pushing tournament names out of view.

On viewports ≤600px the badge now shows only the icon (✓ for seating ready, ⏳ for no seating). Desktop continues to display the full text.

### Mobile: no horizontal overflow

The results table (~420px minimum) caused the whole page to overflow and shift right on ≤390px viewports.

Added `@media (max-width: 600px)` styles:
- Reduced body/card padding
- Smaller table cell padding and font-size
- Hid rank column (`#`) on mobile
- Smaller pct-meetings progress bar
- Smaller h1 / letter-spacing

### Cancelled tournaments hidden

Tournaments whose name contains "cancelled" / "canceled" (case-insensitive) are now filtered out client-side in `renderTournaments()`.

### Follow-up fix (same day)

On iPhone widths (375/393px), the results table was still wider than the card and its right column was clipped. Fixes:
- Wrapped `<table>` in a `.table-scroll` div (overflow-x: auto) so only the table scrolls if content exceeds.
- Moved the `@media (max-width: 600px)` block to the end of the stylesheet so `.bar-bg { width: 28px; }` actually overrides the default 60px.
- Shortened the `colTotal` translation to "Total" / "Всего" / "Всього" (was "Total in tournament" / "Всего в турнире" / "Всього в турнірі").
- Mobile-only JS tweak shortens the `% meetings` header to `%` on ≤600px viewports to free horizontal space.

Verified at 375/393/430px: `docW == innerWidth`, all columns visible with bar + value (e.g. `58%`).

### Show players with 0 joint games

Previously, the results table listed only players with `joint >= 1`. Now it includes every seated tournament participant (except the target) so you can see whom you have no crossings with.

Sort order: by `joint` desc, then by nickname asc as tiebreaker. Both `analyze()` (mafgame) and `imafia_analyze()` updated.

Verified in Four Seasons Cyprus Open (30 participants) — target played 12 games, 29 rows, last row shows `joint=0, pct=0%`.

### Tests

Added 3 new Titan scenarios and desktop+mobile dual-viewport runner:

- **S13** `no_horizontal_overflow` — asserts `scrollWidth <= innerWidth` after load AND after clicking a seating-ready tournament + analyze.
- **S14** `seating_badge_responsive` — asserts text visible on desktop, icon-only on mobile.
- **S15** `no_cancelled_tournaments` — asserts no rendered tournament name contains "cancelled".

Runner flags:
- `--mobile` — single mobile run (390x844, `is_mobile=True`)
- `--both` — run desktop (1440x900) then mobile sequentially

Results: **30/30 PASS** (15 desktop + 15 mobile).
