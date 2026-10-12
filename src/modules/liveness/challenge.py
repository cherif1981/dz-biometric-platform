import secrets


CHALLENGES = ["blink", "turn_left", "turn_right", "smile", "nod"]


def new_challenge() -> dict:
    seq = [secrets.choice(CHALLENGES) for _ in range(2)]
    return {"challenge_id": secrets.token_hex(8), "sequence": seq}