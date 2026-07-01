"""Jupiter quote client: live prices and swap quotes for the trading pair."""
from __future__ import annotations

import time
from dataclasses import dataclass

import requests

from .config import Config


@dataclass
class Quote:
    """A Jupiter swap quote, plus the raw response needed to build a swap tx."""
    in_mint: str
    out_mint: str
    in_amount_atomic: int
    out_amount_atomic: int
    price_impact_pct: float
    slippage_bps: int
    raw: dict


class PriceError(RuntimeError):
    pass


class JupiterClient:
    def __init__(self, cfg: Config, session: requests.Session | None = None) -> None:
        self.cfg = cfg
        self.base_url = cfg.secrets.jupiter_base_url.rstrip("/")
        self.session = session or requests.Session()

    def _get(self, path: str, params: dict) -> dict:
        url = f"{self.base_url}{path}"
        last_err: Exception | None = None
        for attempt in range(4):
            try:
                resp = self.session.get(url, params=params, timeout=15)
                if resp.status_code == 429:
                    raise PriceError("rate limited (429)")
                resp.raise_for_status()
                return resp.json()
            except Exception as e:  # noqa: BLE001 - retry on any transient failure
                last_err = e
                time.sleep(2 ** attempt)
        raise PriceError(f"GET {path} failed after retries: {last_err}")

    def get_quote(self, in_mint: str, out_mint: str, in_amount_atomic: int, slippage_bps: int) -> Quote:
        data = self._get(
            "/quote",
            {
                "inputMint": in_mint,
                "outputMint": out_mint,
                "amount": int(in_amount_atomic),
                "slippageBps": int(slippage_bps),
                "swapMode": "ExactIn",
            },
        )
        if "outAmount" not in data:
            raise PriceError(f"no route for {in_mint}->{out_mint}: {data}")
        return Quote(
            in_mint=in_mint,
            out_mint=out_mint,
            in_amount_atomic=int(data["inAmount"]),
            out_amount_atomic=int(data["outAmount"]),
            price_impact_pct=float(data.get("priceImpactPct", 0.0)),
            slippage_bps=slippage_bps,
            raw=data,
        )

    def get_price_in_sol(self) -> float:
        """Current price of 1 base token (e.g. PONKE) expressed in SOL.

        Derived from a real quote of a fixed SOL notional, which reflects actual
        executable liquidity rather than a mid-market oracle number.
        """
        p = self.cfg.pair
        probe_lamports = int(self.cfg.engine.price_probe_sol * 10 ** p.quote_decimals)
        q = self.get_quote(p.quote_mint, p.base_mint, probe_lamports, self.cfg.risk.max_slippage_bps)
        sol_in = q.in_amount_atomic / 10 ** p.quote_decimals
        base_out = q.out_amount_atomic / 10 ** p.base_decimals
        if base_out <= 0:
            raise PriceError("quote returned zero output")
        return sol_in / base_out
