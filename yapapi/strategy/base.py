"""Implementation of strategies for choosing offers from market."""

import abc
from copy import deepcopy
from datetime import datetime, timezone
import logging
from typing import Dict, Optional

from dataclasses import dataclass
from typing_extensions import Final

from yapapi.props import Activity
from yapapi.props.builder import DemandBuilder, DemandDecorator
from yapapi import rest


SCORE_NEUTRAL: Final[float] = 0.0
SCORE_REJECTED: Final[float] = -1.0
SCORE_TRUSTED: Final[float] = 100.0

# the properties and their default ranges here are part of the general protocol used by all
# provider and requestor agents on the market to agree on certain parameters of their
# offers, demands and, finally the resultant agreements

PROP_DEBIT_NOTE_INTERVAL_SEC: Final[str] = "golem.com.scheme.payu.debit-note.interval-sec?"
PROP_PAYMENT_TIMEOUT_SEC: Final[str] = "golem.com.scheme.payu.payment-timeout-sec?"
PROP_DEBIT_NOTE_ACCEPTANCE_TIMEOUT: Final[str] = "golem.com.payment.debit-notes.accept-timeout?"

MID_AGREEMENT_PAYMENTS_PROPS = [PROP_DEBIT_NOTE_INTERVAL_SEC, PROP_PAYMENT_TIMEOUT_SEC]


@dataclass
class PropValueRange:
    min: Optional[float] = None
    max: Optional[float] = None

    def __contains__(self, item: float) -> bool:
        return (self.min is None or item >= self.min) and (self.max is None or item <= self.max)

    def clamp(self, item: float):
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"Cannot clamp to a range in which min={self.min} > max={self.max}.")
        if self.min is not None and item < self.min:
            return self.min
        if self.max is not None and item > self.max:
            return self.max
        return item

    def __str__(self):
        return f"({self.min}, {self.max})"


DEFAULT_DEBIT_NOTE_ACCEPTANCE_TIMEOUT_SEC: Final[int] = 30
DEFAULT_DEBIT_NOTE_INTERVAL_SEC: Final[int] = 60
DEFAULT_PAYMENT_TIMEOUT_SEC: Final[int] = 18000
MIN_EXPIRATION_FOR_MID_AGREEMENT_PAYMENTS: Final[int] = DEFAULT_PAYMENT_TIMEOUT_SEC

DEBIT_NOTE_INTERVAL_GRACE_PERIOD: Final[int] = 30


DEFAULT_PROPERTY_VALUE_RANGES: Dict[str, PropValueRange] = {
    PROP_DEBIT_NOTE_INTERVAL_SEC: PropValueRange(DEFAULT_DEBIT_NOTE_INTERVAL_SEC, None),
    PROP_PAYMENT_TIMEOUT_SEC: PropValueRange(DEFAULT_PAYMENT_TIMEOUT_SEC, None),
    PROP_DEBIT_NOTE_ACCEPTANCE_TIMEOUT: PropValueRange(
        DEFAULT_DEBIT_NOTE_ACCEPTANCE_TIMEOUT_SEC, None
    ),
}

logger = logging.getLogger(__name__)


class BaseMarketStrategy(DemandDecorator, abc.ABC):
    """Base market strategy interface."""

    @abc.abstractmethod
    async def score_offer(self, offer: rest.market.OfferProposal) -> float:
        """Score `offer`. Better offers should get higher scores."""
        raise NotImplementedError()

    @abc.abstractmethod
    async def respond_to_provider_offer(
        self,
        our_demand: DemandBuilder,
        provider_offer: rest.market.OfferProposal,
    ) -> DemandBuilder:
        """Respond with a modified `DemandBuilder` object to an offer coming from a provider."""
        raise NotImplementedError()


class MarketStrategy(BaseMarketStrategy, abc.ABC):
    """Abstract market strategy."""

    acceptable_prop_value_range_overrides: Dict[str, PropValueRange]
    __acceptable_prop_value_ranges: Dict[str, PropValueRange]

    @property
    def acceptable_prop_value_ranges(self) -> Dict[str, PropValueRange]:
        if not hasattr(self, "__acceptable_prop_value_ranges"):
            # initialize with the overrides
            self.__acceptable_prop_value_ranges = getattr(
                self, "acceptable_prop_value_range_overrides", {}
            ).copy()

            # and set default property value ranges if they were not set in the market strategy.
            for key, value in DEFAULT_PROPERTY_VALUE_RANGES.items():
                self.__acceptable_prop_value_ranges.setdefault(key, value)

        return self.__acceptable_prop_value_ranges

    async def respond_to_provider_offer(
        self,
        our_demand: DemandBuilder,
        provider_offer: rest.market.OfferProposal,
    ) -> DemandBuilder:
        # Create a new DemandBuilder with a response to a provider offer.
        updated_demand = deepcopy(our_demand)

        # only enable mid-agreement-payments when we need a longer expiration
        # and when the provider supports it
        activity = Activity.from_properties(our_demand.properties)

        assert activity.expiration  # type/sanity check, normally always set by the Engine

        expiration_secs = round((activity.expiration - datetime.now(timezone.utc)).total_seconds())
        trigger_mid_agreement_payments = expiration_secs >= float(
            MIN_EXPIRATION_FOR_MID_AGREEMENT_PAYMENTS
        )

        mid_agreement_payments_enabled = (
            PROP_DEBIT_NOTE_INTERVAL_SEC in provider_offer.props and trigger_mid_agreement_payments
        )

        if mid_agreement_payments_enabled:
            logger.debug(
                "Enabling mid-agreement payments mechanism "
                "as the expiration set to %ss (more than %ss).",
                expiration_secs,
                MIN_EXPIRATION_FOR_MID_AGREEMENT_PAYMENTS,
            )
        elif trigger_mid_agreement_payments:
            logger.debug(
                "Expiration of %ss (more than our minimum for MAP: %ss) while negotiating "
                "with a provider unaware of mid-agreeement-payments.",
                expiration_secs,
                MIN_EXPIRATION_FOR_MID_AGREEMENT_PAYMENTS,
            )

        # Update response by either accepting proposed values or by proposing ours
        # only set mid-agreement payments values if we're agreeing to them
        for prop_key, acceptable_range in self.acceptable_prop_value_ranges.items():
            prop_value = provider_offer.props.get(prop_key)
            if prop_value is not None and (
                mid_agreement_payments_enabled or prop_key not in MID_AGREEMENT_PAYMENTS_PROPS
            ):

                if prop_value not in acceptable_range:
                    our_value = acceptable_range.clamp(prop_value)
                    logger.debug(
                        f"Negotiated property %s = %s outside of our accepted range: %s. "
                        f"Proposing our own value instead: %s",
                        prop_key,
                        prop_value,
                        acceptable_range,
                        our_value,
                    )
                    prop_value = our_value

                updated_demand.properties[prop_key] = prop_value
        return updated_demand

    async def decorate_demand(self, demand: DemandBuilder) -> None:
        """Optionally add relevant constraints to a Demand."""