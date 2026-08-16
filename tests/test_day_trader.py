import tempfile
import unittest
from pathlib import Path

from sac_scanner.day_trader import (
    DayTraderConfig,
    approve_entry,
    close_position,
    load_ledger_events,
    status,
)


class DayTraderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.state_path = root / "state.json"
        self.ledger_path = root / "ledger.jsonl"
        self.config = DayTraderConfig(account_size=1000, risk_per_trade=50, reward_target=100)

    def tearDown(self):
        self.tmp.cleanup()

    def test_manual_approval_appends_sac_entry_to_shared_ledger_shape(self):
        result = approve_entry(
            candidate_fixture(),
            config=self.config,
            state_path=self.state_path,
            ledger_path=self.ledger_path,
        )

        self.assertTrue(result["ok"])
        events = load_ledger_events(self.ledger_path)
        entry = events[-1]
        self.assertEqual(entry["event_type"], "ENTRY")
        self.assertEqual(entry["asset_class"], "stock")
        self.assertEqual(entry["source"], "sac_day_trader")
        self.assertEqual(entry["strategy_id"], "sac_manual_day_trade")
        self.assertEqual(entry["metadata"]["trade_mode"], "DAY")
        self.assertEqual(entry["metadata"]["grade"], "A")
        self.assertLess(entry["cash_delta"], 0)

    def test_open_position_limit_locks_additional_manual_entries(self):
        approve_entry(
            candidate_fixture(),
            config=self.config,
            state_path=self.state_path,
            ledger_path=self.ledger_path,
        )

        second = approve_entry(
            {**candidate_fixture(), "symbol": "NEXT"},
            config=self.config,
            state_path=self.state_path,
            ledger_path=self.ledger_path,
        )
        third = approve_entry(
            {**candidate_fixture(), "symbol": "DONE"},
            config=self.config,
            state_path=self.state_path,
            ledger_path=self.ledger_path,
        )

        self.assertTrue(second["ok"])
        self.assertFalse(third["ok"])
        self.assertIn("already open", third["error"])

    def test_manual_close_appends_exit_and_realizes_pnl(self):
        approved = approve_entry(
            candidate_fixture(),
            config=self.config,
            state_path=self.state_path,
            ledger_path=self.ledger_path,
        )
        position_id = approved["position"]["position_id"]

        closed = close_position(
            position_id,
            3.05,
            state_path=self.state_path,
            ledger_path=self.ledger_path,
            config=self.config,
        )

        self.assertTrue(closed["ok"])
        events = load_ledger_events(self.ledger_path)
        exit_event = events[-1]
        self.assertEqual(exit_event["event_type"], "EXIT")
        self.assertEqual(exit_event["side"], "SELL")
        self.assertGreater(exit_event["cash_delta"], 0)
        self.assertGreater(exit_event["realized_pnl"], 0)
        current = status(
            state_path=self.state_path,
            ledger_path=self.ledger_path,
            config=self.config,
        )
        self.assertEqual(current["open_positions"], [])
        self.assertEqual(len(current["closed_positions"]), 1)


def candidate_fixture():
    return {
        "symbol": "TINY",
        "grade": "A",
        "score": 97,
        "price": 2.65,
        "change_percent": 32.5,
        "relative_volume": 8.2,
        "float_millions": 7.6,
        "target_profit_price": 3.1,
        "passes": [
            "price is within the $1-$20 small-account range",
            "strong percent move at 32.5%",
            "relative volume is 8.2x",
        ],
        "warnings": [],
    }


if __name__ == "__main__":
    unittest.main()
