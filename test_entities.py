"""Entity selection and device tree against the real API dump.
Run: uv run --python 3.14 --with homeassistant==2026.11.1 python test_entities.py"""
import json
import re
from pathlib import Path
from types import SimpleNamespace

import custom_components.duco_legacy as duco
from custom_components.duco_legacy import select, sensor

dump = Path(__file__).with_name("api-dump").joinpath("legacy.txt").read_text()
nodes = {
    int(m[1]): json.loads(m[2])
    for m in re.finditer(r"### GET /nodeinfoget\?node=(\d+)\n(.+)", dump)
}
box = json.loads(re.search(r"### GET /boxinfoget\n(.+)", dump)[1])
c = SimpleNamespace(data={"nodes": nodes, "box": box})

ids = {e.unique_id.split("_", 1)[1] + f"@{e.node}" for e in sensor.build(c) + select.build(c)}
sel = {e.node for e in select.build(c)}

assert sel == set(range(1, 10)), sel  # UC wall control (10) not settable
assert {"temp@2", "co2@2", "trgt@2", "actl@2", "cntdwn@2", "state@2"} <= ids
assert "temp@1" not in ids and "co2@1" not in ids  # box reports 0 = no sensor
assert {"power@1", "trgt@1", "actl@1"} <= ids
assert "temp@10" in ids and "co2@10" not in ids and "cntdwn@10" not in ids
assert not any(i.startswith("rh@") for i in ids)  # nobody reports humidity here

for e in select.build(c):
    assert e.current_option == "AUTO"
# Device tree: fake registry records each device; ids are the serials.
devs = {}
def get_or_create(**kw):
    serial = next(iter(kw["identifiers"]))[1]
    assert kw["via_device_id"] is None or kw["via_device_id"] in devs, "parent must exist first"
    devs[serial] = kw
    return SimpleNamespace(id=serial)
duco.dr.async_get = lambda hass: SimpleNamespace(async_get_or_create=get_or_create)
duco.register_devices(None, SimpleNamespace(entry_id="e"), nodes)
by_node = {n: devs[i["serialnb"]] for n, i in nodes.items()}
assert by_node[2]["name"] == "Bedroom2" and by_node[2]["via_device_id"] == nodes[1]["serialnb"]
assert by_node[1]["name"] == "DucoBox" and by_node[1]["via_device_id"] is None
assert by_node[10]["via_device_id"] == nodes[9]["serialnb"]  # wall control hangs off the bathroom valve
print(f"ok: {len(ids)} entities")
for i in sorted(ids, key=lambda s: (int(s.split("@")[1]), s)):
    print(" ", i)
