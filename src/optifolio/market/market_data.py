"""Module to handle market data."""

from functools import lru_cache

import pandas as pd

from optifolio.config import SETTINGS
from optifolio.enums import BarsField, DataProvider
from optifolio.market.alpaca_market_data import AlpacaMarketData, Asset
from optifolio.market.base_data_provider import BaseDataProvider
from optifolio.market.yahoo_market_data import YahooMarketData
from optifolio.models.asset import AssetModel


class MarketData:
    """Class that implements market data connections."""

    def __init__(
        self,
        data_provider: DataProvider = DataProvider.ALPACA,
        trading_key: str | None = SETTINGS.ALPACA_TRADING_API_KEY,
        trading_secret: str | None = SETTINGS.ALPACA_TRADING_API_SECRET,
        broker_key: str | None = SETTINGS.ALPACA_BROKER_API_KEY,
        broker_secret: str | None = SETTINGS.ALPACA_BROKER_API_SECRET,
    ) -> None:
        self._trading_key = trading_key
        self._trading_secret = trading_secret
        self._broker_key = broker_key
        self._broker_secret = broker_secret
        self.__alpaca_client = AlpacaMarketData(
            trading_key=trading_key,
            trading_secret=trading_secret,
            broker_key=broker_key,
            broker_secret=broker_secret,
        )
        self.__yahoo_client = YahooMarketData()
        provider_mapping: dict[DataProvider, BaseDataProvider] = {
            DataProvider.ALPACA: self.__alpaca_client,
            DataProvider.YAHOO: self.__yahoo_client,
        }
        self.__provider_client = provider_mapping[data_provider]

    @lru_cache  # noqa: B019
    def load_prices(
        self,
        tickers: tuple[str, ...],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp | None = None,
        bars_field: BarsField = BarsField.CLOSE,
    ) -> pd.DataFrame:
        """
        Load the prices df from the data provider.

        Parameters
        ----------
        `tickers`: tuple[str, ...]
            A tuple of str representing the tickers.
        `start_date`: pd.Timestamp
            A pd.Timestamp representing start date.
        `end_date`: pd.Timestamp
            A pd.Timestamp representing end date.
        `bars_field`: BarsField
            A field in the OHLCV bars. Defaults to CLOSE.
        `excel_filename` str | None
            The path for an excel file with custom prices.
            Defaults to None and is required only if the DataProvider is EXCEL_FILE.

        Returns
        -------
        `prices`
            pd.DataFrame with market prices.
        """
        return self.__provider_client.get_prices(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            bars_field=bars_field,
        )

    def get_total_returns(
        self,
        tickers: tuple[str, ...],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp | None = None,
        required_pct_obs: float = 0.95,
    ) -> pd.DataFrame:
        """
        Return total return dataframe.

        Parameters
        ----------
        `tickers`: tuple[str, ...]
            A tuple of str representing the tickers.
        `start_date`: pd.Timestamp
            A pd.Timestamp representing start date.
        `end_date`: pd.Timestamp
            A pd.Timestamp representing end date.
        `required_pct_obs`: float
            Minimum treshold for non NaNs in each column.
            Columns with more NaNs(%)>required_pct_obs will be dropped.

        Returns
        -------
        `returns`
            pd.DataFrame with market linear returns.
        """
        returns = (
            self.load_prices(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
            )
            .pct_change()
            .iloc[1:, :]
        )
        # remove tickers that do not have enough observations
        return returns.dropna(axis=1, thresh=int(returns.shape[0] * required_pct_obs))

    @lru_cache  # noqa: B019
    def get_asset_from_ticker(self, ticker: str) -> AssetModel:
        """
        Return asset info from ticker.

        Parameters
        ----------
        `ticker`: str
            A str representing the ticker.

        Returns
        -------
        `asset`
            AssetModel data model.
        """
        apca_asset = self.__alpaca_client.get_alpaca_asset(ticker)
        yahoo_asset = self.__yahoo_client.get_yahoo_asset(ticker)
        return AssetModel(
            **apca_asset.dict(),
            **yahoo_asset.dict(),
        )

    @lru_cache  # noqa: B019
    def get_financials(self, ticker: str) -> pd.DataFrame:
        """
        Return asset info from ticker.

        Parameters
        ----------
        `ticker`: str
            A str representing the ticker.

        Returns
        -------
        `fin_df`
            pd.DataFrame of financials.
        """
        return self.__yahoo_client.get_financials(ticker)

    def get_tradable_tickers(self) -> tuple[str, ...]:
        """Get all tradable tickers from Alpaca."""
        return tuple(self.__alpaca_client.get_alpaca_tickers())

    def get_asset_by_name(self, name: str) -> Asset:
        """Get asset by name from Alpaca."""
        return self.__alpaca_client.get_asset_by_name(name)

    def get_total_number_of_shares(
        self,
        tickers: tuple[str, ...],
    ) -> pd.Series:
        """Get the number of shares for each ticket in tickets."""
        return self.__yahoo_client.get_multi_number_of_shares(tickers)

    def get_market_caps(
        self,
        tickers: tuple[str, ...],
        start_date: pd.Timestamp,
        end_date: pd.Timestamp | None = None,
    ) -> pd.DataFrame:
        """
        Return total return dataframe.

        Parameters
        ----------
        `tickers`: tuple[str, ...]
            A tuple of str representing the tickers.
        `start_date`: pd.Timestamp
            A pd.Timestamp representing start date.
        `end_date`: pd.Timestamp
            A pd.Timestamp representing end date.
        `required_pct_obs`: float
            Minimum treshold for non NaNs in each column.
            Columns with more NaNs(%)>required_pct_obs will be dropped.

        Returns
        -------
        `returns`
            pd.DataFrame with market linear returns.
        """
        return self.load_prices(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
        ) * self.get_total_number_of_shares(tickers)

    def get_top_market_caps(
        self,
        tickers: tuple[str, ...],
        top: int,
    ) -> pd.Series:
        """Get the tickers with the top market cap."""
        caps = self.get_market_caps(
            tickers=tickers,
            # only taking last week data for the market cap
            start_date=pd.Timestamp.today() - pd.Timedelta(days=5),
        )
        return caps.iloc[-1, :].sort_values(ascending=False)[:top]

    def get_top_market_cap_tickers(
        self,
        tickers: tuple[str, ...],
        top: int = 10,
    ) -> tuple[str, ...]:
        """Get the tickers with the top market cap."""
        return tuple(self.get_top_market_caps(tickers=tickers, top=top).index)
