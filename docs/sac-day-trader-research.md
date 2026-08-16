# SAC Day Trader Research Notes

These notes capture source material for planning a new SAC-focused day-trading
simulator. This is planning material only, not an implemented strategy.

## Source: HYoQYCBW4sw YouTube Transcript

Source file reviewed:

`/Users/tonyday/.codex/attachments/95a2d348-d593-4f94-9be0-e012086a9ba0/pasted-text.txt`

Working label:

`Micro Pullback / Bull Flag Candlestick Pattern`

## Core Idea

The pattern is trend-following momentum. Do not buy the initial spike. Wait for
a strong catalyst-driven move to hit scanners, then look for the first controlled
pullback and buy as strength returns.

The trade thesis is:

1. A catalyst starts a move.
2. The move is strong enough to hit scanners.
3. The stock pulls back without breaking the move.
4. Buyers return on the tape.
5. Entry is near the pullback turn, with stop at the pullback low.
6. Profit is taken into the next extension, often around half-dollar or
   whole-dollar levels.

## Scanner Filters Mentioned

- Stock up at least `10%`
- Price between `$1` and `$20`
- High relative volume
- Low supply / float, preferably under `10M` shares available to trade
- News catalyst preferred

These are directionally aligned with the existing SAC scanner, though current
scanner constants use float under `20M`. The day-trader plan should decide
whether the active day-trade gate should tighten to `10M`.

## Chart Timeframes

Use multiple timeframes:

- Daily chart for broader context
- 5-minute chart for intraday structure
- 1-minute chart for active pattern recognition
- 10-second chart for very fast movers and IPO-like momentum

The transcript emphasizes multi-timeframe alignment. If the 10-second chart
looks acceptable but the 1-minute chart shows a doji or other warning, avoid
adding or reduce confidence.

## Candlestick Reading

Bullish signals:

- Long green body
- Close near high
- Lower wick that recovers and closes near high

Weakness / caution signals:

- Long upper wick / shooting-star style candle
- Doji after an extended move
- Big red candle
- Red candle with high volume
- Break of the prior pivot low

Doji candles are treated as indecision. They are especially important when they
appear after a fast extension.

## Volume Rules

Preferred profile:

- Increasing volume as price moves up
- Higher volume on green candles
- Lighter volume on red pullback candles

Avoid / caution:

- High-volume red candle during the pullback
- Red pullback candle volume greater than the prior green candle
- Selling volume increasing as the move gets extended

The transcript is explicit that candles without volume are incomplete
information.

## Pullback Quality

Preferred:

- One or two red candles after the initial move
- Pullback stays in the top part of the move
- Price hovers in the top `25%` of the move when possible
- Prior pivot lows keep holding, creating a stair-step pattern

Reject / caution:

- Three or four red candles on the pullback
- Pullback retraces more than `50%` of the prior leg
- Break of the previous pivot low

The speaker says more than `50%` retracement breaks the pattern. He also says
he prefers a much shallower retracement, ideally staying near the upper `25%` of
the move.

## Entry Trigger

Entry is not necessarily after candle close.

The transcript describes watching Level 2 / time and sales for green prints to
start coming through as the pullback turns. That buyer activity is treated as
confirmation that the "light has turned green."

For our simulator, we may need an approximation because Schwab quote/history
data may not provide true Level 2/time-and-sales. Possible approximations:

- completed 10-second or 1-minute candle turns green
- price reclaims prior candle high
- price breaks above pullback candle high
- volume accelerates on the turn
- bid/ask quote improves if quote fields are available

## Stop Placement

Initial stop:

- Low of the pullback

Rationale:

- Buying the initial spike requires a stop near the entire move low, which is
  too wide.
- Waiting for the pullback moves the stop up and defines risk tightly.

## Target Logic

Targets often cluster around memorable levels:

- Whole dollars: `$6`, `$7`, `$8`
- Half dollars: `$6.50`, `$7.50`, `$8.50`

