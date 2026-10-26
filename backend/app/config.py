"""Central configuration. Everything scoped to the January 2026 challenge window."""
import os
from pathlib import Path

ELEXON_BASE = "https://data.elexon.co.uk/bmrs/api/v1"

# Target (delivery) period we care about: purchase decisions for Jan 2026 deliveries.
TARGET_START = "2026-01-01"
TARGET_END = "2026-01-31"

# Forecasts for 1 Jan are made on 31 Dec, so we pull publishes from a few days earlier.
PUBLISH_START = "2025-12-29T00:00:00Z"
PUBLISH_END = "2026-01-31T23:59:59Z"

# Drop forecasts issued more than this many hours before the target half-hour.
MAX_HORIZON_H = 72

# Day-ahead gate closure (local UK time, hour of day D-1). Configurable per request.
DEFAULT_CUTOFF_HOUR = 9
TIMEZONE = "Europe/London"

_ROOT = Path(__file__).resolve().parents[2]
_PACKAGED_DATA = Path(__file__).resolve().parent.parent / "data" / "jan2026.json"
_ROOT_DATA = _ROOT / "data" / "jan2026.json"
_configured_data = os.getenv("DATA_FILE")
DATA_FILE = Path(_configured_data) if _configured_data else (_ROOT_DATA if _ROOT_DATA.exists() else _PACKAGED_DATA)
STATIC_DIR = Path(os.getenv("STATIC_DIR", _ROOT / "frontend" / "dist"))
