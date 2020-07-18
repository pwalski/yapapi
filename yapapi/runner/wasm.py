"""
Basic WASM Support.

"""
import abc
from typing import Optional, Union, Collection, List

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
    entry_points: List["EntryPoint"]
    mount_points: List["MountPoint"]

    def to_dict(self):
        output = {
            "id": self.id,
            "name": self.name,
            "entry-points": [entry_point.to_dict() for entry_point in self.entry_points],
            "mount-points": [mount_point.to_dict() for mount_point in self.mount_points],
        }
        return output


@dataclass
class EntryPoint:
    id: str
    wasm_path: str
    js_path: Optional[str] = None

    def to_dict(self) -> dict:
        output = {"id": self.id, "wasm-path": self.wasm_path}
        if self.js_path:
            output["js-path"] = self.js_path
        return output


@dataclass
class MountPoint:
    path: str

    def to_dict(self) -> dict:
        return dict()


@dataclass
class RoMount(MountPoint):
    def to_dict(self) -> dict:
        return {"ro": self.path}


@dataclass
class RwMount(MountPoint):
    def to_dict(self) -> dict:
        return {"rw": self.path}


def pack_into(
    output: str,
    src: str,
    name: Optional[str] = None,
    ro: Union[str, Collection[str], None] = "/in",
    rw: Union[str, Collection[str], None] = "/out",
):
    """
    Helper for building custom images from wasm file.

    ## Params

    `output`
    :   path to output file. for WASM images sugested extension is `gwsi` for example `my-super-app.gwsi`

    `src`
    :   path to wasm file.

    'name'
    :   name for application. (optional)

    `ro`
    :   readonly container path. or `None` if there will be no read only mount points inside container.

    `rw`
    :   container path. or `None` if there will be no writable mount points inside container.


    """
    from zipfile import ZipFile, ZIP_LZMA
    import json

    src_path = Path(src)
    name = name or src_path.name
    wasm_bytes = src_path.read_bytes()
    manifest = Manifest(
        id=f"/yapapi/pack/{name}", name=name, entry_points=list(), mount_points=list()
    )
    manifest.entry_points.append(EntryPoint(id="main", wasm_path="main.wasm"))

    def paths(spec: Union[str, Collection[str], None]) -> Collection[str]:
        if spec is None:
            return ()
        if isinstance(spec, str):
            return (spec,)
        return spec

    for ro_path in paths(ro):
        manifest.mount_points.append(RoMount(ro_path))
    for rw_path in paths(rw):
        manifest.mount_points.append(RwMount(rw_path))

    with ZipFile(output, mode="w", compression=ZIP_LZMA) as zipf:
        zipf.writestr("manifest.json", json.dumps(manifest.to_dict()))
        zipf.writestr("main.wasm", wasm_bytes)


async def local(path: str, min_mem_gib: float = 0.5, min_storage_gib: float = 2.0,) -> Package:
    """
    Exposes WASM appliaction from local storage.

    `path`
    :   path to file. wasi binary (*.wasm) or full application image *.gwsi

    `min_mem_gib`
    :   minial memory to run given application.

    `min_storage_gib`
    :   minimal sotrage to run given application.

    **return**: Prepared application package.
    """

    return _LocalWasmFile()


class _LocalWasmFile(Package):
    async def resolve_url(self) -> str:
        pass

    async def decorate_demand(self, demand: DemandBuilder):
        pass


__all__ = ("pack_into", "local")
