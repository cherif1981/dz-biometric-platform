"""Decision gate: OCR success is NOT a validity signal."""
from enum import Enum


class ExtractionStatus(str, Enum):
    OK = "OK"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class AuthenticityStatus(str, Enum):
    VERIFIED = "VERIFIED"
    SUSPECT = "SUSPECT"
    UNKNOWN = "UNKNOWN"


class FinalDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


def decide_document(extraction, authenticity):
    if authenticity == AuthenticityStatus.SUSPECT:
        return FinalDecision.REJECT
    if authenticity == AuthenticityStatus.UNKNOWN:
        return FinalDecision.REVIEW
    if extraction == ExtractionStatus.OK:
        return FinalDecision.ACCEPT
    return FinalDecision.REVIEW
