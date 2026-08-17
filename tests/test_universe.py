import json
import unittest

from sac_scanner.universe import build_universe, load_universe_symbols


NASDAQ_SAMPLE = """Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares
TINY|Tiny Biotech Inc. Common Stock|S|N|N|100|N|N
ETFZ|Index Fund ETF|G|N|N|100|Y|N
WTT|Widget Corp Warrant|S|N|N|100|N|N
TEST|Test Company Common Stock|S|Y|N|100|N|N
File Creation Time: 0816202620:00|||||||
"""


OTHER_SAMPLE = """ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol
LITT|Little Retailer Inc. Common Stock|A|LITT|N|100|N|LITT
PREF|Bank Preferred Shares|N|PREF|N|100|N|PREF
FUND|Income Fund|P|FUND|N|100|N|FUND
"""


class JsonPathFixture:
    def __init__(self, payload):
        self.payload = payload

    def read_text(self, encoding="utf-8"):
        return json.dumps(self.payload)


class UniverseTest(unittest.TestCase):
    def test_build_universe_keeps_common_stocks_and_excludes_non_common_rows(self):
        rows = build_universe(NASDAQ_SAMPLE, OTHER_SAMPLE)

        self.assertEqual([row.symbol for row in rows], ["LITT", "TINY"])
        self.assertEqual(rows[0].exchange, "A")
        self.assertEqual(rows[1].exchange, "NASDAQ")

    def test_load_universe_symbols_reads_portable_json_cache(self):
        symbols = load_universe_symbols(
            JsonPathFixture(
                {
                    "symbols": [
                        {"symbol": "tiny"},
                        {"symbol": "TINY"},
                        {"symbol": "LITT"},
                    ]
                }
            )
        )

        self.assertEqual(symbols, ["TINY", "LITT"])


if __name__ == "__main__":
    unittest.main()
