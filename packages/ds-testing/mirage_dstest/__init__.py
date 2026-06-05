"""Public surface for the mirage_dstest deterministic-simulation testing harness.

This package marker re-exports only the pure, mirage-free framework classes so
that consumers can write::

    from mirage_dstest import (
        ModelFS,
        DSStateMachine,
        VirtualClock,
        SeededRandom,
        ChaosResource,
        FaultSchedule,
        HistoryRecorder,
        ScopedConsistencyChecker,
        ResourceFactory,
        ResourceSUT,
        contract_suite,
        CONTRACT_CASES,
    )

Importing this package must be import-light and side-effect-free, and must NOT
pull ``mirage`` into ``sys.modules``. Every name re-exported below comes from a
framework module that references mirage types only via ``typing.Protocol`` or
``if TYPE_CHECKING:`` guards, so the package is collectable even when mirage is
not installed. The runtime mirage seam lives exclusively in
``mirage_dstest.adapters`` and is deliberately NOT re-exported here.
"""

from mirage_dstest.chaos import ChaosResource, FaultSchedule
from mirage_dstest.clock import VirtualClock
from mirage_dstest.contract import (
    CONTRACT_CASES,
    ResourceFactory,
    ResourceSUT,
    contract_suite,
)
from mirage_dstest.history import HistoryRecorder, ScopedConsistencyChecker
from mirage_dstest.modelfs import ModelFS
from mirage_dstest.rng import SeededRandom
from mirage_dstest.statemachine import DSStateMachine

__all__: list[str] = [
    "ModelFS",
    "DSStateMachine",
    "VirtualClock",
    "SeededRandom",
    "ChaosResource",
    "FaultSchedule",
    "HistoryRecorder",
    "ScopedConsistencyChecker",
    "ResourceFactory",
    "ResourceSUT",
    "contract_suite",
    "CONTRACT_CASES",
]
