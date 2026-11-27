"""critical-path-risk: rank WBS tasks by the true blast radius of a slip.

The public surface is small on purpose. Most callers want ``Schedule`` to load a
program and ``analyze`` to get the full result bundle; everything else is
reachable through that bundle.
"""

from __future__ import annotations

from .analysis import AnalysisResult, Gate, analyze
from .config import Policy, load_policy
from .cpm import CpmResult, CycleError, compute_cpm
from .model import Schedule, ScheduleError, Task

__all__ = [
    "AnalysisResult",
    "CpmResult",
    "CycleError",
    "Gate",
    "Policy",
    "Schedule",
    "ScheduleError",
    "Task",
    "analyze",
    "compute_cpm",
    "load_policy",
]

__version__ = "0.3.0"