The transcript describes stocks stair-stepping between these levels, with
profit-taking and resistance often appearing there.

Potential simulator target rules:

- first target at next half-dollar or whole-dollar above entry
- partial profit into first extension
- optional runner only if price keeps stair-stepping and pivot lows hold

## Re-Entry And Add-Back Logic

The transcript allows repeated trades while the pattern remains intact:

- take profit into the extension
- add back or re-enter on later pullbacks
- continue only while higher lows hold

Related pattern:

- ABCD / W pattern can be traded, but it is less preferred because it requires
  the first attempt to fail before the second attempt works.

## Risk Management Implications

Key risk idea:

- Risk is entry minus stop, not total buying power used.

The example uses a very high percentage of buying power in a small account, but
that should not be copied blindly into the simulator. For our SAC day trader,
the safer rule is still to cap dollar risk per trade and enforce daily lockouts.

Existing SAC risk framework remains relevant:

- risk about `$50` to target `$100`
- daily max loss around `-$100`
- stop after three consecutive losers
- no overnight holds

## Manual Approval Gate Ideas

Because this strategy depends on fast tape-reading and trader discretion, the
first implementation should require manual approval before simulated entry.

The approval screen should show:

- symbol
- catalyst/news
- price
- percent change
- relative volume
- float
- current pullback depth
- pullback low / proposed stop
- proposed entry trigger
- next half-dollar / whole-dollar target
- red-volume warning status
- multi-timeframe alignment status
- reason the trade is A quality or why it is only watchlist quality

## Open Questions For Planning

- Should active day-trade float max be `10M`, while scanner watch quality can
  remain `20M`?
- Can Schwab data provide enough intraday resolution for 10-second/micro
  pullbacks, or should v1 use 1-minute confirmation only?
- Should entries require completed candles, or can live quote movement arm a
  simulated entry?
- What is the maximum number of SAC day trades per day?
- Should the simulator allow add-backs/re-entries in v1, or only one entry per
  symbol until we trust the rules?
- How should the shared Trader ledger reserve capital so SAC day trades do not
  over-allocate against swing stock/options/futures simulations?

## Source: Beginner Gap And Go Transcript

Source file reviewed:

`/Users/tonyday/.codex/attachments/258855eb-7c7b-4cee-94e1-ef0c0ff50144/pasted-text.txt`

Duplicate / alternate clip also reviewed:

`/Users/tonyday/.codex/attachments/2ea3c7e5-6f46-4982-9907-3aa4c76788d6/pasted-text.txt`

Working label:

`Gap And Go / Leading Gapper Beginner Strategy`

## Added Thesis

This source reinforces that the simplest beginner strategy is to focus on the
leading percentage gainers and gappers each day. The goal is not to capture an
entire `100%` or `200%` move. The goal is to capture a small, controlled piece
of a very large move.

The source strongly argues against trading slow, narrow-range large caps for
this style because a small piece of a small move does not provide enough reward
to justify the risk.

## Gap And Go Stock Selection

Preferred stock profile:

- one of the top market gappers or percentage gainers
- fresh catalyst such as partnership, earnings, clinical-trial news, or other
  breaking news
- low-priced stock, generally `$2-$20`
- low float / low supply, generally under `20M` shares
- strong retail interest because the stock is affordable and moving quickly
- daily chart has room or known levels that explain potential resistance

The source mentions a practical `20/20` rule:

- under `$20`
- under `20M` float

It also notes exceptions can exist when the catalyst is unusually strong, but
those should probably be treated as advanced discretionary exceptions rather
than v1 simulator defaults.

## Morning Watchlist Process

The source describes sitting down around `7-8 AM` and reviewing the leading
gappers. Premarket starts as early as `4 AM`, but the practical routine is to
identify the top five gappers, then decide which has the clearest combination of
supply/demand imbalance and daily-chart opportunity.

This suggests the day-trader dashboard should have a premarket preparation
view:

