#!/usr/bin/env python3
"""SRC001 SAREF adapter.

SAREF remains a screened candidate. No artifact rows are produced until the
ETSI TS 104 267 SHACL Shapes Repository is publicly available.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from pilot_common import AdapterResult, run_adapter


def collect() -> AdapterResult:
    return AdapterResult(
        source_id="SRC001",
        source_name="SAREF",
        status="skipped",
        warnings=[
            "SRC001 SAREF skipped: screened candidate only; ETSI TS 104 267 "
            "SHACL Shapes Repository is not yet publicly available."
        ],
        notes=[
            "No artifact candidates are invented for unpublished work items."
        ],
    )


def main() -> int:
    run_adapter(collect(), slug="saref")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
