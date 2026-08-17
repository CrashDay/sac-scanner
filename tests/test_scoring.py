import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from sac_scanner.live import CACHE_HEADER_PREFIX, build_live_scan
from sac_scanner.models import Candidate, RiskPlan
from sac_scanner.scoring import evaluate


ACTIVE_SCAN_TIME = datetime(2026, 8, 17, 10, 30, tzinfo=ZoneInfo("America/New_York"))
CLOSED_SCAN_TIME = datetime(2026, 8, 16, 10, 30, tzinfo=ZoneInfo("America/New_York"))


class FakeSchwabClient:
    def get_movers(self, symbol_id, *, sort="PERCENT_CHANGE_UP", frequency=0):
        if symbol_id == "EQUITY_ALL" and sort == "PERCENT_CHANGE_UP":
            return {"screeners": [{"symbol": "TINY"}]}
        return {"screeners": []}

    def get_quotes(self, symbols):
        return {
            "TINY": {
                "realtime": True,
                "fundamental": {
                    "sharesOutstanding": 90000000,
                },
                "quote": {
                    "lastPrice": 2.65,
                    "closePrice": 2.00,
                    "netPercentChange": 32.5,
                    "totalVolume": 5800000,
                },
            }
        }

    def get_price_history(self, symbol):
        return {
            "previousClose": 2.00,
            "candles": [
                {"volume": 900000, "close": 1.85},
                {"volume": 1000000, "close": 1.92},
                {"volume": 1100000, "close": 2.00},
            ],
        }


class CachePathFixture:
    def __init__(self, text=""):
        self.text = text
        self.writes: list[str] = []
        self.parent = self

    def read_text(self, encoding="utf-8"):
        return self.text

    def write_text(self, text, encoding="utf-8"):
        self.text = text
        self.writes.append(text)

    def mkdir(self, parents=False, exist_ok=False):
        return None

    def __str__(self):
        return "cache/watchlist.txt"


class UniversePathFixture:
    def __init__(self, symbols):
        self.symbols = symbols

    def read_text(self, encoding="utf-8"):
        import json

        return json.dumps({"symbols": [{"symbol": symbol} for symbol in self.symbols]})

    def __str__(self):
        return "data/universe/equities.json"


class MissingUniversePathFixture:
    def read_text(self, encoding="utf-8"):
        raise OSError("missing universe")

    def __str__(self):
        return "missing/universe.json"


