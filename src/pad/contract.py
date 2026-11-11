from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol

import numpy as np


class PADState(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    LOADED = "LOADED"
    HEURISTIC = "HEURISTIC"
    VERIFIED = "VERIFIED"


class Decision(str, Enum):
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


@dataclass(frozen=True)
class PADInput:
    image_bgr: np.ndarray
    request_id: str
    source: str


@dataclass(frozen=True)
class PADResult:
    decision: Decision
    state: PADState
    liveness: Optional[float]
    threshold: Optional[float]
    reasons: tuple[str, ...]
    request_id: str
    source: str
    model_sha_prefix: Optional[str]
    preprocess_version: str


class PADPort(Protocol):
    @property
    def state(self) -> PADState: ...

    def evaluate(self, inp: PADInput) -> PADResult: ...
