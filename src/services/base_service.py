
from typing import Dict


class BaseVerificationService:
    """كل خدمة تُرجع درجات خام (scores) فقط.

    قرار القبول/الرفض مسؤولية DecisionEngine وحدها.
    """

    modality: str = "unknown"

    def verify(self, payload: Dict) -> Dict[str, float]:
        raise NotImplementedError
