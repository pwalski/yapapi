"""
Basic WASM Support.

"""
import abc
from typing import List, Optional

from dataclasses import dataclass
from yapapi.runner import Package
from enum import Enum
from pathlib import Path

from ..props.builder import DemandBuilder
from ..storage.gftp import GftpDriver


class WasmRuntime(Enum):
    WASI = "wasi"
    EMSC = "emscripten"


@dataclass
class Manifest:
    id: str
    name: str
    entry_points: List['EntryPoint']
    mount_points: List['MountPoint']

    def to_dict(self):
        output = {'id': self.id, 'name': self.name,
                  'entry-points': [entry_point.to_dict() for entry_point in self.entry_points],
                  'mount-points': [mount_point.to_dict() for mount_point in self.mount_points]}
        return output


@dataclass
class EntryPoint:
    id: str
    wasm_path: str
    js_path: Optional[str] = None

    def to_dict(self) -> dict:
        output = {
            'id': self.id,
            'wasm-path': self.wasm_path
        }
        if self.js_path:
            output['js-path'] = self.js_path
        return output


@dataclass
class MountPoint:
    path: str

    def to_dict(self) -> dict:
        return dict()

@dataclass
class RoMount(MountPoint):

    def to_dict(self) -> dict:
        return {'ro': self.path}

@dataclass
class RwMount(MountPoint):

    def to_dict(self) -> dict:
        return {'rw': self.path}


def pack_into(output: str, src: str, name: Optional[str] = None, ro: str = "/in", rw: str = "/out"):
    from zipfile import ZipFile, ZIP_LZMA
    import json
    src_path = Path(src)
    name = name or src_path.name
    wasm_bytes = src_path.read_bytes()
    manifest = Manifest(id=f"/yapapi/pack/{name}", name = name, entry_points=list(), mount_points=list())
    manifest.entry_points.append(EntryPoint(id="main", wasm_path="main.wasm"))
    manifest.mount_points.append(RoMount(ro))
    manifest.mount_points.append(RwMount(rw))
    with ZipFile(output, mode='w', compression=ZIP_LZMA) as zipf:
        zipf.writestr('manifest.json', json.dumps(manifest.to_dict()))
        zipf.writestr("main.wasm", wasm_bytes)


async def local(path: str, runtime: WasmRuntime = WasmRuntime.WASI, min_mem_gib: float = 0.5, min_storage_gib: float = 2.0) -> Package:
    return _LocalWasmFile()


class _LocalWasmFile(Package):

    async def resolve_url(self) -> str:
        pass

    async def decorate_demand(self, demand: DemandBuilder):
        pass

