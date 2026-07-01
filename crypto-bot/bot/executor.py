"""Execution layer: turn a quote into a fill. Paper (simulated) or Live (real swaps).

PaperExecutor needs no keys and touches no chain. LiveExecutor signs and submits a
real Solana transaction via Jupiter and your RPC — it can lose real money.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from .config import Config
from .prices import Quote

log = logging.getLogger("bot.executor")


@dataclass
class ExecResult:
    ok: bool
    side: str            # "BUY" | "SELL"
    base_amount: float
    sol_amount: float
    fill_price_sol: float
    tx_sig: str = ""
    error: str = ""


def _amounts_from_quote(side: str, quote: Quote, cfg: Config) -> tuple[float, float, float]:
    """Return (base_amount, sol_amount, fill_price_sol) for a quote in either direction."""
    p = cfg.pair
    if side == "BUY":   # SOL in -> base out
        sol_amount = quote.in_amount_atomic / 10 ** p.quote_decimals
        base_amount = quote.out_amount_atomic / 10 ** p.base_decimals
    else:               # base in -> SOL out
        base_amount = quote.in_amount_atomic / 10 ** p.base_decimals
        sol_amount = quote.out_amount_atomic / 10 ** p.quote_decimals
    fill_price = sol_amount / base_amount if base_amount > 0 else 0.0
    return base_amount, sol_amount, fill_price


class PaperExecutor:
    mode = "paper"

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def execute(self, side: str, quote: Quote) -> ExecResult:
        base_amount, sol_amount, fill_price = _amounts_from_quote(side, quote, self.cfg)
        # The Jupiter quote already reflects real price impact for this size, so the
        # simulated fill is realistic. We do not invent extra slippage here.
        return ExecResult(True, side, base_amount, sol_amount, fill_price, tx_sig="PAPER")


class LiveExecutor:
    mode = "live"

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self._keypair = None          # lazy
        self._client = None           # lazy solana RPC client
        self.session = requests.Session()

    # ----- lazy wallet / rpc setup (imports only needed for live) -----
    def _load_keypair(self):
        if self._keypair is not None:
            return self._keypair
        from solders.keypair import Keypair  # type: ignore

        s = self.cfg.secrets
        if s.keypair_path:
            import json
            arr = json.loads(open(s.keypair_path).read())
            self._keypair = Keypair.from_bytes(bytes(arr))
        elif s.private_key_base58:
            self._keypair = Keypair.from_base58_string(s.private_key_base58)
        else:
            raise RuntimeError(
                "Live mode needs a wallet: set SOLANA_KEYPAIR_PATH or SOLANA_PRIVATE_KEY_BASE58"
            )
        return self._keypair

    def _rpc(self):
        if self._client is None:
            from solana.rpc.api import Client  # type: ignore
            self._client = Client(self.cfg.secrets.rpc_url)
        return self._client

    def pubkey_str(self) -> str:
        return str(self._load_keypair().pubkey())

    def execute(self, side: str, quote: Quote) -> ExecResult:
        import base64

        from solders.transaction import VersionedTransaction  # type: ignore

        base_amount, sol_amount, fill_price = _amounts_from_quote(side, quote, self.cfg)
        kp = self._load_keypair()

        # 1) Ask Jupiter to build the swap transaction for this exact quote.
        swap_url = f"{self.cfg.secrets.jupiter_base_url.rstrip('/')}/swap"
        body = {
            "quoteResponse": quote.raw,
            "userPublicKey": str(kp.pubkey()),
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": "auto",
        }
        try:
            resp = self.session.post(swap_url, json=body, timeout=20)
            resp.raise_for_status()
            swap_tx_b64 = resp.json()["swapTransaction"]
        except Exception as e:  # noqa: BLE001
            return ExecResult(False, side, 0, 0, 0, error=f"swap build failed: {e}")

        # 2) Sign it locally with our key.
        try:
            raw = base64.b64decode(swap_tx_b64)
            unsigned = VersionedTransaction.from_bytes(raw)
            signed = VersionedTransaction(unsigned.message, [kp])
        except Exception as e:  # noqa: BLE001
            return ExecResult(False, side, 0, 0, 0, error=f"signing failed: {e}")

        # 3) Submit and confirm.
        try:
            from solana.rpc.types import TxOpts  # type: ignore
            client = self._rpc()
            sig = client.send_raw_transaction(
                bytes(signed), opts=TxOpts(skip_preflight=False, max_retries=3)
            ).value
            client.confirm_transaction(sig, commitment="confirmed")
        except Exception as e:  # noqa: BLE001
            return ExecResult(False, side, 0, 0, 0, error=f"submit/confirm failed: {e}")

        # NOTE: amounts here come from the quote, not from parsing the on-chain result.
        # Actual fills can differ slightly (within your slippage cap). Parsing the
        # confirmed tx for exact deltas is a worthwhile enhancement before scaling size.
        return ExecResult(True, side, base_amount, sol_amount, fill_price, tx_sig=str(sig))


def build_executor(cfg: Config, live: bool):
    return LiveExecutor(cfg) if live else PaperExecutor(cfg)