- top gappers
- catalyst headline
- price
- float
- gap/change percent
- relative volume
- daily resistance / prior high notes
- whether the stock is the obvious leading focus name

## Added Entry Rule: First Pullback To VWAP / 9 EMA

The source says a safer beginner entry is the first pullback, especially:

- first pullback after a fresh breakout
- pullback to VWAP
- pullback to the 9 moving average
- entry on the first candle to make a new high

The speaker typically trades from the 1-minute chart and uses the 5-minute
chart for reference points. Five-minute pullbacks can be used as adds or
higher-confidence structure.

Potential simulator approximation:

- detect first 1-minute or 5-minute pullback after a fresh high
- require price near VWAP or 9 EMA
- arm entry above the pullback candle high
- stop below the pullback low or below VWAP/9 EMA structure

## Pullback Count Risk

The source says the first pullback is the cleanest beginner setup. The second
pullback can work but is more extended. Third pullbacks and later become risky.

Planning implication:

- first pullback: eligible for A-quality manual approval
- second pullback: lower confidence / smaller size
- third or later pullback: probably watch only in v1

## Topping Tail Warning

The source calls out topping tails as risky for longs. If a setup follows a
topping-tail candle, confidence should be reduced or the trade should be
blocked.

This aligns with the first transcript's warning about upper wicks and doji
candles after extension.

## Beginner Trade Frequency

The source recommends less trading for beginners:

- aim for one good trade per day
- maybe two trades per day
- avoid overtrading
- build consistency and confidence before trading more actively

Planning implication:

- v1 SAC day trader should use a low max-trades-per-day default
- manual gate should make "skip" as natural as "approve"
- dashboard should show whether the best opportunity has already passed

## Added Open Questions

- Should v1 cap SAC day trades at `1` approved trade per day, with an optional
  override to allow `2`?
- Should the first pullback to VWAP/9 EMA be the only v1 entry pattern?
- Should third-pullback-or-later setups be blocked entirely?
- How should the scanner identify the "obvious" top focus name among the top
  five gappers?
- Can we compute VWAP and 9 EMA reliably from Schwab intraday candles with the
  data frequency available to this project?

## Source: Pullback Qualification Transcript

Source file reviewed:

`/Users/tonyday/.codex/attachments/56101dbf-1449-4b3f-ae86-c8accb544b1d/pasted-text.txt`

Working label:

`Qualified Dip / Micro Pullback Checklist`

## Added Thesis

This source compares breakout entries with pullback entries.

Breakout entries provide faster confirmation because the stock is already
making a new high. The cost of that confirmation is a higher entry price.
Pullback entries are earlier and can offer a better risk/reward ratio, but they
need stricter qualification because the trader is buying before full breakout
confirmation.

Planning implication:

- v1 can show both "early pullback entry" and "confirmed breakout entry" zones.
- Manual approval should make clear whether the user is approving an early
  pullback starter or a later breakout confirmation.

## Pullback Qualification Checklist

Before approving a pullback trade, the source says to check:

1. Volume profile
2. Price at or above the 1-minute 9 EMA
3. MACD open / positive
4. Level 2 / tape free of major sellers
5. Preference for entries near half-dollar or whole-dollar levels

The first three are chart-based checks. The last two are execution-quality
checks.

## Volume Profile Detail

Preferred:

- price rises on increasing volume
- pullback happens on light red volume
- no high-volume selling candle on the pullback

Caution / avoid:

- price rises while volume declines
- pullback red volume is high
- high buying volume prints but price fails to move higher

If heavy green tape does not lift price, the transcript suggests a possible
hidden seller / iceberg order. That should reduce confidence or block approval.

## 9 EMA Rule

The source says price should be at or above the 1-minute 9 EMA for a clean
pullback entry.

Allowed nuance:

- a quick dip below the 9 EMA can be acceptable if price immediately reclaims it

Avoid:

- price sustains below the 9 EMA
- pullback keeps grinding lower under the 9 EMA

