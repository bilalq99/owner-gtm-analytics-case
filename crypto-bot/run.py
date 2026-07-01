#!/usr/bin/env python3
"""CLI entrypoint for the PONKE/SOL bot.

Examples:
  python run.py --config config.yaml                 # PAPER mode (safe default)
  python run.py --config config.yaml --once          # one paper cycle, then exit
  python run.py --config config.yaml --live          # LIVE mode (real money; requires confirmation)
"""
from __future__ import annotations

import argparse
import sys

from bot.config import load_config
from bot.engine import Engine
from bot.logging_setup import setup_logging

CONFIRM_PHRASE = "I ACCEPT THE RISK"


def confirm_live(cfg) -> bool:
    print("\n" + "=" * 70)
    print("  LIVE TRADING MODE — THIS SPENDS REAL MONEY")
    print("=" * 70)
    print(f"  Token:        {cfg.pair.base_symbol}  ({cfg.pair.base_mint})")
    print(f"  Per trade:    {cfg.risk.per_trade_sol} SOL")
    print(f"  Max position: {cfg.risk.max_position_sol} SOL")
    print(f"  Lifetime cap: {cfg.risk.max_total_invested_sol} SOL")
    print(f"  RPC:          {cfg.secrets.rpc_url}")
    print("  You can lose 100% of deployed funds. Meme coins are extremely volatile.")
    print("  Verify the token mint on a block explorer before continuing.")
    print("=" * 70)
    if not (cfg.secrets.keypair_path or cfg.secrets.private_key_base58):
        print("  ERROR: no wallet configured (SOLANA_KEYPAIR_PATH / SOLANA_PRIVATE_KEY_BASE58).")
        return False
    try:
        ans = input(f'\n  Type exactly "{CONFIRM_PHRASE}" to proceed (anything else aborts): ')
    except EOFError:
        return False
    return ans.strip() == CONFIRM_PHRASE


def main() -> int:
    ap = argparse.ArgumentParser(description="PONKE/SOL auto-trading bot")
    ap.add_argument("--config", default="config.yaml", help="path to config YAML")
    ap.add_argument("--live", action="store_true", help="enable LIVE trading (real money)")
    ap.add_argument("--once", action="store_true", help="run a single cycle and exit")
    ap.add_argument("--yes", action="store_true",
                    help="skip the interactive live confirmation (for non-interactive live runs — be careful)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    setup_logging(cfg.engine.state_dir)

    if args.live and not args.yes:
        if not confirm_live(cfg):
            print("Aborted. (No confirmation.) Staying safe.")
            return 1
    elif args.live and args.yes:
        if not (cfg.secrets.keypair_path or cfg.secrets.private_key_base58):
            print("ERROR: --live --yes but no wallet configured.")
            return 1

    engine = Engine(cfg, live=args.live)
    if args.once:
        engine.run_once()
    else:
        try:
            engine.run_forever()
        except KeyboardInterrupt:
            print("\nStopped by user.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
