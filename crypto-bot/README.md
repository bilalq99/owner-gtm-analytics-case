# PONKE/SOL Auto-Trading Bot

An automated trading bot for the PONKE/SOL pair on Solana, using [Jupiter](https://jup.ag)
for pricing and swaps. It runs a configurable strategy (momentum or DCA) with hard risk
limits, and can operate in **paper mode** (simulated, no money) or **live mode** (real swaps).

> [!CAUTION]
> **Read this before you do anything.**
>
> - **This bot cannot make you rich, and nobody can promise that it will.** PONKE is a
>   microcap Solana meme coin. Its price is driven by hype and sentiment, not fundamentals.
> - **You can lose 100% of the money you put in — quickly, and while you sleep.** An
>   automated bot removes the human circuit-breaker. A bug, an exploit, an RPC outage, or
>   a bad market move at 3am can all cost you real money.
> - **Live mode signs transactions with your private key.** Treat the wallet you connect as
>   burnable: fund it with only what you can afford to lose completely, never your main wallet.
> - **No strategy here has a proven edge.** Momentum/SMA/RSI on a meme coin is a reasonable
>   toy, not alpha. Backtest and paper trade for a long time before risking a cent.
> - **You are solely responsible** for how you use this, for tax/legal compliance in your
>   jurisdiction, and for verifying the token mint address is correct.
>
> The safest and most valuable thing you can do with this repo is run it in **paper mode**
> for weeks and see whether your strategy actually survives contact with the real market.

---

## What it does (each cycle)

```
read live PONKE/SOL price (Jupiter quote)
        │
        ▼
update rolling price history ──► strategy decides BUY / SELL / HOLD
        │                                  │
        ▼                                  ▼
mark portfolio & P&L               risk manager checks HARD caps
        │                                  │  (position, spend, daily-loss,
        ▼                                  │   cooldown, slippage, kill-switch)
persist state  ◄──── record fill ◄──── executor (paper sim OR live Jupiter swap)
```

## Safety features

| Control | What it does |
|---|---|
| **Paper mode (default)** | Real prices, fake money. No keys, no chain. |
| **Live confirmation gate** | Live mode requires typing `I ACCEPT THE RISK`. |
| `per_trade_sol` | Fixed, small size per buy. |
| `max_position_sol` | Never hold more than this much exposure. |
| `max_total_invested_sol` | Lifetime cap on SOL deployed into the token. |
| `max_daily_spend_sol` | Cap on buying per UTC day. |
| `daily_loss_limit_sol` | Circuit breaker — halts trading after this much daily loss. |
| `max_slippage_bps` | Aborts any swap whose quote is worse than this. |
| `min_seconds_between_trades` | Cooldown to prevent churn. |
| **Kill switch** | Create a file named `STOP` in the bot dir to halt trading immediately. |
| **Stop-loss / take-profit** | Auto-exit a position at configured % vs cost basis. |
| Secrets in env only | Keys are read from `.env` / env vars, never logged or committed. |

## Install

```bash
cd crypto-bot
python3 -m pip install -r requirements.txt        # paper mode
python3 -m pip install solders solana             # ADDITIONALLY, only if going live
```

## Configure

```bash
cp config.example.yaml config.yaml     # tune strategy + risk limits
cp .env.example .env                    # live only: wallet + RPC (leave blank for paper)
```

Open `config.yaml` and, at minimum, review every value under `risk:`.

## Run — paper mode (start here)

```bash
python3 run.py --config config.yaml --once     # a single cycle, then exit
python3 run.py --config config.yaml            # loop forever (Ctrl-C to stop)
```

State (portfolio, P&L, logs) is written to `state/`. Let it run for days/weeks and read
`state/bot.log` to judge whether the strategy is any good **before** risking real funds.

## Run — live mode (only after you understand the risk)

1. Verify the PONKE mint on a block explorer:
   https://explorer.solana.com/address/5z3EqYQo9HiCEs3R84RCDMu2n7anpDMxRhdK8PSWmrRC
2. Fund a **dedicated burner wallet** with a small amount of SOL.
3. Put the keypair path and a real RPC URL in `.env`.
4. Keep `per_trade_sol` / `max_*` limits small.

```bash
python3 run.py --config config.yaml --live
# then type:  I ACCEPT THE RISK
```

Create a file named `STOP` in this directory at any time to halt trading instantly.

## Project layout

```
crypto-bot/
├── run.py                 # CLI entrypoint + live confirmation gate
├── config.example.yaml    # strategy + risk configuration
├── .env.example           # wallet / RPC (live only)
├── bot/
│   ├── config.py          # load + validate config, load secrets from env
│   ├── prices.py          # Jupiter quote client + live price
│   ├── strategy.py        # momentum / DCA + indicators (pure, tested)
│   ├── portfolio.py       # balances, cost basis, realized/unrealized P&L
│   ├── risk.py            # hard caps + circuit breakers (tested)
│   ├── executor.py        # PaperExecutor (sim) / LiveExecutor (Jupiter swap)
│   └── engine.py          # the observe→decide→risk→execute→record loop
└── tests/                 # 25 tests: strategy, portfolio math, risk gates
```

## Tests

```bash
python3 -m pytest -q
```

## Known limitations / honest caveats

- **The strategy is not proven profitable.** SMA-cross + RSI is a starting point, nothing more.
- **Live fills use quoted amounts**, not on-chain-parsed deltas — fine for small size, but
  parse the confirmed transaction for exact fills before scaling up.
- **The public Jupiter/RPC endpoints are rate-limited.** Use paid providers for real trading.
- **No MEV protection, no partial-fill handling, no reorg handling.** This is a solid
  educational framework, not a battle-tested production trading system.
- **This is not financial advice.** It is example software.
