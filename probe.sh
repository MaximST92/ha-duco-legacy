#!/bin/sh
# Read-only dump of the legacy Duco (Communication Print) API. Sends no writes.
# Usage (HA Terminal add-on):  sh probe.sh <board-ip>  > duco-dump.txt
H=${1:?usage: sh probe.sh <board-ip>}
get() { echo "### GET /$1"; curl -s -m 20 "http://$H/$1"; echo; echo; }

# Endpoint names the board's own web UI calls (finds ones we don't know about).
echo "### endpoints referenced by web UI"
{ curl -s -m 10 "http://$H/"
  for js in $(curl -s -m 10 "http://$H/" | grep -oE 'src="[^"]+\.js"' | cut -d'"' -f2); do
    curl -s -m 10 "http://$H/${js#/}"
  done
} | grep -oE '[a-z_]+(get|set|info|list)[a-z_]*' | sort -u
echo

get board_info
get nodelist
get boxinfoget
for n in $(curl -s -m 10 "http://$H/nodelist" | grep -oE '[0-9]+'); do
  get "nodeinfoget?node=$n"
  get "nodeconfigget?node=$n"
done