Potential v1 rule:

- A-quality pullback requires last price above 1-minute 9 EMA, or a reclaim
  within the most recent candle.

## MACD Rule

The source uses MACD as a filter:

- MACD open / positive supports a long pullback trade
- MACD crossing below the signal line warns of consolidation or failed momentum

Avoid:

- buying dips when MACD is against the trade

Potential v1 rule:

- mark pullback as blocked or lower confidence when MACD is closed/negative.

## Level 2 / Hidden Seller Rule

The source watches Level 2 and time-and-sales for:

- green prints at the ask as buyers return
- no large seller blocking the ask
- no iceberg-like behavior where large buy prints fail to move price

Potential limitation:

- Schwab quote/history data may not provide true Level 2 or time-and-sales.
  If unavailable, v1 should treat this as a manual checklist item rather than
  an automated gate.

Manual approval prompt should include:

- "Do you see green tape?"
- "Is there a large seller at the next half/whole-dollar level?"
- "Is price moving when buyers hit the ask?"

## Half-Dollar / Whole-Dollar Entry Preference

The transcript prefers entries near psychological support:

- whole dollars
- half dollars

Example:

- stock rejects near `$9.50`, pulls back toward `$9.00`, reclaims `$9.00`, and
  buyers return

Planning implication:

- approval screen should compute nearest half-dollar/whole-dollar support and
  resistance
- target can be next half-dollar/whole-dollar
- stop can be nearby pullback low, with the psychological level as context

## Starter / Add-To-Winners Rule

The source is explicit:

- do not enter pullback trades with full size initially
- take a starter on the early pullback turn
- add only when the trade starts working
- add on the first candle to make a new high or breakout confirmation
- never add to losers
- cut quickly if the tape stays red or pullback low breaks

Planning implication:

- v1 should probably simulate a single approved starter first
- later versions can support add approvals as separate events
- add events must have their own approval and should only be enabled when the
  open trade is green

## Quick-Loss Expectation

The source accepts small failed attempts on early pullback entries:

- starter can be cut for a small loss, often less than `10 cents/share`
- if the setup reappears, the trader may re-enter

Planning implication:

- v1 can allow re-entry after a small starter stop, but only while the same
  high-quality conditions remain true
- daily max loss and max attempts per symbol must prevent repeated chopping

## Daily Risk And Sizing Guardrails

The source adds process-level risk controls:

- start the day with reduced share size
- do not increase size until there is a profit cushion
- once daily goal is reached, do not give back more than half of the day's
  profit
- if too much profit is given back, reduce size or stop trading
- after a large red day, put restrictions back on until confidence recovers

Planning implication for virtual SAC trader:

- start each day in "starter size only" mode
- unlock larger simulated size only after a configured green cushion
- use a trailing daily profit giveback stop
- if daily P/L gives back too much, lock new entries

This should be adapted to the small-account SAC framework rather than copying
the transcript's large-share examples.

## Added Accuracy Principle

This source emphasizes improving accuracy first:

- trade fewer setups
- focus on first and second pullbacks
- avoid obscure names with no volume
- trade only obvious A-quality setups

Planning implication:

- manual gate should default to selective behavior
- dashboard should show "quality grade" and "why not" just as prominently as
  "approve"

## Added Open Questions

- Should v1 support early pullback starters, breakout confirmation entries, or
  both?
- Should MACD be a hard gate or just a confidence warning?
- If Level 2 is unavailable from Schwab, should the approval gate require the
  user to manually confirm no large seller?
- Should add-to-winner events be excluded from v1?
- What daily green cushion unlocks larger SAC simulated size?
- What profit giveback amount should lock the SAC day trader for the day?

## Source: Relative Volume Transcript

Source file reviewed:

`/Users/tonyday/.codex/attachments/1f2bbfeb-f3fb-499a-857c-e57be417647e/pasted-text.txt`

Working label:

`Relative Volume Stock Selection`

