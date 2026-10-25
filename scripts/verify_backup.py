"""Verify a PostgreSQL backup restores correctly (staging only)."""
import argparse
import subprocess
import sys


def run(cmd):
    print("+", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        raise SystemExit(f"failed: {cmd[0]}")
    return r.stdout


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--restore-dsn", required=True)
    p.add_argument("--backup-file", required=True)
    p.add_argument("--expect-users-min", type=int, default=1)
    args = p.parse_args()

    run(["pg_restore", "--clean", "--if-exists",
         "-d", args.restore_dsn, args.backup_file])

    n = int(run(["psql", args.restore_dsn, "-tAc",
                 "SELECT count(*) FROM users;"]).strip())
    if n < args.expect_users_min:
        raise SystemExit(f"users={n} < {args.expect_users_min}")
    print(f"✅ users={n}")

    r = run(["psql", args.restore_dsn, "-tAc",
             "SELECT username FROM users WHERE username=\'testuser\';"]).strip()
    if r != "testuser":
        raise SystemExit("testuser missing")
    print("✅ testuser present")


if __name__ == "__main__":
    main()
