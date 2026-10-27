# /// script
# requires-python = ">=3.11"
# ///
"""Wait for GitHub Pages to issue the TLS cert for zachadamseffect.com, then
enable "Enforce HTTPS" and verify.

Bounded: gives up after MAX_WAIT_S and reports honestly where it got to.
Stdout stays quiet while polling (notifications pick up the exit).
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = "zackees/zachadamseffect.com"
DOMAIN = "zachadamseffect.com"
POLL_S = 45
MAX_WAIT_S = 3 * 60 * 60  # 3 hours


def gh_json(args: list[str]) -> dict:
    out = subprocess.run(["gh", "api", *args], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip()[:200])
    if not out.stdout.strip():
        return {}
    parsed = json.loads(out.stdout)
    return parsed if isinstance(parsed, dict) else {}


def gh_write(args: list[str], payload: dict) -> tuple[bool, str]:
    out = subprocess.run(
        ["gh", "api", *args, "-X", "PUT", "--input", "-"],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return out.returncode == 0, out.stderr.strip()[:300]


def https_status() -> int:
    req = urllib.request.Request(f"https://{DOMAIN}/", method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def main() -> int:
    deadline = time.monotonic() + MAX_WAIT_S
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            pages = gh_json([f"repos/{REPO}/pages"]) or {}
        except Exception as exc:  # transient API trouble: keep waiting
            print(f"[{attempt}] api error: {exc}", file=sys.stderr, flush=True)
            time.sleep(POLL_S)
            continue

        cert = (pages.get("https_certificate") or {}).get("state", "none")
        code = https_status()
        print(f"[{attempt}] cert={cert} https={code}", flush=True)

        if code == 200:
            if pages.get("https_enforced"):
                print(f"DONE: HTTPS live and already enforced (cert={cert})")
                return 0
            ok, err = gh_write([f"repos/{REPO}/pages"], {"https_enforced": True})
            time.sleep(4)
            after = gh_json([f"repos/{REPO}/pages"]) or {}
            enforced = bool(after.get("https_enforced"))
            print(
                f"HTTPS live (cert={cert}); enforce request ok={ok} {err}; "
                f"https_enforced now={enforced}"
            )
            return 0 if enforced else 2

        time.sleep(POLL_S)

    print(f"TIMEOUT after {MAX_WAIT_S // 60} min: cert never issued; Enforce HTTPS NOT set")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
