# scripts/test_drift.py
import asyncio
import os
from app.service.drift_funding_collector import DriftFundingCollector
from dotenv import load_dotenv
from anchorpy.provider import Wallet
from solana.rpc.async_api import AsyncClient
from driftpy.drift_client import DriftClient
from driftpy.accounts.get_accounts import get_perp_market_account
from driftpy.accounts.oracle import get_oracle_price_data_and_slot
from driftpy.constants import FUNDING_RATE_PRECISION, QUOTE_PRECISION
from driftpy.math.funding import calculate_long_short_funding_and_live_twaps

# Markets to test
MARKETS = {
    0: "SOL-PERP",
    1: "BTC-PERP",
    2: "ETH-PERP",
}

async def get_funding_for_market(drift_client, connection, market_id, market_name):
    """Get funding rate for a single market"""
    try:
        print(f"\nFetching {market_name}...")
        
        # Get market data (no subscription needed)
        market = await get_perp_market_account(drift_client.program, market_id)
        
        if market is None:
            print(f"Market {market_id} not found")
            return None
        
        # Get oracle price
        oracle_price = await get_oracle_price_data_and_slot(
            connection,
            market.amm.oracle,
            market.amm.oracle_source
        )
        
        # Calculate funding
        now = int(asyncio.get_event_loop().time())
        mark_price = market.amm.historical_oracle_data.last_oracle_price
        
        (mark_twap, oracle_twap, long_rate, short_rate) = \
            await calculate_long_short_funding_and_live_twaps(
                market, oracle_price.data, mark_price, now
            )
        
        precision = FUNDING_RATE_PRECISION
        
        result = {
            "market_name": market_name,
            "long_rate": long_rate / precision,
            "short_rate": short_rate / precision,
            "last_24h_avg": market.amm.last24h_avg_funding_rate / precision,
            "oracle_price": oracle_price.data.price / QUOTE_PRECISION,
            "mark_price": mark_price / QUOTE_PRECISION,
        }
        
        print(f"Long: {result['long_rate']:+.4f}%  Price: ${result['oracle_price']:,.2f}")
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        return None

async def main():

    # Load .env file
    load_dotenv()
    rpc_url = os.getenv("RPC_URL")

    connection = None
    drift_client = None

    if connection is None:
        print("Initializing Drift connection...")
        connection = AsyncClient(rpc_url)
        drift_client = DriftClient(
            connection,
            Wallet.dummy(),  # For rates collection read-only type is enought
                "mainnet"
           )
    
    try:
        results = []
        
        # Fetch each market
        for market_id, market_name in MARKETS.items():
            result = await get_funding_for_market(
                drift_client, 
                connection, 
                market_id, 
                market_name
            )
            if result:
                results.append(result)
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        
        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        for r in results:
            print(f"\n{r['market_name']:12} | "
                  f"Long: {r['long_rate']:+.4f}% | "
                  f"Short: {r['short_rate']:+.4f}% | "
                  f"24h Avg: {r['last_24h_avg']:+.4f}% | "
                  f"Price: ${r['oracle_price']:,.2f}")
        
        print("\n" + "=" * 70)
        print(f"Successfully fetched {len(results)}/{len(MARKETS)} markets")
        print("=" * 70)
        
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await connection.close()
    

if __name__ == "__main__":
    asyncio.run(main())