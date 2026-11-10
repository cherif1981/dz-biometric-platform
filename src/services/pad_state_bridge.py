"""Semantic bridge: service-level PADState ⇄ canonical model-level PADState."""

def to_canonical(service_state):
    from anti_spoof.decision import PADState as _CanonicalPADState
    from src.services.antispoofing_service import PADState as _ServicePADState
    mapping = {
        _ServicePADState.VERIFIED:  _CanonicalPADState.VERIFIED,
        _ServicePADState.HEURISTIC: _CanonicalPADState.HEURISTIC,
        _ServicePADState.LOADED:    _CanonicalPADState.UNAVAILABLE,
    }
    return mapping[service_state]
