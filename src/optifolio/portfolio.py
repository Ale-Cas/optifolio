"""Portfolio module."""
import pandas as pd
from typeguard import typechecked

from optifolio.market import MarketData
from optifolio.models import AssetModel
from optifolio.optimization.objectives import ObjectiveValue


class Portfolio:
    """Portfolio class."""

    def __init__(
        self,
        weights: pd.Series,
        objective_values: list[ObjectiveValue],
        market_data: MarketData | None = None,
        created_at: pd.Timestamp | None = None,
    ) -> None:
        self.weights = weights
        self.objective_values = objective_values
        self.market_data = market_data
        self.created_at = created_at

    def __repr__(self) -> str:
        """Object representation."""
        objectives_dict = {o.name.value: o.value for o in self.objective_values}
        return f"{self.__class__.__name__}(weights={self.get_non_zero_weights().to_dict()}, objective_values={objectives_dict})"

    def get_non_zero_weights(self, round_to_decimal: int | None = 5) -> pd.Series:
        """Non zero weights."""
        non_zero = self.weights[self.weights != 0]
        return non_zero.round(round_to_decimal) if round_to_decimal else non_zero

    def get_tickers(self, only_non_zero: bool = True) -> tuple[str, ...]:
        """Get the tickers in portfolio."""
        weights = self.get_non_zero_weights() if only_non_zero else self.weights
        return tuple(weights.keys())

    @typechecked
    def set_market_data(self, market_data: MarketData) -> None:
        """Set the market data."""
        self.market_data = market_data

    def get_assets_in_portfolio(self, only_non_zero: bool = True) -> list[AssetModel]:
        """Return the assets in the portfolio."""
        assert isinstance(
            self.market_data, MarketData
        ), "You must set the market data to get the assets info."
        weights = self.get_non_zero_weights() if only_non_zero else self.weights
        return [
            AssetModel(
                **self.market_data.get_asset_from_ticker(ticker=ticker).dict(
                    exclude={"weight_in_ptf"}
                ),
                weight_in_ptf=weight,
            )
            for ticker, weight in weights.items()
        ]

    def get_holdings_df(self) -> pd.DataFrame:
        """Return holdings info df."""
        return (
            pd.DataFrame(
                [asset.dict() for asset in self.get_assets_in_portfolio()],
            )
            .set_index("symbol")
            .sort_values(by="weight_in_ptf", ascending=False)
        )

    def get_history(
        self,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp | None = None,
    ) -> pd.Series:
        """Get the portfolio wealth history."""
        assert isinstance(
            self.market_data, MarketData
        ), "You must set the market data to get the assets info."
        rets = self.market_data.get_total_returns(
            tickers=self.get_tickers(),
            start_date=start_date,
            end_date=end_date,
        )
        return 1 + (rets * self.get_non_zero_weights()).sum(axis=1, skipna=True).cumsum()
