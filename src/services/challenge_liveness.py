import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Challenge:
    session_id: str
    actions: List[str]
    created_at: float
    completed: List[str] = field(default_factory=list)
    frames_analyzed: int = 0


@dataclass
class ChallengeResult:
    passed: bool
    completed: List[str]
    missing: List[str]
    confidence: float
    reason: str = ""


class ChallengeResponseLiveness:
    ACTIONS = ["blink", "turn_left", "turn_right", "smile", "nod"]
    SESSION_TTL = 60

    def __init__(self, actions_per_challenge: int = 2):
        self.sessions: Dict[str, Challenge] = {}
        self.n_actions = actions_per_challenge

    def new_challenge(self):
        actions = random.sample(self.ACTIONS, self.n_actions)
        s = Challenge(str(uuid.uuid4()), actions, time.time())
        self.sessions[s.session_id] = s
        return s

    def process_frame(self, sid, features):
        s = self.sessions.get(sid)
        if not s:
            return ChallengeResult(False, [], [], 0.0, "session_not_found")
        if time.time() - s.created_at > self.SESSION_TTL:
            del self.sessions[sid]
            return ChallengeResult(False, [], s.actions, 0.0, "session_expired")
        s.frames_analyzed += 1
        for a in s.actions:
            if a in s.completed:
                continue
            if a == "blink" and features.get("ear", 1.0) < 0.15:
                s.completed.append(a)
            elif a == "turn_left" and features.get("yaw", 0) < -20:
                s.completed.append(a)
            elif a == "turn_right" and features.get("yaw", 0) > 20:
                s.completed.append(a)
            elif a == "smile" and features.get("mouth_ratio", 0) > 0.35:
                s.completed.append(a)
            elif a == "nod":
                p = features.get("pitch_history", [])
                if len(p) >= 5 and max(p) - min(p) > 15:
                    s.completed.append(a)
        missing = [a for a in s.actions if a not in s.completed]
        return ChallengeResult(
            len(missing) == 0, s.completed, missing, len(s.completed) / len(s.actions)
        )

    def get_session(self, sid):
        return self.sessions.get(sid)
