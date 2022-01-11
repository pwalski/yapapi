from unittest.mock import Mock, PropertyMock, patch
from contextlib import contextmanager

from tests.factories.rest.market import OfferProposalFactory


def mock_offer(provider_id=1, coeffs=(0.001, 0.002, 0.1)):
    """Yield an offer issued by a given provider for given coeffs"""
    kwargs = {}
    kwargs["proposal__proposal__issuer_id"] = provider_id
    kwargs["proposal__proposal__properties__linear_coeffs"] = list(coeffs)
    return OfferProposalFactory(**kwargs)


def mock_event(cls, provider_id):
    event = cls(Mock(), Mock())
    event.agreement.cached_details.raw_details.offer.provider_id = provider_id
    return event