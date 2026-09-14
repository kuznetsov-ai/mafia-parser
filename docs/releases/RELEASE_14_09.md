# Release 14.09.2026

## CI: fix recurring base-image CVEs (perl-base CRITICAL)

### Bug

Weekly Trivy scan on Silver flagged 3 CRITICAL in `mafia-parser`: CVE-2026-13221, CVE-2026-42496, CVE-2026-8376 (all `perl-base` in the `python:3.11-slim` base image).

### Fix attempt 1 (partial): `docker build --pull`

`deploy.yml`'s build step never passed `--pull`, so it kept reusing whatever `python:3.11-slim` layer was already cached locally, even after Docker Hub published a newer one — this was the same root cause as the earlier openssl CRITICAL fix (2026-06-01), just recurring. Added `--pull` to the deploy script.

Re-scan after deploy: **still 3 CRITICAL, same perl-base version (5.40.1-6)**. `--pull` alone didn't help — Docker Hub's `python:3.11-slim` tag hadn't been rebuilt yet with the Debian security point-release, even though the actual Debian fix (`5.40.1-6+deb13u1`) already existed upstream.

### Fix attempt 2 (actual fix): `apt-get upgrade` in the Dockerfile

Added `RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*` right after `FROM`. This pulls Debian's own security-updates repo directly at build time instead of waiting for Docker Hub's less frequent base-image rebuild cadence.

Verified: `perl-base` now `5.40.1-6+deb13u1` inside the built image. Re-scan: **CRITICAL 0, HIGH 2** (unrelated leftovers). Prod health 200 OK.

Both fixes kept — `--pull` still matters for genuinely stale local caches, `apt-get upgrade` covers the gap when Docker Hub itself lags behind Debian security.
