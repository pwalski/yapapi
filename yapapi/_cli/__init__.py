from .market import Demand
from .payment import Allocation, Invoices
from .wasm import Wasm


class Cli:
    def __init__(self):
        self.allocation = Allocation
        self.invoice = Invoices
        self.demand = Demand
        self.wasm = Wasm


def _main():
    import fire  # type: ignore

    fire.Fire(Cli, name="yapapi")
