import abc
import logging
import os
from typing import Optional

import aiohttp
from dataclasses import dataclass

from yapapi.payload import Payload

logger = logging.getLogger(__name__)


class PackageException(Exception):
    """Exception raised on any problems related to the package repository."""


@dataclass  # type: ignore  # mypy issue #5374
class Package(Payload):
    """Description of a task package (e.g. a VM image) deployed on the provider nodes."""

    @abc.abstractmethod
    async def resolve_url(self) -> str:
        """Return package URL."""


async def check_package_url(image_url: str, image_hash: str) -> str:
    async with aiohttp.ClientSession() as client:
        resp = await client.head(image_url, allow_redirects=True)
        if resp.status != 200:
            resp.raise_for_status()

        return f"hash:sha3:{image_hash}:{image_url}"


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.2f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


async def resolve_package_url(
    repo_url: str,
    image_tag: Optional[str] = None,
    image_hash: Optional[str] = None,
    image_use_https: bool = False,
) -> str:
    async with aiohttp.ClientSession() as client:
        is_dev = os.getenv("GOLEM_DEV_MODE", False)

        if image_tag is None and image_hash is None:
            raise PackageException("Neither image tag nor image hash specified")

        if image_tag and image_hash:
            raise PackageException("Both image tag and image hash specified")

        if image_tag:
            url_params = f"tag={image_tag}"
        else:
            url_params = f"hash={image_hash}"

        if is_dev:
            # if dev, skip usage statistics, pass dev option for statistics
            url_params += "&dev=true"
        else:
            # resolved by yapapi, so count as used tag (for usage statistics)
            url_params += "&count=true"

        query_url = f"{repo_url}/v1/image/info?{url_params}"
        logger.debug(f"Querying registry portal: {query_url}")
        resp = await client.get(query_url)
        if resp.status != 200:
            try:
                text = await resp.text()
            except Exception as ex:
                logger.error(f"Failed to get body of response: {ex}")
                text = "N/A"

            logger.error(f"Failed to resolve image URL: {resp.status} {text}")
            raise Exception(f"Failed to resolve image URL: {resp.status} {text}")
        json_resp = await resp.json()
        if image_use_https:
            image_url = json_resp["https"]
        else:
            image_url = json_resp["http"]
        image_hash = json_resp["sha3"]
        image_size = json_resp["size"]
        logger.debug(f"Resolved image size: {sizeof_fmt(image_size)}")
        logger.debug(f"Resolved image hash: {image_hash}")
        logger.debug(f"Resolved image url: {image_url}")
        # TODO: check if image_arch is ok
        # image_arch = image_info["arch"]

        return f"hash:sha3:{image_hash}:{image_url}"