## Added Thesis

This source frames relative volume as the most important stock-selection
indicator for small-cap day trading. Relative volume measures today's volume
against what is normal for the same stock, instead of ranking by total market
volume.

The source claims almost all of the speaker's profit came from stocks with
relative volume of at least `5x`. This directly supports the existing SAC
scanner's `REL_VOLUME_MIN = 5.0` rule.

## Relative Volume Definition

Relative volume compares:

- today's volume
- average volume over a lookback window, such as `14`, `30`, or `50` days

The exact lookback depends on the platform. The planning implication is that
the scanner should be explicit about which lookback it uses and should show it
in the UI.

The source emphasizes:

- high total volume is not enough
- high relative volume means unusual attention
- unusual attention makes standard patterns more likely to resolve predictably

## Premarket Relative Volume Approximation

The source notes that some scanners do not populate relative volume premarket.
The speaker estimates it by comparing premarket volume against prior-day or
average historical volume.

Planning implication:

- v1 should calculate an estimated premarket relative volume from Schwab volume
  and daily average volume when live relative volume is not available
- UI should label it clearly as estimated if calculated this way

## Why Relative Volume Matters

The source argues that high relative volume means:

- something special is happening
- more traders are watching today than usual
- catalyst-driven attention is present
- VWAP, first-candle-new-high, dojis, topping tails, and breakouts become more
  respected because many traders are watching the same levels

This supports a key design principle:

- pattern confidence should be lower on low-relative-volume stocks, even if the
  chart appears technically clean

## Avoid Low Relative Volume Names

The source warns that trading familiar large caps or random low-relative-volume
stocks can put the trader "off in the weeds." In that condition, standard
technical patterns may not resolve predictably because not enough active
day-traders are watching the same setup.

Planning implication:

- SAC day trader should not approve entries on low-relative-volume stocks
- manual override should be possible only with a visible warning

## Catalyst Relationship

Relative volume is usually caused by breaking news, but the source does not
start by reading every headline. The workflow is:

1. find the top gappers / unusual volume names
2. then check the catalyst
3. then inspect the daily chart and intraday setup

This reinforces the scanner-first workflow.

The source also notes that continuation setups can have high relative volume
versus a monthly average, even if volume is lower than the previous day. The UI
should distinguish:

- relative volume vs historical average
- volume vs previous day

## Daily Chart Context

After identifying high relative volume, the source checks:

- daily chart
- upside resistance
- prior highs
- former momentum behavior
- float accuracy
- whether the stock is easy to borrow, which may invite more short sellers

Planning implication:

- day-trader approval should include daily resistance notes when available
- easy-to-borrow/short-availability data may not be available from Schwab; if
  absent, leave as manual note or future enhancement

## Obvious Levels

High relative volume creates shared attention. The transcript says obvious
levels become more predictable because many traders draw the same lines.

Examples:

- premarket high
- high of day
- VWAP
- first candle to make a new high
- recent breakout level

Planning implication:

- approval screen should surface obvious levels and label the proposed entry in
  relation to them

## Accuracy Versus Profit/Loss Ratio

The source explains a tradeoff:

- taking quick profit can increase accuracy but lower average winner size
- holding for larger targets can improve profit/loss ratio but reduce accuracy

The speaker prefers higher accuracy because it supports confidence, even if it
means taking smaller pieces of the move.

Planning implication:

- v1 should favor quick partial/target rules over swinging for the whole move
- manual approval should show both "quick target" and "extended target"
- simulator metrics should track accuracy and average winner/loss separately

## Red-To-Green And Continuation Notes

The source mentions:

- red-to-green moves can be valid when relative volume is high
- continuation names can work on day two, but they may not always have fresh
  stock-specific news
- former momentum stocks can move from trader memory, but lack of fresh news
  reduces predictability

Planning implication:

- v1 can include red-to-green as a watch pattern, but likely not the first
  implemented entry
