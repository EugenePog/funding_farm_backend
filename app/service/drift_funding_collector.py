import asyncio
import os
from typing import List, Dict
import logging
from datetime import datetime
from dotenv import load_dotenv

from anchorpy.provider import Wallet
from solana.rpc.async_api import AsyncClient
from driftpy.drift_client import DriftClient
from driftpy.accounts.get_accounts import get_perp_market_account
from driftpy.accounts.oracle import get_oracle_price_data_and_slot
from driftpy.constants import FUNDING_RATE_PRECISION, QUOTE_PRECISION
from driftpy.math.funding import calculate_long_short_funding_and_live_twaps

from app.config import configuration

logger = logging.getLogger(__name__)

# Market IDs for different tokens on Drift
# https://docs.drift.trade/market-info
DRIFT_MARKETS = {
    0: "SOL-PERP",
}

DRIFT_MARKETS_ALL = {
    0: "SOL-PERP",
    1: "BTC-PERP",
    2: "ETH-PERP",
    3: "APT-PERP",
    4: "MATIC-PERP",
    5: "ARB-PERP",
    6: "DOGE-PERP",
    7: "BNB-PERP",
    8: "SUI-PERP",
    9: "1MPEPE-PERP",
    10: "OP-PERP",
    11: "RNDR-PERP",
    12: "HNT-PERP",
    13: "WIF-PERP",
    14: "JTO-PERP",
    15: "PYTH-PERP",
    16: "TIA-PERP",
    17: "JUP-PERP",
    18: "ONEMT-PERP",
    19: "SEI-PERP",
    20: "W-PERP",
}

class DriftFundingCollector:
    """Collects funding rates from Drift Protocol"""
    
    def __init__(self, rpc_url: str = None):
        # Load .env file
        load_dotenv()
        
        self.rpc_url = rpc_url or os.getenv("RPC_URL")
        self.connection = None
        self.drift_client = None
    
    async def initialize(self):
        """Initialize connection and Drift client"""
        if self.rpc_url is None:
            logger.error("RPC_URL is empty")
        
        if self.connection is None:
            logger.info("Initializing Drift connection...")
            self.connection = AsyncClient(self.rpc_url)
            self.drift_client = DriftClient(
                self.connection,
                Wallet.dummy(),  # For rates collection read-only type is enought
                "mainnet"
            )
            logger.info("Drift client initialized")
    
    async def close(self):
        """Close connections"""
        if self.connection:
            await self.connection.close()
        logger.info("Drift connection closed")
    
    async def get_funding_for_market(self, market_id: int, market_name: str) -> Dict:
        """Get funding rate for a single market"""
        try:
            # Get market account
            market = await get_perp_market_account(self.drift_client.program, market_id)
            
            if market is None:
                logger.warning(f"Market {market_name} (ID: {market_id}) not found")
                return None
            
            # Get oracle price
            oracle_price = await get_oracle_price_data_and_slot(
                self.connection,
                market.amm.oracle,
                market.amm.oracle_source
            )
            oracle_price_data = oracle_price.data
            
            # Current timestamp
            now = int(asyncio.get_event_loop().time())
            mark_price = market.amm.historical_oracle_data.last_oracle_price
            
            # Calculate funding rates
            (
                mark_twap,
                oracle_twap,
                long_rate,
                short_rate,
            ) = await calculate_long_short_funding_and_live_twaps(
                market, oracle_price_data, mark_price, now
            )
            
            precision = FUNDING_RATE_PRECISION
            
            # Build result
            result = {
                "market_id": market_id,
                "market_name": market_name,
                "timestamp": datetime.utcnow().isoformat(),
                "funding_rates": {
                    "long_rate": round(long_rate / precision, 6),
                    "short_rate": round(short_rate / precision, 6),
                    "last_funding_rate": round(market.amm.last_funding_rate / precision, 6),
                    "last_funding_rate_long": round(market.amm.last_funding_rate_long / precision, 6),
                    "last_funding_rate_short": round(market.amm.last_funding_rate_short / precision, 6),
                    "last_24h_avg": round(market.amm.last24h_avg_funding_rate / precision, 6),
                },
                "prices": {
                    "oracle_price": round(oracle_price_data.price / QUOTE_PRECISION, 2),
                    "mark_price": round(mark_price / QUOTE_PRECISION, 2),
                    "oracle_twap": round(oracle_twap / QUOTE_PRECISION, 2),
                    "mark_twap": round(mark_twap / QUOTE_PRECISION, 2),
                },
                "market_info": {
                    "base_asset_amount_long": market.base_asset_amount_long,
                    "base_asset_amount_short": market.base_asset_amount_short,
                    "open_interest": market.open_interest,
                }
            }
            
            logger.info(f"Collected funding for {market_name}: Long={result['funding_rates']['long_rate']}%")
            return result
            
        except Exception as e:
            logger.error(f"Error collecting {market_name} (ID: {market_id}): {e}")
            return {
                "market_id": market_id,
                "market_name": market_name,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def get_all_funding_rates(self) -> List[Dict]:
        """Get funding rates for all available markets"""
        logger.info(f"Collecting funding rates for {len(DRIFT_MARKETS)} markets...")
        
        await self.initialize()
        
        # Collect all markets concurrently for speed
        tasks = [
            self.get_funding_for_market(market_id, market_name)
            for market_id, market_name in DRIFT_MARKETS.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out None and exceptions
        valid_results = [
            r for r in results 
            if r is not None and not isinstance(r, Exception)
        ]
        
        logger.info(f"Collected {len(valid_results)} funding rates")
        return valid_results
    
    async def get_top_funding_opportunities(self, limit: int = 5) -> List[Dict]:
        """Get markets with highest absolute funding rates"""
        all_rates = await self.get_all_funding_rates()
        
        # Filter out errors
        valid_rates = [r for r in all_rates if "error" not in r]
        
        # Sort by absolute long funding rate (highest opportunities)
        sorted_rates = sorted(
            valid_rates,
            key=lambda x: abs(x["funding_rates"]["long_rate"]),
            reverse=True
        )
        
        return sorted_rates[:limit]

# Global instance
drift_collector = DriftFundingCollector()