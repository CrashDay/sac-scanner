import unittest

from sac_scanner.live import build_live_scan
from sac_scanner.models import Candidate, RiskPlan
from sac_scanner.scoring import evaluate


class FakeSchwabClient:
    def get_quotes(self, symbols):
        return {
            "TINY": {
                "realtime": True,
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


class PathFixture:
    def __init__(self, text):
        self.text = text

    def read_text(self, encoding="utf-8"):
        return self.text


class JsonFixture:
    def __init__(self, payload):
        self.payload = payload

    def read_text(self, encoding="utf-8"):
        import json

        return json.dumps(self.payload)


class ScoringTest(unittest.TestCase):
    def test_a_quality_candidate_meets_core_pdf_criteria(self):
        result = evaluate(
            Candidate(
                symbol="TINY",
                price=2.65,
                previous_close=2.00,
                relative_volume=5.8,
                has_news=True,
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

    def test_missing_news_prevents_a_quality_grade(self):
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

        self.assertNotEqual(result.grade, "A")
        self.assertIn("no news catalyst", result.fail_reasons)

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

    def test_live_scan_uses_schwab_quote_and_local_annotations(self):
        payload = build_live_scan(
            watchlist_path=PathFixture("TINY"),
            annotations_path=JsonFixture(
                {
                    "TINY": {
                        "has_news": True,
                        "float_millions": 13.3,
                        "target_potential_percent": 21,
                        "setup": "pullback",
                        "entry_price": 2.68,
                        "stop_price": 2.52,
                    }
                }
            ),
            risk=RiskPlan(),
            client=FakeSchwabClient(),
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["results"][0]["symbol"], "TINY")
        self.assertEqual(payload["results"][0]["grade"], "A")


if __name__ == "__main__":
    unittest.main()