- continuation without fresh news should be lower confidence than fresh-catalyst
  gap-and-go

## Added Open Questions

- Should relative volume below `5x` be a hard block for SAC day trades?
- What lookback should v1 use for average volume: `20`, `30`, or `50` days?
- Should premarket relative volume compare against full-day average volume,
  prior-day volume, or both?
- Should the approval gate require a named catalyst unless relative volume is
  extremely high?
- How should v1 handle former momentum stocks with no fresh news?
- Should quick-profit targets be preferred over larger hold-for-breakout
  targets in the default simulator settings?

## Source: VWAP Trading Strategies Transcript

Source file reviewed:

`/Users/tonyday/.codex/attachments/a81f2fb6-301c-4c98-ac53-6259fca9d82e/pasted-text.txt`

Working label:

`VWAP Regime / Reclaim / Trap Framework`

## Added Thesis

This source is centered on VWAP as a short-term sentiment and regime indicator.
VWAP incorporates both price and volume, so the source treats it as a better
intraday support/resistance reference than a simple moving average.

For the SAC day trader, this should not replace the gapper/relative-volume
filters. It should help qualify whether a long setup is supported by intraday
structure.

## VWAP Regime Rules

General long/short regime:

- above VWAP and holding: bullish / dip-buying context
- below VWAP and rejecting: bearish / weak context

For the planned SAC day trader, which is long-focused in v1:

- A-quality long approvals should prefer price above VWAP or reclaiming VWAP
- setups below VWAP should require extra caution, manual confirmation, or be
  blocked unless specifically treated as a reclaim setup

## VWAP Reclaim Long

The transcript describes a VWAP reclaim as:

- stock breaks below VWAP
- attempts to reclaim once or twice
- later reclaims VWAP, often around `10:30-11:00`
- forms higher lows
- buying volume improves or selling volume declines

Planning implication:

- v1 can track VWAP reclaim as a separate watch condition
- a reclaim should not be considered strong unless higher lows and improving
  volume are present

## VWAP As Pullback Support

For strong stocks:

- daily breakout plus strong intraday volume
- stock holds above VWAP
- pullbacks toward VWAP get bought
- higher lows form above or near VWAP

This reinforces earlier first-pullback rules:

- first pullback to VWAP/9 EMA is higher quality
- repeated successful VWAP holds add confidence
- a long setup should become weaker if VWAP breaks and cannot be reclaimed

## VWAP Breakdown Exit Warning

The source says if a long stock breaks below VWAP and cannot reclaim it, that is
a warning to cut or reduce the long.

Planning implication:

- VWAP loss can be a warning or exit trigger, but it should not be the only
  trigger because of VWAP stop traps
- combine VWAP loss with failed reclaim, lower highs, and increased selling
  volume before marking the long thesis broken

## VWAP Trap Warning

This source strongly warns that VWAP is popular enough to become an algo/market
maker trap, especially in small caps and low-float runners.

Trap pattern:

- stock breaks below VWAP
- appears weak
- volume dries up
- price stays close to VWAP instead of selling off hard
- higher lows form below VWAP
- VWAP reclaim later squeezes shorts

Planning implication:

- do not place simulated stops exactly at VWAP
- do not treat one wick below VWAP as automatic failure
- if price dips below VWAP but immediately reclaims, preserve or improve
  confidence if other long criteria are intact
- if price is below VWAP but forming higher lows near it on low volume, show a
  "possible reclaim trap" warning rather than a hard bearish label

## Time-Of-Day Note

The source says VWAP reclaim traps often appear around midday, roughly
`11:00-12:00`.

Planning implication:

- v1 gap-and-go entries should still prioritize morning momentum
- midday VWAP reclaim should be a watch/reversal context, not the first v1
  entry pattern unless intentionally added later

## Chart Timeframes

The source uses:

- 5-minute chart
- 2-minute chart for volatile names

Planning implication:

- our current research set now supports 1-minute, 2-minute, 5-minute, and
  optional 10-second views
