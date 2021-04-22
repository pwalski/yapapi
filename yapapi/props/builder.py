import abc
import enum
from datetime import datetime
from typing import List
from ..rest.market import Market, Subscription

from dataclasses import asdict

from . import Model
from .base import join_str_constraints, constraint_model_serialize


class DemandBuilder:
    """Builds a dictionary of properties and constraints from high-level models.

    The dictionary represents a Demand object, which is later matched by the new Golem's
    market implementation against Offers coming from providers to find those providers
    who can satisfy the requestor's demand.

    example usage:

    ```python
    >>> import yapapi
    >>> from yapapi import properties as yp
    >>> from yapapi.props.builder import DemandBuilder
    >>> from datetime import datetime, timezone
    >>> builder = DemandBuilder()
    >>> builder.add(yp.NodeInfo(name="a node", subnet_tag="testnet"))
    >>> builder.add(yp.Activity(expiration=datetime.now(timezone.utc)))
    >>> builder.__repr__
    >>> print(builder)
    {'properties':
        {'golem.node.id.name': 'a node',
         'golem.node.debug.subnet': 'testnet',
         'golem.srv.comp.expiration': 1601655628772},
     'constraints': []}
    ```
    """

    def __init__(self):
        self._properties: dict = {}
        self._constraints: List[str] = []
        pass

    def __repr__(self):
        return repr({"properties": self._properties, "constraints": self._constraints})

    @property
    def properties(self) -> dict:
        """List of properties for this demand."""
        return self._properties

    @property
    def constraints(self) -> str:
        """Constraints definition for this demand."""
        return join_str_constraints(self._constraints)

    def ensure(self, constraint: str):
        """Add a constraint to the demand definition."""
        self._constraints.append(constraint)

    def add(self, m: Model):
        """Add properties from the specified model to this demand definition."""
        kv = m.keys()
        base = asdict(m)

        for name in kv.names():
            prop_id = kv.__dict__[name]
            value = base[name]
            if value is None:
                continue
            if isinstance(value, datetime):
                value = int(value.timestamp() * 1000)
            if isinstance(value, enum.Enum):
                value = value.value
            assert isinstance(value, (str, int, list))
            self._properties[prop_id] = value

    async def subscribe(self, market: Market) -> Subscription:
        """Create a Demand on the market and subscribe to Offers that will match that Demand."""
        return await market.subscribe(self._properties, self.constraints)

    async def decorate(self, *decorators: 'DemandDecorator'):
        for decorator in decorators:
            await decorator.decorate_demand(self)


class DemandDecorator(abc.ABC):
    """An interface that specifies classes that can add properties and constraints through a DemandBuilder"""

    @abc.abstractmethod
    async def decorate_demand(self, demand: DemandBuilder):
        """Add appropriate properties and constraints to a Demand"""


class AutodecoratingModel(Model, DemandDecorator):
    async def decorate_demand(self, demand: DemandBuilder):
        demand.add(self)
        demand.ensure(join_str_constraints(constraint_model_serialize(self)))
