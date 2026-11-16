from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
)

from . import DucoEntity

M = SensorStateClass.MEASUREMENT
# key in /nodeinfoget -> (name, unit, device class)
SENSORS = {
    "temp": ("Temperature", UnitOfTemperature.CELSIUS, SensorDeviceClass.TEMPERATURE),
    "co2": ("CO2", UnitOfRatio.PARTS_PER_MILLION, SensorDeviceClass.CO2),
    "rh": ("Humidity", PERCENTAGE, SensorDeviceClass.HUMIDITY),
    "trgt": ("Target flow", PERCENTAGE, None),
    "actl": ("Actual flow", PERCENTAGE, None),
    "cntdwn": ("Override remaining", UnitOfTime.SECONDS, SensorDeviceClass.DURATION),
}
# Every node reports temp/co2/rh, but nodes without that sensor report 0.
# ponytail: decided once at setup; a real sensor reading exactly 0 at startup gets skipped.
ZERO_MEANS_ABSENT = {"temp", "co2", "rh"}


def build(coordinator) -> list[SensorEntity]:
    entities: list[SensorEntity] = []
    for n, info in coordinator.data["nodes"].items():
        for key in SENSORS:
            if key not in info or (key in ZERO_MEANS_ABSENT and not info[key]):
                continue
            if key == "cntdwn" and info.get("state", "-") == "-":
                continue
            entities.append(DucoSensor(coordinator, n, key))
        if info["devtype"] == "BOX":
            entities.append(DucoPowerSensor(coordinator, n))
    return entities


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities(build(entry.runtime_data))


class DucoSensor(DucoEntity, SensorEntity):
    _attr_state_class = M

    def __init__(self, coordinator, node: int, key: str) -> None:
        name, unit, device_class = SENSORS[key]
        super().__init__(coordinator, node, key, name)
        self._key = key
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class

    @property
    def native_value(self):
        return self.info.get(self._key)


class DucoPowerSensor(DucoEntity, SensorEntity):
    _attr_state_class = M
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator, node: int) -> None:
        super().__init__(coordinator, node, "power", "Power")

    @property
    def native_value(self):
        return self.coordinator.data["box"].get("Performance", {}).get("PowerNow")