- v1 should probably standardize on Schwab-supported 1-minute/5-minute candles
  first, with 2-minute derived locally if useful

## Added Open Questions

- Should VWAP loss be an immediate exit or a warning that requires confirmation?
- Should stops be placed below pullback low instead of directly at VWAP?
- Should v1 implement VWAP reclaim as a separate approval pattern, or only use
  it as context for pullbacks?
- Can Schwab provide enough intraday data to calculate reliable VWAP from
  premarket plus regular-session candles?
- Should midday reclaim setups be excluded from v1 to keep the system focused
  on the morning gap-and-go window?

## Source: Choppy Market Scalping Transcript

Source file reviewed:

`/Users/tonyday/.codex/attachments/59987e00-c13e-40c4-aa5b-9e109b267b10/pasted-text.txt`

Working label:

`Scalping / Choppy Market / Daily Key Level Framework`

## Added Thesis

This source focuses on fast scalping in choppy or difficult markets. Much of the
example material is short-side, so it is not a direct v1 SAC long strategy.
However, it adds useful filters for avoiding bad long entries and for taking
quick profits around known levels.

## Three Scalping Criteria

Only scalp stocks that meet all three:

1. Above-average trading volume on both the daily and intraday chart
2. Breakout or breakdown around a key daily level
3. Intraday price action confirms the daily breakout/rejection

Planning implication:

- SAC approval should not rely only on today's gap/change
- approval should include whether the stock is interacting with a meaningful
  daily level
- intraday action must confirm the daily context

## Chart And Indicator Setup

The source uses:

- daily chart
- 5-minute chart for slower consolidation and patience
- 2-minute or 1-minute chart for very volatile small caps
- Level 2 / tape for execution
- VWAP
- volume
- 13-period volume moving average

Planning implication:

- v1 can compute a short volume moving average to detect whether breakout or
  breakdown volume is actually above recent intraday bars
- for slower/choppier names, 5-minute confirmation may be more reliable than
  1-minute noise

## Key Level Rule

The source emphasizes daily key levels:

- prior resistance
- prior support
- prior close / red-to-green level
- premarket high
- daily breakout or rejection level

For long-biased SAC planning:

- do not approve a long directly under major daily resistance unless the plan is
  explicitly a breakout through that level
- if a stock has already gone parabolic into resistance, prefer taking profit
  or waiting for a clean reset rather than chasing

## Confirming Breakout Or Rejection

The source uses VWAP and volume to confirm whether the key-level move is real:

- breakout/breakdown should happen with meaningful volume
- stock holding above VWAP supports long continuation
- stock breaking below VWAP with volume warns that longs should be cautious or
  exit

Planning implication:

- manual gate should show daily key level, VWAP relation, and volume-vs-average
  together

## Choppy Market Timeframe Rule

The source says a lower timeframe can create too much noise during 30-minute
consolidations around a key level. In those cases, the 5-minute chart is better
for patience.

Planning implication:

- if price is chopping around a level, v1 should reduce confidence and prefer
  5-minute confirmation before approval
- the approval gate should warn when the last several candles overlap heavily
  or show repeated wicks around the same level

## Scalp Profit Behavior

The source repeatedly stresses:

- plan the trade around key levels
- take profits into daily support/resistance
- on bullish-news parabolic moves, a counter-move scalp should be quick
- do not be greedy

For SAC long planning:

- target should usually be the next obvious level, not an open-ended hold
- if price reaches a daily resistance level, take partial or exit
- do not approve new longs after a parabolic move into resistance without a
  clean pullback/reset

## Added Open Questions

- Should v1 calculate a 13-bar volume moving average for intraday confirmation?
- How should the scanner detect "chop" around a key level?
- Should daily resistance proximity reduce share size or block approval?
- Should the manual gate require a named target level before approval?
- Should v1 use 5-minute confirmation when price has been consolidating for
  more than 20-30 minutes?
