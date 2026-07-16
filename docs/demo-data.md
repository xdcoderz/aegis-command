# Judge demo data

The demo seed contains nine privileged banking sessions: four routine sessions,
two sessions that require step-up authentication, and three sessions that should
be blocked. The identities, event UUIDs and session IDs are stable across runs.
Event times are placed within the previous 24 hours so the command centre stays
useful on the day of a presentation.

The dataset deliberately covers the systems a bank's security team would care
about during a privileged-access review: core banking, the SWIFT gateway, the
payments API, IAM and the SIEM. Every record includes a named identity, role,
device, source address and protected resource. No placeholder telemetry is used.

## Preview without making changes

From the repository root:

```powershell
python scripts/seed_demo.py --dry-run --reset-local-db
```

To list only the session catalogue:

```powershell
python scripts/seed_demo.py --list
```

## Reset and seed

Start the local API on port 8000, then run:

```powershell
python scripts/seed_demo.py --reset-local-db
```

The reset is intentionally narrow. It can only open
`D:\code\Finspark\apps\api\finspark.db`, checks the SQLite signature and required
tables, and deletes child records before parent assessments. It never reads the
database URL from `.env`, so it cannot reset the Docker PostgreSQL database by
accident. Before deleting anything, it also confirms the loopback API is ready.
After the reset it checks that the API sees an empty assessment list; this catches
a local API that was started against a different database.

The utility restores the demo thresholds to 40 for step-up and 70 for block, then
posts all nine sessions through the public assessment endpoint. Re-running it
without `--reset-local-db` is safe: deterministic event UUIDs use the API's
idempotency path.

If local API authentication is enabled, provide an admin key without putting it
in shell history:

```powershell
$env:FINSPARK_DEMO_API_KEY = "your-local-admin-key"
python scripts/seed_demo.py --reset-local-db
```
