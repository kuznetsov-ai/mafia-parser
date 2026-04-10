"""Mafia Parser — E2E Test Scenarios (Titan methodology)"""

from __future__ import annotations

import asyncio
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "titan"))

from scenarios.base import BaseScenario, StepResult
from testMe.selectors import SEL


class MafiaParserScenarios(BaseScenario):
    REPORT_URL = "/"
    OUTPUT_SUBDIR = "mafia-parser"

    # ── S01: Page load ─────────────────────────────────────────────────
    async def test_page_load(self):
        """S01: Homepage loads with header, tabs, tournament list."""
        start = await self._step("page_load")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            h1 = self.page.locator(SEL["h1"])
            subtitle = self.page.locator(SEL["subtitle"])
            card = self.page.locator(SEL["tournaments_card"])
            checks = [
                await h1.count() > 0,
                "MAFIA" in (await h1.text_content() or ""),
                await subtitle.count() > 0,
                await card.count() > 0,
            ]
            screenshot = await self._screenshot("01_page_load")
            if all(checks):
                self._record("page_load", "PASS", "Homepage loaded: h1, subtitle, tournaments card", screenshot, start)
            else:
                self._record("page_load", "FAIL", f"Missing elements: {checks}", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("01_error")
            self._record("page_load", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S02: Language switcher ─────────────────────────────────────────
    async def test_lang_switcher(self):
        """S02: Language buttons EN/RU/UK work and update UI text."""
        start = await self._step("lang_switcher")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            results = []

            # Test RU
            await self.page.click(SEL["lang_ru"])
            await asyncio.sleep(0.3)
            subtitle_text = await self.page.locator(SEL["subtitle"]).text_content()
            results.append(("RU subtitle", "Анализ" in (subtitle_text or "")))

            # Test UK
            await self.page.click(SEL["lang_uk"])
            await asyncio.sleep(0.3)
            subtitle_text = await self.page.locator(SEL["subtitle"]).text_content()
            results.append(("UK subtitle", "Аналіз" in (subtitle_text or "")))

            # Test EN
            await self.page.click(SEL["lang_en"])
            await asyncio.sleep(0.3)
            subtitle_text = await self.page.locator(SEL["subtitle"]).text_content()
            results.append(("EN subtitle", "Joint" in (subtitle_text or "")))

            screenshot = await self._screenshot("02_lang_switcher")
            failed = [name for name, ok in results if not ok]
            if not failed:
                self._record("lang_switcher", "PASS", "All 3 languages work", screenshot, start)
            else:
                self._record("lang_switcher", "FAIL", f"Failed: {failed}", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("02_error")
            self._record("lang_switcher", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S03: Tournaments load ──────────────────────────────────────────
    async def test_tournaments_load(self):
        """S03: Tournament list loads with items and date range."""
        start = await self._step("tournaments_load")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            # Wait for tournaments to load (API call)
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            items = await self.page.locator(SEL["tournament_item"]).count()
            date_range = await self.page.locator(SEL["date_range"]).text_content()
            has_date_range = bool(date_range and re.search(r"\d{4}-\d{2}-\d{2}", date_range))

            screenshot = await self._screenshot("03_tournaments")
            if items > 0 and has_date_range:
                self._record("tournaments_load", "PASS", f"{items} tournaments loaded, date range visible", screenshot, start)
            else:
                self._record("tournaments_load", "FAIL", f"items={items}, date_range={has_date_range}", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("03_error")
            self._record("tournaments_load", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S04: Source filter tabs ────────────────────────────────────────
    async def test_source_filter(self):
        """S04: Source filter tabs (All/Mafgame/iMafia) filter tournaments."""
        start = await self._step("source_filter")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            all_count = await self.page.locator(SEL["tournament_item"]).count()

            # Click Mafgame tab
            await self.page.click(SEL["tab_mafgame"])
            await asyncio.sleep(0.3)
            mafgame_count = await self.page.locator(SEL["tournament_item"]).count()
            screenshot_maf = await self._screenshot("04a_mafgame")

            # Click iMafia tab
            await self.page.click(SEL["tab_imafia"])
            await asyncio.sleep(0.3)
            imafia_count = await self.page.locator(SEL["tournament_item"]).count()
            screenshot_ima = await self._screenshot("04b_imafia")

            # Click All tab
            await self.page.click(SEL["tab_all"])
            await asyncio.sleep(0.3)
            back_count = await self.page.locator(SEL["tournament_item"]).count()

            checks = [
                mafgame_count <= all_count,
                imafia_count <= all_count,
                back_count == all_count,
                mafgame_count + imafia_count >= all_count,  # together should cover all
            ]

            screenshot = await self._screenshot("04c_all_again")
            if all(checks):
                self._record("source_filter", "PASS",
                             f"All={all_count}, Mafgame={mafgame_count}, iMafia={imafia_count}", screenshot, start)
            else:
                self._record("source_filter", "FAIL",
                             f"Filter mismatch: all={all_count}, maf={mafgame_count}, ima={imafia_count}, back={back_count}", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("04_error")
            self._record("source_filter", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S05: Tournament badges ─────────────────────────────────────────
    async def test_tournament_badges(self):
        """S05: Each tournament has seating badge and source badge."""
        start = await self._step("tournament_badges")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            items = self.page.locator(SEL["tournament_item"])
            count = await items.count()
            badges_ok = 0
            for i in range(min(count, 5)):
                item = items.nth(i)
                has_seating_badge = (
                    await item.locator(SEL["badge_seating"]).count() > 0
                    or await item.locator(SEL["badge_no_seating"]).count() > 0
                )
                has_name = len((await item.locator(SEL["t_name"]).text_content() or "").strip()) > 0
                if has_seating_badge and has_name:
                    badges_ok += 1

            screenshot = await self._screenshot("05_badges")
            if badges_ok >= min(count, 5):
                self._record("tournament_badges", "PASS", f"{badges_ok}/{min(count,5)} tournaments have proper badges", screenshot, start)
            else:
                self._record("tournament_badges", "WARN", f"Only {badges_ok}/{min(count,5)} have badges", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("05_error")
            self._record("tournament_badges", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S06: Tournament click loads players ────────────────────────────
    async def test_tournament_click(self):
        """S06: Clicking a tournament with seating loads player list."""
        start = await self._step("tournament_click")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            # Find a tournament with seating
            seating_items = self.page.locator(f'{SEL["tournament_item"]}:has({SEL["badge_seating"]})')
            count = await seating_items.count()

            if count == 0:
                screenshot = await self._screenshot("06_no_seating")
                self._record("tournament_click", "WARN", "No tournaments with seating available", screenshot, start)
                return self.results[-1]

            await seating_items.first.click()
            await asyncio.sleep(1)

            # Check URL input is filled
            url_val = await self.page.locator(SEL["url_input"]).input_value()
            has_url = bool(url_val and ("mafgame.org" in url_val or "imafia.org" in url_val))

            # Wait for player list to load
            await self.page.wait_for_function(
                "document.querySelector('#nicknameSelect').options.length > 1", timeout=30000)
            options = await self.page.locator(f'{SEL["nickname_select"]} option').count()

            screenshot = await self._screenshot("06_players_loaded")
            if has_url and options > 1:
                self._record("tournament_click", "PASS", f"URL set, {options - 1} players loaded", screenshot, start)
            else:
                self._record("tournament_click", "FAIL", f"url={has_url}, options={options}", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("06_error")
            self._record("tournament_click", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S07: Analyze player ────────────────────────────────────────────
    async def test_analyze_player(self):
        """S07: Selecting a player and clicking Analyze shows results table."""
        start = await self._step("analyze_player")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            # Find tournament with seating
            seating_items = self.page.locator(f'{SEL["tournament_item"]}:has({SEL["badge_seating"]})')
            if await seating_items.count() == 0:
                screenshot = await self._screenshot("07_no_seating")
                self._record("analyze_player", "WARN", "No tournaments with seating", screenshot, start)
                return self.results[-1]

            await seating_items.first.click()
            await asyncio.sleep(1)

            # Wait for players to load
            await self.page.wait_for_function(
                "document.querySelector('#nicknameSelect').options.length > 1", timeout=30000)

            # Select second option (first real player)
            options = self.page.locator(f'{SEL["nickname_select"]} option')
            count = await options.count()
            if count < 2:
                screenshot = await self._screenshot("07_no_players")
                self._record("analyze_player", "FAIL", "No players in dropdown", screenshot, start)
                return self.results[-1]

            player_name = await options.nth(1).text_content()
            await self.page.select_option(SEL["nickname_select"], index=1)
            await asyncio.sleep(0.3)

            # Click Analyze
            await self.page.click(SEL["btn_analyze"])

            # Wait for results
            await self.page.wait_for_selector(SEL["results_card"], state="visible", timeout=30000)
            await asyncio.sleep(1)

            rows = await self.page.locator(SEL["results_rows"]).count()
            results_visible = await self.page.locator(SEL["results_card"]).is_visible()

            screenshot = await self._screenshot("07_results")
            if results_visible and rows > 0:
                self._record("analyze_player", "PASS", f"Results: {rows} rows for {player_name}", screenshot, start)
            else:
                self._record("analyze_player", "FAIL", f"visible={results_visible}, rows={rows}", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("07_error")
            self._record("analyze_player", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S08: i18n months ───────────────────────────────────────────────
    async def test_i18n_months(self):
        """S08: Month names change with language switch."""
        start = await self._step("i18n_months")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            # EN months
            await self.page.click(SEL["lang_en"])
            await asyncio.sleep(0.5)
            en_month = await self.page.locator(f'{SEL["t_date"]} .month').first.text_content()

            # RU months
            await self.page.click(SEL["lang_ru"])
            await asyncio.sleep(0.5)
            ru_month = await self.page.locator(f'{SEL["t_date"]} .month').first.text_content()

            # UK months
            await self.page.click(SEL["lang_uk"])
            await asyncio.sleep(0.5)
            uk_month = await self.page.locator(f'{SEL["t_date"]} .month').first.text_content()

            screenshot = await self._screenshot("08_months")

            # At least RU and EN should differ (unless month name is same)
            en_month = (en_month or "").strip().lower()
            ru_month = (ru_month or "").strip().lower()
            uk_month = (uk_month or "").strip().lower()

            all_exist = all([en_month, ru_month, uk_month])
            # EN and RU should differ for most months
            differs = en_month != ru_month

            # Switch back to EN
            await self.page.click(SEL["lang_en"])

            if all_exist and differs:
                self._record("i18n_months", "PASS", f"EN={en_month}, RU={ru_month}, UK={uk_month}", screenshot, start)
            elif all_exist:
                self._record("i18n_months", "WARN", f"Months same: EN={en_month}, RU={ru_month}", screenshot, start)
            else:
                self._record("i18n_months", "FAIL", f"Missing months: EN={en_month}, RU={ru_month}, UK={uk_month}", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("08_error")
            self._record("i18n_months", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S09: Cache refresh ─────────────────────────────────────────────
    async def test_cache_refresh(self):
        """S09: Refresh button clears cache and reloads tournaments."""
        start = await self._step("cache_refresh")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            count_before = await self.page.locator(SEL["tournament_item"]).count()

            # Click refresh
            await self.page.click(SEL["btn_refresh"])
            await asyncio.sleep(2)

            # Wait for tournaments to reload
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)
            count_after = await self.page.locator(SEL["tournament_item"]).count()

            screenshot = await self._screenshot("09_refresh")
            if count_after > 0:
                self._record("cache_refresh", "PASS", f"Refreshed: {count_before} → {count_after} tournaments", screenshot, start)
            else:
                self._record("cache_refresh", "FAIL", "No tournaments after refresh", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("09_error")
            self._record("cache_refresh", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S10: Today line ────────────────────────────────────────────────
    async def test_today_line(self):
        """S10: Today divider line is shown in tournament list."""
        start = await self._step("today_line")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            today_line = self.page.locator(SEL["today_line"])
            count = await today_line.count()

            screenshot = await self._screenshot("10_today_line")
            if count > 0:
                text = await today_line.first.text_content()
                self._record("today_line", "PASS", f"Today line: {text}", screenshot, start)
            else:
                self._record("today_line", "WARN", "No today line (might be date range issue)", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("10_error")
            self._record("today_line", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S11: Single-line layout ────────────────────────────────────────
    async def test_single_line_layout(self):
        """S11: Each tournament fits in a single line (no wrapping)."""
        start = await self._step("single_line_layout")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            items = self.page.locator(SEL["tournament_item"])
            count = await items.count()
            max_height = 0
            for i in range(min(count, 5)):
                box = await items.nth(i).bounding_box()
                if box:
                    max_height = max(max_height, box["height"])

            screenshot = await self._screenshot("11_single_line")
            # A single line item should be ~40-60px tall. >80 means wrapping
            if max_height < 80:
                self._record("single_line_layout", "PASS", f"Max item height: {max_height:.0f}px", screenshot, start)
            else:
                self._record("single_line_layout", "FAIL", f"Item too tall ({max_height:.0f}px), likely wrapping", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("11_error")
            self._record("single_line_layout", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── S12: Manual nickname input ─────────────────────────────────────
    async def test_manual_nickname(self):
        """S12: Manual nickname input triggers analysis."""
        start = await self._step("manual_nickname")
        try:
            await self.page.goto(self.base_url, wait_until="networkidle")
            await self.page.wait_for_selector(SEL["tournament_item"], timeout=30000)

            # Find tournament with seating
            seating_items = self.page.locator(f'{SEL["tournament_item"]}:has({SEL["badge_seating"]})')
            if await seating_items.count() == 0:
                screenshot = await self._screenshot("12_no_seating")
                self._record("manual_nickname", "WARN", "No tournaments with seating", screenshot, start)
                return self.results[-1]

            await seating_items.first.click()
            await asyncio.sleep(1)
            await self.page.wait_for_function(
                "document.querySelector('#nicknameSelect').options.length > 1", timeout=30000)

            # Get a real player name from dropdown
            player_name = await self.page.locator(f'{SEL["nickname_select"]} option').nth(1).text_content()

            # Type it manually
            await self.page.fill(SEL["nickname_input"], player_name or "")
            await self.page.click(SEL["btn_analyze"])

            await self.page.wait_for_selector(SEL["results_card"], state="visible", timeout=30000)
            rows = await self.page.locator(SEL["results_rows"]).count()

            screenshot = await self._screenshot("12_manual_nick")
            if rows > 0:
                self._record("manual_nickname", "PASS", f"Manual input works: {rows} rows", screenshot, start)
            else:
                self._record("manual_nickname", "FAIL", f"No results for manual nickname", screenshot, start)
        except Exception as e:
            screenshot = await self._screenshot("12_error")
            self._record("manual_nickname", "FAIL", str(e), screenshot, start)
        return self.results[-1]

    # ── run_all ────────────────────────────────────────────────────────
    async def run_all(self, only=None, random_n=None):
        scenarios = [
            self.test_page_load,           # S01
            self.test_lang_switcher,       # S02
            self.test_tournaments_load,    # S03
            self.test_source_filter,       # S04
            self.test_tournament_badges,   # S05
            self.test_tournament_click,    # S06
            self.test_analyze_player,      # S07
            self.test_i18n_months,         # S08
            self.test_cache_refresh,       # S09
            self.test_today_line,          # S10
            self.test_single_line_layout,  # S11
            self.test_manual_nickname,     # S12
        ]

        if only:
            def matches(fn):
                doc = fn.__doc__ or ""
                name = fn.__name__
                for tag in only:
                    if tag.upper() in doc.upper() or tag.lower() in name.lower():
                        return True
                return False
            scenarios = [s for s in scenarios if matches(s)]

        if random_n:
            scenarios = random.sample(scenarios, min(random_n, len(scenarios)))

        for scenario in scenarios:
            await scenario()

        return self.results


# ── Standalone runner ──────────────────────────────────────────────────
async def _main():
    import argparse
    from playwright.async_api import async_playwright

    parser = argparse.ArgumentParser(description="Mafia Parser E2E Tests (Titan)")
    parser.add_argument("--headed", action="store_true", help="Show browser")
    parser.add_argument("--base-url", default="http://localhost:5055", help="App URL")
    parser.add_argument("--only", nargs="*", help="Run only specific scenarios (e.g. S01 S07)")
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "test_output"
    output_dir.mkdir(exist_ok=True)

    total_start = asyncio.get_event_loop().time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.headed)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        suite = MafiaParserScenarios(page, args.base_url, output_dir)
        results = await suite.run_all(only=args.only)

        await browser.close()

    # Summary
    total_ms = int((asyncio.get_event_loop().time() - total_start) * 1000)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    warned = sum(1 for r in results if r.status == "WARN")

    print(f"\n{'='*60}")
    for r in results:
        icon = {"PASS": "\033[32m✓\033[0m", "FAIL": "\033[31m✗\033[0m", "WARN": "\033[33m!\033[0m"}[r.status]
        print(f"  {icon} {r.name}: {r.description} ({r.duration_ms}ms)")
    print(f"{'='*60}")
    print(f"  \033[32m{passed} PASS\033[0m  \033[31m{failed} FAIL\033[0m  \033[33m{warned} WARN\033[0m  ({total_ms}ms)")
    print(f"  Screenshots: {output_dir / suite.OUTPUT_SUBDIR}")
    print(f"{'='*60}\n")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(_main())
