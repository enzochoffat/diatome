#!/bin/bash
set -e

# Substitute env vars in config template if provided
if [[ -n "${CONFIG_TEMPLATE}" && -f "${CONFIG_TEMPLATE}" ]]; then
    envsubst < "${CONFIG_TEMPLATE}" > /tmp/config.json
    CONFIG_FILE="/tmp/config.json"
else
    CONFIG_FILE="${1:-configs_json/config_default.json}"
fi

# Run simulation
exec python -m src.scripts.run_simulation "${CONFIG_FILE}" "${@:2}"