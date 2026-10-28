"""ICAO 9303 MRZ validation."""
def _cv(c):
    if c == "<": return 0
    if "0" <= c <= "9": return ord(c) - ord("0")
    if "A" <= c <= "Z": return ord(c) - ord("A") + 10
    return -1


def mrz_check_digit(s):
    weights = [7, 3, 1]
    return sum(_cv(c) * weights[i % 3] for i, c in enumerate(s)) % 10


def validate_td1(line1, line2, line3):
    if len(line1) != 30 or len(line2) != 30 or len(line3) != 30:
        return {"format_ok": False, "reason": "Lines must be 30 chars"}
    doc = line1[5:14]
    doc_chk = line1[14]
    dob = line2[0:6]
    dob_chk = line2[6]
    exp = line2[8:14]
    exp_chk = line2[14]
    composite = (line1[5:30] + dob + str(mrz_check_digit(dob))
                 + exp + str(mrz_check_digit(exp)) + line2[18:29])
    comp_chk = line2[29]
    return {
        "format_ok": True,
        "doc_number_ok": mrz_check_digit(doc) == int(doc_chk),
        "dob_ok": mrz_check_digit(dob) == int(dob_chk),
        "expiry_ok": mrz_check_digit(exp) == int(exp_chk),
        "composite_ok": mrz_check_digit(composite) == int(comp_chk),
    }


def all_checks_pass(r):
    if not r.get("format_ok"):
        return False
    return all(r.get(k, False) for k in
               ["doc_number_ok", "dob_ok", "expiry_ok", "composite_ok"])
