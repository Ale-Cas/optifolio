"""Implementation of Alpaca as DataProvider."""

import pandas as pd
from alpaca.data import Adjustment, BarSet, StockBarsRequest, StockHistoricalDataClient, TimeFrame

from optifolio.config import SETTINGS
from optifolio.market.base_data_provider import BaseDataProvider
from optifolio.market.enums import BarsField


class AlpacaMarketData(BaseDataProvider):
    """Class to get market data from Alpaca."""

    def __init__(self) -> None:
        super().__init__()
        api_key = SETTINGS.ALPACA_TRADING_API_KEY
        secret_key = SETTINGS.ALPACA_TRADING_API_SECRET
        assert isinstance(api_key, str)
        assert isinstance(secret_key, str)
        self.client = StockHistoricalDataClient(
            api_key=SETTINGS.ALPACA_TRADING_API_KEY,
            secret_key=SETTINGS.ALPACA_TRADING_API_SECRET,
        )

    def get_bars(
        self,
        tickers: tuple[str, ...],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """
        Get the daily bars dataframe from alpaca-py historical client.

        Parameters
        ----------
        `tickers`: tuple[str, ...]
            A tuple of str representing the tickers.
        `start_date`: pd.Timestamp
            A pd.Timestamp representing start date.
        `end_date`: pd.Timestamp
            A pd.Timestamp representing end date.

        Returns
        -------
        `bars`
            a pd.DataFrame with the bars for the tickers.
        """
        bars = self.client.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=sorted(tickers),
                start=start_date,
                end=end_date + pd.Timedelta(5, unit="hours"),  # needed to include last day
                adjustment=Adjustment.ALL,
                timeframe=TimeFrame.Day,
            )
        )
        assert isinstance(bars, BarSet)
        return bars.df

    def get_prices(
        self,
        tickers: tuple[str, ...],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp | None = None,
        bars_field: BarsField = BarsField.CLOSE,
    ) -> pd.DataFrame:
        """
        Get the daily bars dataframe from alpaca-py historical client.

        Parameters
        ----------
        `tickers`: tuple[str, ...]
            A tuple of str representing the tickers.
        `start_date`: pd.Timestamp
            A pd.Timestamp representing start date.
        `end_date`: pd.Timestamp
            A pd.Timestamp representing end date.

        Returns
        -------
        `bars`
            a pd.DataFrame with the bars for the tickers.
        """
        bars = self.get_bars(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
        )
        bars.reset_index(inplace=True)
        _index_name = "timestamp"
        prices = bars.pivot(index=_index_name, columns="symbol", values=bars_field)
        prices.index = pd.to_datetime(prices.index, format="%Y-%m-%d")
        return prices
