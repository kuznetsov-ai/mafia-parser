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

### Tests

Added 3 new Titan scenarios and desktop+mobile dual-viewport runner:

- **S13** `no_horizontal_overflow` — asserts `scrollWidth <= innerWidth` after load AND after clicking a seating-ready tournament + analyze.
- **S14** `seating_badge_responsive` — asserts text visible on desktop, icon-only on mobile.
- **S15** `no_cancelled_tournaments` — asserts no rendered tournament name contains "cancelled".

Runner flags:
- `--mobile` — single mobile run (390x844, `is_mobile=True`)
- `--both` — run desktop (1440x900) then mobile sequentially

Results: **30/30 PASS** (15 desktop + 15 mobile).