class ScoringTest(unittest.TestCase):
    def test_a_quality_candidate_meets_core_pdf_criteria(self):
        result = evaluate(
            Candidate(
                symbol="TINY",
                price=2.65,
                previous_close=2.00,
                relative_volume=5.8,
                has_news=True,
                news_age_days=0.2,
                float_millions=13.3,
                target_potential_percent=21,
                setup="pullback near high of day",
                entry_price=2.68,
                stop_price=2.52,
            ),
            RiskPlan(account_size=1000, risk_per_trade=50, reward_target=100),
        )

        self.assertEqual(result.grade, "A")
        self.assertEqual(result.max_shares_by_cash, 377)
        self.assertEqual(result.max_shares_by_risk, 312)
        self.assertFalse(result.fail_reasons)

    def test_missing_news_only_reduces_conviction(self):
        result = evaluate(
            Candidate(
                symbol="NOCAT",
                price=9.35,
                previous_close=7.95,
                relative_volume=9,
                has_news=False,
                float_millions=11.2,
                target_potential_percent=22,
            ),
            RiskPlan(),
        )

        self.assertEqual(result.grade, "B")
        self.assertIn("no fresh catalyst", result.warnings)
        self.assertNotIn("no news catalyst", result.fail_reasons)

    def test_stale_news_is_not_treated_as_a_live_catalyst(self):
        result = evaluate(
            Candidate(
                symbol="STALE",
                price=8.4,
                previous_close=7.1,
                relative_volume=7.4,
                has_news=False,
                news_age_days=6.0,
                float_millions=9.2,
                target_potential_percent=24,
            ),
            RiskPlan(),
        )

        self.assertEqual(result.grade, "B")
        self.assertIn("catalyst is stale at 6.0 day(s) old", result.warnings)

    def test_price_below_one_dollar_is_rejected(self):
        result = evaluate(
            Candidate(
                symbol="QUIK",
                price=0.82,
                previous_close=0.55,
                relative_volume=12.1,
                has_news=True,
                float_millions=4.0,
            ),
            RiskPlan(),
        )

        self.assertEqual(result.grade, "Reject")
        self.assertIn("price is outside the $1-$20 range", result.fail_reasons)

    def test_missing_live_price_does_not_crash(self):
        result = evaluate(
            Candidate(
                symbol="NOPRICE",
                price=0,
                previous_close=0,
                relative_volume=0,
                has_news=True,
                float_millions=10,
            ),
            RiskPlan(),
        )

        self.assertEqual(result.grade, "Reject")
        self.assertEqual(result.max_shares_by_cash, 0)

    def test_live_scan_uses_schwab_quote_and_fundamentals_only(self):
        cache = CachePathFixture()
        payload = build_live_scan(
            risk=RiskPlan(),
            client=FakeSchwabClient(),
            now=ACTIVE_SCAN_TIME,
            watchlist_path=cache,
            universe_path=MissingUniversePathFixture(),
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["source"], "schwab_movers")
        self.assertEqual(payload["symbols"], ["TINY"])
        self.assertEqual(payload["results"][0]["symbol"], "TINY")
        self.assertEqual(payload["results"][0]["float_millions"], 90)
        self.assertEqual(payload["results"][0]["float_source"], "schwab_shares_outstanding")
        self.assertEqual(payload["results"][0]["news_headline"], "")
        self.assertFalse(payload["results"][0]["has_news"])
        self.assertEqual(payload["results"][0]["setup"], "")
        self.assertIsNone(payload["results"][0]["max_shares_by_risk"])
        self.assertIn(CACHE_HEADER_PREFIX, cache.writes[0])
        self.assertTrue(cache.writes[0].endswith("\nTINY\n"))

    def test_live_scan_uses_universe_file_when_available(self):
        class UniverseClient(FakeSchwabClient):
            def get_movers(self, symbol_id, *, sort="PERCENT_CHANGE_UP", frequency=0):
                raise AssertionError("universe scan should not call movers")

        payload = build_live_scan(
            risk=RiskPlan(),
            client=UniverseClient(),
            now=ACTIVE_SCAN_TIME,
            watchlist_path=CachePathFixture(),
            universe_path=UniversePathFixture(["TINY"]),
        )

        self.assertEqual(payload["source"], "schwab_universe")
        self.assertEqual(payload["discovery"]["universe_symbol_count"], 1)
        self.assertEqual(payload["symbols"], ["TINY"])

    def test_live_scan_does_not_accept_local_float_or_news_overrides(self):
        payload = build_live_scan(
            risk=RiskPlan(),
            client=FakeSchwabClient(),
            now=ACTIVE_SCAN_TIME,
            watchlist_path=CachePathFixture(),
            universe_path=MissingUniversePathFixture(),
        )

        self.assertEqual(payload["results"][0]["float_millions"], 90)
        self.assertEqual(payload["results"][0]["float_source"], "schwab_shares_outstanding")
        self.assertEqual(payload["results"][0]["news_headline"], "")
        self.assertFalse(payload["results"][0]["has_news"])
        self.assertIn("float is above 20M at 90.0M", payload["results"][0]["fails"])

    def test_live_scan_marks_float_unknown_when_no_schwab_fundamental_exists(self):
        class NoFundamentalClient(FakeSchwabClient):
            def get_quotes(self, symbols):
                payload = super().get_quotes(symbols)
                payload["TINY"].pop("fundamental")
                return payload

        payload = build_live_scan(
            risk=RiskPlan(),
            client=NoFundamentalClient(),
            now=ACTIVE_SCAN_TIME,
            watchlist_path=CachePathFixture(),
            universe_path=MissingUniversePathFixture(),
        )

        self.assertEqual(payload["results"][0]["float_millions"], 999999.0)
        self.assertEqual(payload["results"][0]["float_source"], "unknown")

    def test_live_scan_filters_symbols_outside_display_price_guardrails(self):
        class MultiPriceClient(FakeSchwabClient):
            def get_movers(self, symbol_id, *, sort="PERCENT_CHANGE_UP", frequency=0):
                if symbol_id == "EQUITY_ALL" and sort == "PERCENT_CHANGE_UP":
                    return {"screeners": [{"symbol": "CHEAP"}, {"symbol": "OKAY"}, {"symbol": "RICH"}]}
                return {"screeners": []}

            def get_quotes(self, symbols):
                return {
                    "CHEAP": {"realtime": True, "quote": {"lastPrice": 0.5, "closePrice": 0.4, "netPercentChange": 25, "totalVolume": 5800000}},
                    "OKAY": {"realtime": True, "quote": {"lastPrice": 2.65, "closePrice": 2.0, "netPercentChange": 32.5, "totalVolume": 5800000}},
                    "RICH": {"realtime": True, "quote": {"lastPrice": 30.0, "closePrice": 28.0, "netPercentChange": 7.1, "totalVolume": 5800000}},
                }

        payload = build_live_scan(
            risk=RiskPlan(),
            client=MultiPriceClient(),
            now=ACTIVE_SCAN_TIME,
            watchlist_path=CachePathFixture(),
            universe_path=MissingUniversePathFixture(),
        )

        self.assertEqual([item["symbol"] for item in payload["results"]], ["OKAY"])

    def test_live_scan_returns_empty_results_when_active_schwab_movers_are_empty(self):
        class EmptyMoverClient(FakeSchwabClient):
            def get_movers(self, symbol_id, *, sort="PERCENT_CHANGE_UP", frequency=0):
                return {"screeners": []}

        payload = build_live_scan(
            risk=RiskPlan(),
            client=EmptyMoverClient(),
            now=ACTIVE_SCAN_TIME,
            watchlist_path=CachePathFixture("CACHED\n"),
            universe_path=MissingUniversePathFixture(),
        )

        self.assertEqual(payload["symbols"], [])
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["discovery"]["symbol_count"], 0)

    def test_live_scan_uses_cached_watchlist_when_scan_window_is_closed(self):
        class ClosedClient(FakeSchwabClient):
            def get_movers(self, symbol_id, *, sort="PERCENT_CHANGE_UP", frequency=0):
                raise AssertionError("closed scanner should not call Schwab movers")

        cache = CachePathFixture(f"{CACHE_HEADER_PREFIX}\n# generated_at=2026-08-14T23:59:00+00:00\nTINY\n")
        payload = build_live_scan(
            risk=RiskPlan(),
            client=ClosedClient(),
            now=CLOSED_SCAN_TIME,
            watchlist_path=cache,
        )

        self.assertEqual(payload["source"], "cached_watchlist")
        self.assertFalse(payload["discovery"]["scan_active"])
        self.assertEqual(payload["symbols"], ["TINY"])
        self.assertEqual(payload["results"][0]["symbol"], "TINY")
        self.assertEqual(cache.writes, [])

    def test_live_scan_ignores_legacy_watchlist_when_scan_window_is_closed(self):
        cache = CachePathFixture("TINY\n")
        payload = build_live_scan(
            risk=RiskPlan(),
            client=FakeSchwabClient(),
            now=CLOSED_SCAN_TIME,
            watchlist_path=cache,
        )

        self.assertEqual(payload["source"], "cached_watchlist")
        self.assertEqual(payload["symbols"], [])
        self.assertEqual(payload["results"], [])


if __name__ == "__main__":
    unittest.main()
