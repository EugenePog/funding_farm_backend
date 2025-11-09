from fastapi import APIRouter, HTTPException
from typing import List, Dict

from app.service.drift_funding_collector import drift_collector

router = APIRouter()

@router.get("/funding/all", response_model=List[Dict])
async def get_all_funding_rates():
    """Get funding rates for all Drift markets"""
    try:
        results = await drift_collector.get_all_funding_rates()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/funding/market/{market_id}")
async def get_market_funding(market_id: int):
    """Get funding rate for specific market"""
    from app.service.drift_funding_collector import DRIFT_MARKETS
    
    if market_id not in DRIFT_MARKETS:
        raise HTTPException(status_code=404, detail="Market not found")
    
    try:
        await drift_collector.initialize()
        result = await drift_collector.get_funding_for_market(
            market_id,
            DRIFT_MARKETS[market_id]
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/funding/top")
async def get_top_funding(limit: int = 5):
    """Get top funding rate opportunities"""
    try:
        results = await drift_collector.get_top_funding_opportunities(limit)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))