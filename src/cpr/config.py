"""Why this file exists.

Every number a program office might argue about (the slip size we stress tasks
with, the overstatement ratio that trips the gate, the re-routing alarm window)
is a policy decision, not a fact about the algorithm. Keeping them here, loaded
from ``policy.toml``, means the gate can be retuned without editing analysis
code, and a reviewer can read the whole decision surface in one short file.

The dataclass defaults are the single source of truth in code; they are kept in
step with ``policy.toml`` by ``tests/test_config.py``, which parses the shipped
file and asserts it matches field for field. If the two drift, a test fails
rather than the two silently disagreeing.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = REPO_ROOT / "policy.toml"


class PolicyError(ValueError):
    """Raised when a policy file is present but malformed or out of range."""


@dataclass(frozen=True)
class Policy:
    """The full analysis policy. Defaults mirror the shipped ``policy.toml``."""

    slip_days: int = 5
    review_blind_spot_days: int = 7
    max_float_overstatement_ratio: float = 2.0
    rerouting_alarm_days: int = 7
    top_n: int = 12

    def __post_init__(self) -> None:
        if self.slip_days <= 0:
            raise PolicyError("slip_days must be a positive number of working days")
        if self.review_blind_spot_days < 0:
            raise PolicyError("review_blind_spot_days cannot be negative")
        if self.max_float_overstatement_ratio < 1.0:
            raise PolicyError(
                "max_float_overstatement_ratio below 1.0 would flag every chain, "
                "since a sum can never be less than its own shared minimum"
            )
        if self.rerouting_alarm_days < 0:
            raise PolicyError("rerouting_alarm_days cannot be negative")
        if self.top_n <= 0:
            raise PolicyError("top_n must be positive")


def _flatten(raw: dict) -> dict:
    """Collapse the sectioned TOML into the flat field namespace of Policy.

    The TOML is grouped into [horizon], [gate] and [report] for readability, but
    the field names are unique across sections, so the dataclass stays flat.
    """
    flat: dict = {}
    for key, value in raw.items():
        if isinstance(value, dict):
            # A [section] table: merge its keys into the flat namespace.
            flat.update(value)
        else:
            # A bare top-level scalar, so a minimal override file need not
            # reproduce the section headers.
            flat[key] = value
    return flat


def load_policy(path: str | Path | None = None) -> Policy:
    """Load a Policy from a TOML file, falling back to the dataclass defaults.

    An explicit path that does not exist is an error (the user asked for a file
    we cannot read). A ``None`` path uses the shipped ``policy.toml`` if present,
    and the hard-coded defaults otherwise, so the library works with no files at
    all.
    """
    if path is not None:
        p = Path(path)
        if not p.exists():
            raise PolicyError(f"policy file not found: {p}")
        return _from_file(p)
    if DEFAULT_POLICY_PATH.exists():
        return _from_file(DEFAULT_POLICY_PATH)
    return Policy()


def _from_file(p: Path) -> Policy:
    try:
        raw = tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise PolicyError(f"could not parse {p}: {exc}") from exc
    flat = _flatten(raw)
    known = {f.name for f in fields(Policy)}
    unknown = set(flat) - known
    if unknown:
        raise PolicyError(f"unknown policy keys in {p}: {sorted(unknown)}")
    return Policy(**{k: v for k, v in flat.items() if k in known})
