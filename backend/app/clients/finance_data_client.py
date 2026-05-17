from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable

from backend.app.core.config import DATA_DIR


class MockFinanceDataClient:
    def __init__(self) -> None:
        with (DATA_DIR / "mock_market_data.json").open("r", encoding="utf-8") as f:
            self.market_data = json.load(f)

    def lookup_entities(self, entities: Iterable[str]) -> Dict[str, Any]:
        return {entity: self.market_data[entity] for entity in entities if entity in self.market_data}


class ExternalFinanceDataClient:
    """Optional external fact source adapter with safe failures.

    CoinGecko and Yahoo Finance are queried only when explicitly enabled by the
    pipeline. Network failures return partial evidence instead of failing the
    content workflow.
    """

    CRYPTO_IDS = {"Bitcoin": "bitcoin", "Ethereum": "ethereum"}
    YAHOO_SYMBOLS = {
        "Nvidia": "NVDA",
        "Tesla": "TSLA",
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "Gold": "GC=F",
        "Oil": "CL=F",
        "Treasury": "^TNX",
    }

    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds

    def lookup_entities(self, entities: Iterable[str]) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        for entity in entities:
            if entity in self.CRYPTO_IDS:
                data = self._coingecko_price(self.CRYPTO_IDS[entity])
                if data:
                    results[entity] = {"source": "coingecko", **data}
            elif entity in self.YAHOO_SYMBOLS:
                data = self._yahoo_quote(self.YAHOO_SYMBOLS[entity])
                if data:
                    results[entity] = {"source": "yahoo_finance", **data}
        return results

    def _coingecko_price(self, coin_id: str) -> Dict[str, Any]:
        query = urllib.parse.urlencode({"ids": coin_id, "vs_currencies": "usd", "include_24hr_change": "true"})
        url = f"https://api.coingecko.com/api/v3/simple/price?{query}"
        try:
            payload = _get_json(url, self.timeout_seconds)
            item = payload.get(coin_id, {})
            if not item:
                return {}
            return {"asset_id": coin_id, "usd": item.get("usd"), "usd_24h_change": item.get("usd_24h_change")}
        except Exception:
            return {}

    def _yahoo_quote(self, symbol: str) -> Dict[str, Any]:
        query = urllib.parse.urlencode({"symbols": symbol})
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?{query}"
        try:
            payload = _get_json(url, self.timeout_seconds)
            items = payload.get("quoteResponse", {}).get("result", [])
            if not items:
                return {}
            item = items[0]
            return {
                "symbol": symbol,
                "regularMarketPrice": item.get("regularMarketPrice"),
                "regularMarketChangePercent": item.get("regularMarketChangePercent"),
                "marketState": item.get("marketState"),
            }
        except Exception:
            return {}


class CompositeFinanceDataClient:
    def __init__(self, *clients: Any) -> None:
        self.clients = clients

    def lookup_entities(self, entities: Iterable[str]) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        for client in self.clients:
            for entity, value in client.lookup_entities(entities).items():
                if entity not in merged:
                    merged[entity] = value
                else:
                    existing = merged[entity]
                    if isinstance(existing, list):
                        existing.append(value)
                    else:
                        merged[entity] = [existing, value]
        return merged


def _get_json(url: str, timeout_seconds: int) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "x-financial-hotspot-agent/1.0"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))
