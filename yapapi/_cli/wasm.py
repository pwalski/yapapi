from rich.console import Console
from yapapi.runner import wasm

class Wasm:

    def pack(self, src: str):
        wasm.pack_into(output='out.ywasi', src=src)
        console = Console()
