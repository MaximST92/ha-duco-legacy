"""Duco ventilation via the legacy Communication Print local API (/nodeinfoget etc.)."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

DOMAIN = "duco_legacy"
PLATFORMS = [Platform.SELECT, Platform.SENSOR]
ERRORS = (aiohttp.ClientError, TimeoutError, ValueError, KeyError)
_LOGGER = logging.getLogger(__name__)


class DucoApi:
    """Plain HTTP, no auth. The board is slow, so callers go one request at a time."""

    def __init__(self, hass: HomeAssistant, host: str) -> None:
        self._session = async_get_clientsession(hass)
        self._base = f"http://{host}"

    async def _text(self, path: str) -> str:
        async with self._session.get(
            f"{self._base}/{path}", timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def get(self, path: str) -> dict:
        # Board doesn't send a JSON content type, so parse the text ourselves.
        return json.loads(await self._text(path))

    async def set_state(self, node: int, state: str) -> None:
        try:
            text = await self._text(f"nodesetoperstate?node={node}&value={state}")
        except ERRORS as err:
            raise HomeAssistantError(f"Duco board not responding: {err}") from err
        if "FAIL" in text.upper():
            raise HomeAssistantError(f"Duco refused {state} on node {node}: {text}")


class DucoCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: DucoApi, nodes: list[int]) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=30)
        )
        self.api = api
        # ponytail: node list read once; reload the integration after pairing new Duco nodes.
        self.nodes = nodes

    async def _async_update_data(self) -> dict:
        try:
            return {
                "nodes": {n: await self.api.get(f"nodeinfoget?node={n}") for n in self.nodes},
                "box": await self.api.get("boxinfoget"),
            }
        except ERRORS as err:
            raise UpdateFailed(f"Duco board not responding: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = DucoApi(hass, entry.data[CONF_HOST])
    try:
        nodes = (await api.get("nodelist"))["nodelist"]
    except ERRORS as err:
        raise ConfigEntryNotReady(f"Duco board not responding: {err}") from err
    coordinator = DucoCoordinator(hass, entry, api, nodes)
    await coordinator.async_config_entry_first_refresh()
    register_devices(hass, entry, coordinator.data["nodes"])
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def register_devices(hass: HomeAssistant, entry: ConfigEntry, nodes: dict[int, dict]) -> None:
    """One HA device per Duco node (box, valve, wall control), linked to its parent node.

    Parents first: via_device_id needs the parent's registry id.
    """
    reg = dr.async_get(hass)
    ids: dict[int, str] = {}

    def add(n: int) -> str:
        if n not in ids:
            info = nodes[n]
            p = info["prnt"]
            ids[n] = reg.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, info["serialnb"])},
                name=info["location"] or ("DucoBox" if info["devtype"] == "BOX" else f"Duco {info['devtype']} {n}"),
                manufacturer="Duco",
                model=info["devtype"],
                sw_version=info["swversion"],
                serial_number=info["serialnb"],
                via_device_id=add(p) if p in nodes and p != n else None,
            ).id
        return ids[n]

    for n in nodes:
        add(n)


class DucoEntity(CoordinatorEntity[DucoCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DucoCoordinator, node: int, key: str, name: str) -> None:
        super().__init__(coordinator)
        self.node = node
        serial = coordinator.data["nodes"][node]["serialnb"]
        self._attr_name = name
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, serial)})

    @property
    def info(self) -> dict:
        return self.coordinator.data["nodes"][self.node]
