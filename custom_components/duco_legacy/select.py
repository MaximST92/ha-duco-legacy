from __future__ import annotations

from homeassistant.components.select import SelectEntity

from . import DucoEntity

# MANx = timed override (ManualTimeout per node), CNTx = permanent override.
OPTIONS = ["AUTO", "MAN1", "MAN2", "MAN3", "CNT1", "CNT2", "CNT3"]


def build(coordinator) -> list[DucoStateSelect]:
    # Wall controls (UC) report state "-" and can't be set.
    return [
        DucoStateSelect(coordinator, n)
        for n, info in coordinator.data["nodes"].items()
        if info.get("state", "-") != "-"
    ]


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities(build(entry.runtime_data))


class DucoStateSelect(DucoEntity, SelectEntity):
    _attr_options = OPTIONS
    _attr_icon = "mdi:fan"

    def __init__(self, coordinator, node: int) -> None:
        super().__init__(coordinator, node, "state", "Ventilation state")

    @property
    def current_option(self) -> str | None:
        state = self.info["state"]
        return state if state in OPTIONS else None

    @property
    def extra_state_attributes(self) -> dict:
        # Shows states outside OPTIONS (e.g. ones set by a wall control).
        return {"raw_state": self.info["state"], "mode": self.info.get("mode")}

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.set_state(self.node, option)
        await self.coordinator.async_request_refresh()
