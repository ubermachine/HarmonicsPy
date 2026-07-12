import os
import pytest
import pandas as pd
from app.data_manager_v2 import get_yahoo_data, get_bulk_yahoo_data_v2

def test_pyharmonics_loads_from_lake():
    """Verify that get_yahoo_data and get_bulk_yahoo_data_v2 load from central data lake."""
    # We load TCS.NS
    cd = get_yahoo_data("TCS.NS", interval="1d", candles=100)
    assert cd.df is not None
    assert len(cd.df) > 0
    assert list(cd.df.columns) == ["Open", "High", "Low", "Close", "Volume"]  # DatetimeIndex is index
    
    # We load bulk
    data_dict = get_bulk_yahoo_data_v2(["TCS.NS", "RELIANCE.NS"], interval="1d")
    assert "TCS.NS" in data_dict
    assert "RELIANCE.NS" in data_dict
    assert len(data_dict["TCS.NS"]) > 0
    assert len(data_dict["RELIANCE.NS"]) > 0
