# Iteration 21 D04 business runtime helper

This helper is for the real WoniuNote systemd/Lima VM. It does not use the
synthetic Python backend, the deployment-runtime fixture, injected login
state, test challenge routes, or SVG text extraction. It never starts a Lima
VM automatically. Host evidence goes under
`/tmp/woniunote-iter21-evidence/deploy-business-runtime/` with mode `0700`;
captured files contain service metadata, hashes, schema metadata, and safe API
summaries, never configuration contents, API bodies, credentials, or tokens.

The target instance is fixed to
`woniunote-iter21-systemd-20261024t0028z`. The helper expects the already
prepared guest paths:

- original application: `/var/lib/woniunote-iter21-business/original-v2`
- candidates: `/var/lib/woniunote-iter21-business/candidate-2` and
  `candidate-3` and `candidate-4`
- persistent application data and mode-0600 runtime config:
  `/var/lib/woniunote-iter21-data`
- fresh deployment-manager state: `/var/lib/woniunote-iter21-business/release-state`
- root-only MySQL client file:
  `/root/.config/woniunote-iter21/mysql-client.cnf`
- real Node 22.13.0: `/opt/woniunote-iter21-node/bin`

## Current state and evidence boundary

The original-v2 UI is prepared and was captured unauthenticated at
`/tmp/woniunote-iter21-evidence/deploy-business-runtime/20261023T182220Z-13279-original-ui-and-schema/`.
At that capture, the dedicated original backend and Nginx units were active,
the frontend returned HTTP 200, the category API returned 70 categories, and
both formal test-hook routes returned 404 with hook-enabling environment
variables injected. The backend SHA is
`1935a00eda4f4b61e2728637fbe5d170c5ab78b1e3889185367a7a3eeb32021f`; the
frontend index SHA is
`7c4cfa9910ec4206b589e8b95666d5e74b0ea14427b60a71add8b1595e6cf0f5`.
Root separately confirmed that the SSH tunnel reaches the page with HTTP 200.
Browser trust of the local self-signed certificate, visual CAPTCHA entry,
account creation, and saved-draft/close evidence remain manual.

The original schema was rebuilt from pinned original-v2 SQL commit
`fefab0570c370bebd796df9c683343805d850d18` only after the recorded preflight
showed the sole D04 schema, all 10 business tables empty, and all three seed
tables exact. The resulting schema baseline is original-v2 with
`math_training_wrong_answers.user_answer INT NOT NULL`. The preflight
evidence is a snapshot from before the browser rehearsal; it does not prove
current row counts after account creation. Never run `prepare-original-ui`
again or reset this schema. After UI writes begin, use only a data-bearing
backup and reviewed incremental migration.

The temporary DDL snapshot reported during preparation was made before the
reset and is not the business-data backup required for the first maintenance
transition. The upcoming full backup must include current table data and be
verified against exact per-table row counts and runtime database identity.

Candidate source directories remain `PREPARED_NOT_FROZEN`, have no final
candidate commits, and predate the latest frontend refresh-concurrency fix.
Do not stage or deploy them. Candidate staging requires a clean, frozen Git
repository and a full expected commit SHA.

The first `original-v2 → candidate-2` transition is a one-time maintenance
procedure. It has no all-PASS compatibility record and no managed rollback
pointer to the known-incompatible v2 application. Before maintenance, the
owner must save/export the draft in the browser, close the old editor, and
record the saved-data identity. Then verify the running listener is the exact
original-v2 binary by SHA and systemd PID, stop only that owned backend, take
and verify the full data backup, and apply only the reviewed migration state.
Stopping the original backend also stops its dependent dedicated HTTPS unit;
MySQL, Redis and persistent uploads remain available. Install candidate 2
into an empty release-manager state directory only after those checks pass.
After candidate 2 starts, the owner must use a fresh browser context, log in
again, and read the saved data back. The old v2 application remains an
emergency degraded artifact; it is not the normal rollback target after new
writes.

Only after candidate 2 is current should the owner run compatibility checks
for both candidate 2→3 and candidate 3→2 against the actual frozen candidates,
live schema, session behavior, old/new frontend behavior, and API contracts.
The helper never creates compatibility records. The deployment manager will
reject absent, mismatched, unverified, or hash-invalid records. The operator
must create each record only after root reviews the attached evidence.

## Commands

Read-only inspection and the safe category API probe do not require a handoff:

```bash
bash scripts/tests/iter21-business-runtime/run.sh inspect
bash scripts/tests/iter21-business-runtime/run.sh capture before-maintenance
bash scripts/tests/iter21-business-runtime/run.sh api
```

The pre-UI read-only `audit-original-schema` was already captured in the
evidence directory described above. It checked exact business-table counts,
the selected schema's uniqueness under the D04 prefix, the `user_answer` type,
and SHA-256 checks of original seed rows. Do not rerun it after UI writes
begin: its zero-row result is specifically a reset-precondition gate, not a
business backup check.

The one-time original-v2 preparation was already completed; this command is
retained only to document its invocation. Do not execute it again: the schema
reset path is permanently closed once browser data is created. It required
both explicit mutation gates:

```bash
WONIUNOTE_ITER21_D04_HANDOFF=approved \
  bash scripts/tests/iter21-business-runtime/run.sh prepare-original-ui --confirm-d04-mutation
```

At that run, the helper verified the pinned backend SHA and original built
frontend dist, checked database/Redis and service ownership, created root-only
runtime configuration plus a self-signed localhost certificate, restored
original SQL after the recorded empty-schema checks, and started dedicated
systemd units. Backend HTTP is bound to guest loopback `127.0.0.1:5173`;
dedicated HTTPS is bound to guest loopback `127.0.0.1:8443`. It performed
category API and formal test-hook negative probes without printing response
bodies, credentials, or tokens. It stopped at an unauthenticated page; no
login state was injected.

The current development task already authorizes this isolated rehearsal.
Mutation flags are technical ownership guards, not a request for repeated
approval. The browser handoff remains necessary for the certificate warning,
new credentials, and CAPTCHA under the computer-use tool's rules. Once that
handoff is complete, root reviews the saved/closed evidence and continues the
authorized isolated maintenance steps; production changes remain out of scope.

The tunnel command emitted by the helper is:

```bash
ssh -F /Users/yunjinqi/.lima/woniunote-iter21-systemd-20261024t0028z/ssh.config \
  -N -L 127.0.0.1:18443:127.0.0.1:8443 \
  -o HostName=127.0.0.1 -o ExitOnForwardFailure=yes -o BatchMode=yes \
  lima-woniunote-iter21-systemd-20261024t0028z
```

Open `https://localhost:18443/` in a fresh browser context. The local
self-signed certificate warning must be handled in the browser. The reviewer
must read the CAPTCHA visually and enter it in the page, create an
email-shaped test username through the UI, log in, create and save/export a
draft, record its server-side identity, and close the editor. Root captures
those browser observations and the saved-data identity. After account
creation, never run the schema reset path again. Do not stop original-v2,
migrate, stage candidates, or switch services until root has reviewed the
saved/closed evidence from the completed browser handoff.

## Original-v2 upload-layout correction

The original-v2 runtime config must use `app.document_root` at
`/var/lib/woniunote-iter21-data/uploads` and `app.upload_path` at
`/var/lib/woniunote-iter21-data/uploads/uploads`. Its UEditor handler resolves
`../uploads` before `./uploads` from the dedicated service working directory,
so the run-owned `original-v2-runtime/uploads` symlink must point to the
persistent `/var/lib/woniunote-iter21-data/uploads` directory. The higher
priority `/var/lib/woniunote-iter21-business/uploads` path must be absent or
already resolve to that same persistent target.

The already-prepared UI predates this correction. Apply it only after root has
captured and reviewed the saved/closed browser evidence above. The repair
command refuses an active backend, verifies the pinned binary, dedicated
systemd unit, config identity and port ownership, then changes only the two
`app` path fields and the required symlink. Any real directory or mismatched
symlink at either UEditor path fails closed; existing upload files are never
moved, copied, deleted, or replaced. It does not reset the schema, access
credentials, or stop/start/reload services.

```bash
WONIUNOTE_ITER21_D04_HANDOFF=approved \
  bash scripts/tests/iter21-business-runtime/run.sh stop-original \
  1935a00eda4f4b61e2728637fbe5d170c5ab78b1e3889185367a7a3eeb32021f \
  --confirm-d04-mutation

WONIUNOTE_ITER21_D04_HANDOFF=approved \
  bash scripts/tests/iter21-business-runtime/run.sh repair-original-upload-layout \
  --confirm-d04-mutation
```

The first command stops only the verified original backend; systemd also stops
its dependent dedicated HTTPS unit. MySQL, Redis and global services remain
untouched. The second command requires both original units to be inactive and
port 5173 to be unbound, and leaves them inactive. The runtime config change
takes effect only on the next backend start. Root chooses whether the old UI
should return after inspecting the repair evidence; if so, root can explicitly
start its dedicated HTTPS unit (which pulls in the backend):

```bash
limactl -y shell woniunote-iter21-systemd-20261024t0028z -- sudo -n \
  systemctl start woniunote-iter21-business-original-nginx.service
```

If the old UI is no longer needed, leave the original units stopped for the
later maintenance transition. The repair command does not make that decision.

## First maintenance transition: full backup, verification, migration, candidate 2

This is a future operator runbook, not an assertion that these steps have run.
It starts only after root has reviewed the completed browser handoff and its
saved/closed evidence under the existing isolated-rehearsal authorization. Do not run
`audit-original-schema` after business data exists: nonzero business rows
correctly make that reset-precondition audit return a GAP.

First stop only the dedicated original-v2 backend with the helper. It verifies
the exact original binary SHA, systemd MainPID, and sole port-5173 listener;
systemd also stops the dependent dedicated HTTPS unit, while MySQL, Redis and
global services remain up. Then, as
guest root, create a private backup directory and compare the live MySQL
identity to both original-v2 and candidate runtime configs. This command only
prints database identity fields, never passwords, JWT secrets, or config
contents:

```bash
limactl -y shell woniunote-iter21-systemd-20261024t0028z -- sudo -n /bin/bash -s <<'GUEST'
set -Eeuo pipefail
umask 077
MYSQL_CNF=/root/.config/woniunote-iter21/mysql-client.cnf
ORIGINAL_CONFIG=/var/lib/woniunote-iter21-business/original-v2-runtime/runtime-config.json
CANDIDATE_CONFIG=/var/lib/woniunote-iter21-data/runtime-config.json
BACKUP_DIR=/var/lib/woniunote-iter21-business/evidence/first-maintenance
mkdir -p "$BACKUP_DIR"
chmod 0700 /var/lib/woniunote-iter21-business/evidence "$BACKUP_DIR"
/usr/bin/python3 - "$MYSQL_CNF" "$ORIGINAL_CONFIG" "$CANDIDATE_CONFIG" <<'PY'
import configparser
import json
import os
import stat
import subprocess
import sys

mysql_path, original_path, candidate_path = sys.argv[1:]

def private_regular(path):
    info = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
        raise SystemExit(f"required root-owned mode-0600 regular file: {path}")

private_regular(mysql_path)
client = configparser.ConfigParser(interpolation=None)
if not client.read(mysql_path) or "client" not in client:
    raise SystemExit("MySQL defaults file has no [client] section")
client = client["client"]
expected = (
    client.get("database", ""),
    client.get("user", ""),
    client.get("host", "localhost"),
    client.get("port", "3306"),
)
if not expected[0].startswith("woniunote_iter21_") or not expected[1].startswith("wni21_"):
    raise SystemExit("MySQL defaults file is not the isolated Iteration 21 identity")
if expected[2] not in {"localhost", "127.0.0.1"} or expected[3] != "3306":
    raise SystemExit("MySQL connection must remain on the isolated local service")
live = subprocess.run(
    ["mysql", f"--defaults-extra-file={mysql_path}", "--batch", "--raw",
     "--skip-column-names", "-e",
     'SELECT DATABASE(), SUBSTRING_INDEX(CURRENT_USER(), "@", 1)'],
    check=True, text=True, capture_output=True,
).stdout.rstrip("\n").split("\t")
if tuple(live) != expected[:2]:
    raise SystemExit("live MySQL identity does not match the private client defaults")
identities = []
for path in (original_path, candidate_path):
    private_regular(path)
    with open(path, encoding="utf-8") as stream:
        config = json.load(stream)
    clients = config.get("db_clients")
    if not isinstance(clients, list) or len(clients) != 1:
        raise SystemExit(f"expected exactly one db_clients entry in {path}")
    db = clients[0]
    identity = (
        db.get("dbname", ""), db.get("user", ""),
        db.get("host", ""), str(db.get("port", "")),
    )
    if identity != expected:
        raise SystemExit(f"runtime database identity differs from the private client identity: {path}")
    identities.append(identity)
if identities[0] != identities[1]:
    raise SystemExit("original and candidate runtime configs target different database identities")
print(f"database_identity=PASS schema={expected[0]} user={expected[1]} host={expected[2]} port={expected[3]}")
PY
GUEST
```

After the identity check above and before approving the backup table set,
run the read-only comment-vote preflight described in **Comment votes are a
separate tool**. Its placement later in this runbook is not execution order:
confirm the expected `canonical_only` state before the fixed 13-table backup,
restore verification, or either SQL migration. Any different state stops this
sequence for review of backup coverage; no apply step is implied.

Before running this dump, the candidate runtime config must be available
through the reviewed guest-secret process as a root-owned `0600` file.
Do not copy the original config blindly because its CORS origin and signing
secret belong to the old UI. The prior identity check must pass for the live
MySQL client, original runtime config, and candidate runtime config.

The following guest-only command captures the exact 13-table set, rejects
non-InnoDB tables before using `--single-transaction`, records exact source
counts before and after, and compares those counts to the dump's one-row-per-
`INSERT` statements. It creates a new root-only evidence directory and
refuses to overwrite an existing backup. Run it only after the old backend
has been stopped and the maintenance handoff is approved:

```bash
limactl -y shell woniunote-iter21-systemd-20261024t0028z -- sudo -n /bin/bash -s <<'GUEST'
set -Eeuo pipefail
umask 077
MYSQL_CNF=/root/.config/woniunote-iter21/mysql-client.cnf
ORIGINAL_CONFIG=/var/lib/woniunote-iter21-business/original-v2-runtime/runtime-config.json
CANDIDATE_CONFIG=/var/lib/woniunote-iter21-data/runtime-config.json
BACKUP_BASE=/var/lib/woniunote-iter21-business/evidence/first-maintenance
if systemctl is-active --quiet woniunote-iter21-business-original.service; then
  echo 'dedicated original-v2 backend is still active; stop it through the helper first' >&2
  exit 1
fi
[ -z "$(ss -H -ltnp 'sport = :5173')" ] || { echo 'port 5173 still has a listener' >&2; exit 1; }
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="$BACKUP_BASE/$RUN_ID"
install -d -o root -g root -m 0700 "$BACKUP_BASE"
mkdir -m 0700 "$BACKUP_DIR"
DUMP="$BACKUP_DIR/business-before-candidate2.sql"
COUNTS_BEFORE="$BACKUP_DIR/counts-before.tsv"
COUNTS_AFTER="$BACKUP_DIR/counts-after.tsv"
TABLES='users article comment comment_votes favorite credit card item math_training_records math_training_wrong_answers category cardcategory article_category'
[ ! -e "$DUMP" ] && [ ! -L "$DUMP" ] || { echo 'backup path already exists' >&2; exit 1; }
[ -f "$MYSQL_CNF" ] && [ ! -L "$MYSQL_CNF" ] && [ "$(stat -c '%u:%a' "$MYSQL_CNF")" = 0:600 ] || exit 1
IDENTITY="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --raw --skip-column-names \
  -e 'SELECT DATABASE(), SUBSTRING_INDEX(CURRENT_USER(), "@", 1)')"
IFS=$'\t' read -r DB_SCHEMA DB_USER <<< "$IDENTITY"
[[ "$DB_SCHEMA" =~ ^woniunote_iter21_[A-Za-z0-9_]+$ && "$DB_USER" =~ ^wni21_[A-Za-z0-9_]+$ ]] || exit 1
SCHEMA_NAMES="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
  -e 'SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE LEFT(SCHEMA_NAME, 17) = "woniunote_iter21_" ORDER BY SCHEMA_NAME')"
[ "$SCHEMA_NAMES" = "$DB_SCHEMA" ] || { echo 'selected schema is not the only D04 schema' >&2; exit 1; }
/usr/bin/python3 - "$MYSQL_CNF" "$ORIGINAL_CONFIG" "$CANDIDATE_CONFIG" "$DB_SCHEMA" "$DB_USER" <<'PY'
import configparser
import json
import os
import stat
import sys

mysql_path, original_path, candidate_path, live_schema, live_user = sys.argv[1:]
def private_regular(path):
    info = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
        raise SystemExit(f"required root-owned mode-0600 regular file: {path}")

private_regular(mysql_path)
client = configparser.ConfigParser(interpolation=None)
if not client.read(mysql_path) or "client" not in client:
    raise SystemExit("MySQL defaults file has no [client] section")
client = client["client"]
expected = (
    client.get("database", ""), client.get("user", ""),
    client.get("host", "localhost"), client.get("port", "3306"),
)
if expected[2] not in {"localhost", "127.0.0.1"} or expected[3] != "3306":
    raise SystemExit("MySQL connection must remain on the isolated local service")
if (live_schema, live_user) != expected[:2]:
    raise SystemExit("live MySQL identity differs from the private defaults")
for path in (original_path, candidate_path):
    private_regular(path)
    with open(path, encoding="utf-8") as stream:
        config = json.load(stream)
    clients = config.get("db_clients")
    if not isinstance(clients, list) or len(clients) != 1:
        raise SystemExit(f"expected exactly one db_clients entry in {path}")
    db = clients[0]
    identity = (
        db.get("dbname", ""), db.get("user", ""),
        db.get("host", ""), str(db.get("port", "")),
    )
    if identity != expected:
        raise SystemExit(f"runtime database identity differs from selected schema: {path}")
print(f"database_identity=PASS schema={live_schema} user={live_user}")
PY
EXPECTED="$(printf '%s\n' $TABLES | LC_ALL=C sort)"
ACTUAL="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --raw --skip-column-names \
  -e 'SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = "BASE TABLE" ORDER BY TABLE_NAME' \
  | LC_ALL=C sort)"
[ "$ACTUAL" = "$EXPECTED" ] || { echo 'unexpected selected-schema table set' >&2; exit 1; }
mysql --defaults-extra-file="$MYSQL_CNF" --batch --raw --skip-column-names \
  -e 'SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = "BASE TABLE" ORDER BY TABLE_NAME' \
  > "$BACKUP_DIR/engines.tsv"
[ "$(wc -l < "$BACKUP_DIR/engines.tsv" | tr -d ' ')" = 13 ] || exit 1
if awk -F '\t' '$2 != "InnoDB" {bad=1; print > "/dev/stderr"} END {exit bad ? 0 : 1}' "$BACKUP_DIR/engines.tsv"; then
  echo 'non-InnoDB table: stop and review backup consistency' >&2; exit 1
fi
write_counts() {
  local output="$1" table rows
  : > "$output"
  for table in $TABLES; do
    rows="$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
      -e "SELECT COUNT(*) FROM \`$table\`")"
    printf '%s\t%s\n' "$table" "$rows" >> "$output"
  done
  chmod 0600 "$output"
}
chmod 0600 "$BACKUP_DIR/engines.tsv"
write_counts "$COUNTS_BEFORE"
DUMP_CNF="$BACKUP_DIR/mysqldump-client.cnf"
# Preserve credential bytes verbatim; mysql-only options are not valid for mysqldump.
# Never print the input or derived file, or pass its password as an argument.
/usr/bin/python3 - "$MYSQL_CNF" "$DUMP_CNF" <<'PY'
import os
import re
import stat
import sys
source, destination = sys.argv[1:]
info = os.stat(source, follow_symlinks=False)
if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or stat.S_IMODE(info.st_mode) != 0o600:
    raise SystemExit("invalid private MySQL defaults file")
with open(source, "rb") as stream:
    lines = stream.read().splitlines(keepends=True)
filtered = []
group = b""
removed_database = 0
for line in lines:
    content = line.strip()
    if content.startswith(b"["):
        if not content.endswith(b"]"):
            raise SystemExit("invalid defaults group")
        group = content[1:-1].strip().lower()
    elif content and not content.startswith((b"#", b";")):
        option = re.split(rb"[\s:=]", content, maxsplit=1)[0].lower().replace(b"_", b"-")
        if group == b"client" and option in {b"database", b"connect-timeout"}:
            removed_database += option == b"database"
            continue
        if group.startswith(b"mysqldump") and option in {b"database", b"connect-timeout"}:
            raise SystemExit("unexpected dump-specific client option; review defaults")
    filtered.append(line)
if removed_database != 1:
    raise SystemExit("expected exactly one reviewed client database option")
fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
with os.fdopen(fd, "wb") as stream:
    os.fchown(stream.fileno(), 0, 0)
    os.fchmod(stream.fileno(), 0o600)
    stream.write(b"".join(filtered))
    stream.flush()
    os.fsync(stream.fileno())
PY
if ! MYSQL_TEST_LOGIN_FILE=/dev/null timeout 60s mysqldump \
  --defaults-extra-file="$DUMP_CNF" --protocol=TCP --no-tablespaces --single-transaction \
  --skip-lock-tables --skip-extended-insert --hex-blob --routines --events --databases "$DB_SCHEMA" \
  > "$DUMP" 2> "$BACKUP_DIR/mysqldump.stderr"; then
  echo 'dump failed or timed out; retain private evidence, keep writes stopped, inspect before retry' >&2
  exit 1
fi
[ -s "$DUMP" ] || { echo 'data dump is empty' >&2; exit 1; }
chmod 0600 "$DUMP"
for table in $TABLES; do
  grep -Fq "CREATE TABLE \`$table\`" "$DUMP" || { echo "dump lacks table $table" >&2; exit 1; }
done
while IFS=$'\t' read -r table source_rows; do
  dump_rows="$(grep -Ec "^INSERT INTO \`$table\` VALUES " "$DUMP" || true)"
  [ -n "$dump_rows" ] || dump_rows=0
  [ "$dump_rows" = "$source_rows" ] || { echo "dump row count mismatch for $table" >&2; exit 1; }
done < "$COUNTS_BEFORE"
write_counts "$COUNTS_AFTER"
cmp -s "$COUNTS_BEFORE" "$COUNTS_AFTER" || { echo 'source counts changed during dump' >&2; exit 1; }
{
  printf 'database_schema=%s\ndatabase_user=%s\n' "$DB_SCHEMA" "$DB_USER"
  printf 'captured_at_utc=%s\n' "$RUN_ID"
  printf 'original_binary_sha256=%s\n' \
    "$(sha256sum /var/lib/woniunote-iter21-business/original-v2/backend_cpp/build/woniunote_backend | awk '{print $1}')"
  printf 'backup_sha256=%s\n' "$(sha256sum "$DUMP" | awk '{print $1}')"
  printf 'backup_bytes=%s\n' "$(stat -c '%s' "$DUMP")"
  printf 'verification=PASS (table set, all InnoDB, exact source counts stable, dump INSERT counts match)\n'
} > "$BACKUP_DIR/manifest.txt"
chmod 0600 "$BACKUP_DIR/manifest.txt"
printf 'backup_dir=%s\n' "$BACKUP_DIR"
cat "$BACKUP_DIR/manifest.txt" "$BACKUP_DIR/engines.tsv" "$COUNTS_BEFORE"
GUEST
```

No database password is passed on a command line. The dump contains user
data; keep it and the manifests on the guest in the root-only directory.
Share only database/user identity, hashes, engines, and aggregate row counts
for review. Never print or copy the dump to host evidence or the repository.
This verifies dump structure and table data counts; it is not a restore drill.
The separate dump defaults file is required: the isolated rehearsal actually
failed when the shared defaults supplied `database`, then `connect-timeout`,
to `mysqldump`. The outer timeout bounds the process; a nonzero result never
authorizes migration or marks an incomplete dump as a valid backup.

Before a schema change, inspect the frozen candidate-2 commit and bind its
complete SHA to the migration inputs. The release manager runs real `npm ci`,
frontend build, CMake Release build, Nginx validation and smoke; it does not
run database migrations. Do not rerun original SQL01–09 after UI data exists.

For the inspected original-v2 database, the required ordered SQL set is:

| Order | Frozen input | Accepted before / required after | Reviewed SHA-256 |
|---|---|---|---|
| 1 | `scripts/sql/migrations/2026-10-23_math_answers.sql` | signed `INT NOT NULL` or already signed `DOUBLE NULL` → `DOUBLE NULL`; existing numeric values preserved | `5cef1a5aefb23e26191f8c9afa71d13f07ed0642ffe9eb1c19e8a4815cc0708b` |
| 2 | `scripts/sql/migrations/2026-10-24_article_thumbnail.sql` | nullable `VARCHAR(30)` or already `VARCHAR(512)`, NULL default, no generated/extra attributes → nullable `VARCHAR(512)`; values, charset, collation and comment preserved | `9b1bc83a4afe11883010a0d8e302b69d8c3254c3fe3cb46ccc75c77310b9365f` |

These hashes describe the currently reviewed candidate-5 inputs, not a future
candidate-2 commit automatically. Before maintenance, verify the frozen
candidate contains those exact bytes; a changed input requires an explicit
contract update. Missing or unexpected column shapes are stop conditions.
The original schema already has `article_category`, a 255-character password
column and canonical `comment_votes`; do not run unrelated historical
migrations merely because they exist in the directory.

Copy the two reviewed SQL files into the actual root-only backup directory
with their original basenames and mode 0600. Run the following **inside the
already verified guest, after handoff, stop-writing, backup and restore
verification**, never against the host or production MySQL:

```bash
set -Eeuo pipefail
umask 077
BACKUP_DIR=/var/lib/woniunote-iter21-business/evidence/first-maintenance/REVIEWED_RUN_ID
MYSQL_CNF=/root/.config/woniunote-iter21/mysql-client.cnf
DB_SCHEMA="$(awk -F= '$1 == "database_schema" {print $2; exit}' "$BACKUP_DIR/manifest.txt")"
[[ "$DB_SCHEMA" =~ ^woniunote_iter21_[A-Za-z0-9_]+$ ]] || exit 1
[ "$(mysql --defaults-extra-file="$MYSQL_CNF" --batch --skip-column-names \
    --database="$DB_SCHEMA" -e 'SELECT DATABASE()')" = "$DB_SCHEMA" ] || exit 1
MIGRATION_NAMES="${MIGRATION_NAMES:-2026-10-23_math_answers.sql 2026-10-24_article_thumbnail.sql}"
MIGRATION_ATTEMPT="$(date -u +%Y%m%dT%H%M%SZ)-$$"
for MIGRATION_NAME in $MIGRATION_NAMES; do
  case "$MIGRATION_NAME" in
    2026-10-23_math_answers.sql) EXPECTED_SHA=5cef1a5aefb23e26191f8c9afa71d13f07ed0642ffe9eb1c19e8a4815cc0708b ;;
    2026-10-24_article_thumbnail.sql) EXPECTED_SHA=9b1bc83a4afe11883010a0d8e302b69d8c3254c3fe3cb46ccc75c77310b9365f ;;
    *) exit 1 ;;
  esac
  MIGRATION_SQL="$BACKUP_DIR/$MIGRATION_NAME"
  MIGRATION_LOG="$BACKUP_DIR/$MIGRATION_NAME.$MIGRATION_ATTEMPT.log"
  [ -f "$MIGRATION_SQL" ] && [ ! -L "$MIGRATION_SQL" ] \
    && [ "$(stat -c '%u:%a' "$MIGRATION_SQL")" = 0:600 ] || exit 1
  [ ! -e "$MIGRATION_LOG" ] && [ ! -L "$MIGRATION_LOG" ] || exit 1
  [ "$(sha256sum "$MIGRATION_SQL" | awk '{print $1}')" = "$EXPECTED_SHA" ] || exit 1
  mysql --defaults-extra-file="$MYSQL_CNF" --default-character-set=utf8mb4 \
    --database="$DB_SCHEMA" < "$MIGRATION_SQL" > "$MIGRATION_LOG" 2>&1
  chmod 0600 "$MIGRATION_LOG"
  printf 'migration_applied=%s sha256=%s\n' "$MIGRATION_NAME" "$EXPECTED_SHA" \
    >> "$BACKUP_DIR/manifest.txt"
done
```

Use the actual run directory in place of `REVIEWED_RUN_ID`; placeholders are
not permission to pick another database. Keep logs root-only and do not print
their contents. MySQL DDL commits independently: a failed second migration
does not undo the first. Preserve the first result, inspect the actual schema
and restart only the necessary reviewed step with a fresh log name; never
shrink the thumbnail column or replay the old dump over later writes.
For example, if the math migration has been verified and only the thumbnail
step needs retry, export `MIGRATION_NAMES=2026-10-24_article_thumbnail.sql`
before rerunning this block. The allowlist and digest checks still apply;
the new attempt suffix preserves both earlier success and failure logs.

**Backup restore verification:** before either migration, restore the exact
hashed dump into a separate disposable MySQL instance with its own datadir,
process identity and isolated access endpoint, with no application connections
and no import directed at the original guest MySQL. This may be a separately
owned container/volume or the private socket-only instance below. The dump
contains `CREATE DATABASE`/`USE` statements;
passing a different database argument to the same instance is not isolation.
Read back the restore instance identity, the expected 13-table set, engines,
column shapes and exact table counts, and compare the saved draft identity and
content digests without publishing its body. Record the dump hash and the
restore result. The SQL dump does not contain uploaded files: separately
inventory and back up the persistent uploads, verify their file hashes on a
separate restore copy, and retain both artifacts. A merely existing dump or
matching INSERT count is insufficient to set a restore-verified flag. Do not
remove the restore target or backup before the result has been reviewed.

The completed Ubuntu VM rehearsal used a separate socket-only `mysqld`, not
a container. Its AppArmor profile already permits `/var/lib/mysql-files/**`;
using a datadir under the business evidence directory was denied. Do not
disable AppArmor or modify the system MySQL directory to bypass this. For
this VM, create a unique root-owned `0700` directory below the existing
`/var/lib/mysql-files` parent after checking that parent is a real directory
owned by the installed `mysql` account and mode `0700`. The core commands
below run **only inside the verified disposable guest**, with `DUMP`,
`DB_SCHEMA`, and the dump digest bound to the reviewed backup above:

```bash
set -Eeuo pipefail
umask 077
BACKUP_DIR=/var/lib/woniunote-iter21-business/evidence/first-maintenance/REVIEWED_RUN_ID
MANIFEST="$BACKUP_DIR/manifest.txt"
DUMP="$BACKUP_DIR/business-before-candidate2.sql"
for PRIVATE_FILE in "$MANIFEST" "$DUMP"; do
  [ -f "$PRIVATE_FILE" ] && [ ! -L "$PRIVATE_FILE" ] \
    && [ "$(stat -c '%u:%a' "$PRIVATE_FILE")" = 0:600 ] || exit 1
done
DB_SCHEMA="$(awk -F= '$1 == "database_schema" {print $2; exit}' "$MANIFEST")"
EXPECTED_DUMP_SHA="$(awk -F= '$1 == "backup_sha256" {print $2; exit}' "$MANIFEST")"
[[ "$DB_SCHEMA" =~ ^woniunote_iter21_[A-Za-z0-9_]+$ ]] || exit 1
[[ "$EXPECTED_DUMP_SHA" =~ ^[0-9a-f]{64}$ ]] || exit 1
[ "$(sha256sum "$DUMP" | awk '{print $1}')" = "$EXPECTED_DUMP_SHA" ] || exit 1
[ -d /var/lib/mysql-files ] && [ ! -L /var/lib/mysql-files ] || exit 1
[ "$(stat -c '%u:%g:%a' /var/lib/mysql-files)" = "$(id -u mysql):$(id -g mysql):700" ] || exit 1
SOURCE_MYSQL_PID="$(systemctl show mysql.service -p MainPID --value)"
[[ "$SOURCE_MYSQL_PID" =~ ^[1-9][0-9]*$ ]] || exit 1
RESTORE_DIR="$(mktemp -d /var/lib/mysql-files/woniunote-d04-restore-XXXXXXXX)"
chmod 0700 "$RESTORE_DIR"
mkdir -m 0700 "$RESTORE_DIR/data" "$RESTORE_DIR/tmp"
RESTORE_SOCKET="$RESTORE_DIR/mysql.sock"
RESTORE_PIDFILE="$RESTORE_DIR/mysql.pid"
MYSQLD="$(command -v mysqld)"
COMMON=(--no-defaults --user=root --datadir="$RESTORE_DIR/data"
  --tmpdir="$RESTORE_DIR/tmp" --socket="$RESTORE_SOCKET"
  --pid-file="$RESTORE_PIDFILE" --skip-networking --mysqlx=OFF
  --innodb-buffer-pool-size=32M)
MYSQL_TEST_LOGIN_FILE=/dev/null "$MYSQLD" "${COMMON[@]}" --initialize-insecure \
  --log-error="$RESTORE_DIR/init.log" > "$RESTORE_DIR/init.stdout" 2>&1
MYSQL_TEST_LOGIN_FILE=/dev/null "$MYSQLD" "${COMMON[@]}" \
  --log-error="$RESTORE_DIR/server.log" > "$RESTORE_DIR/server.stdout" 2>&1 &
RESTORE_PID=$!
printf 'restore_pid=%s\nsource_mysql_pid=%s\nrestore_dir=%s\nmysqld=%s\n' \
  "$RESTORE_PID" "$SOURCE_MYSQL_PID" "$RESTORE_DIR" "$MYSQLD" > "$RESTORE_DIR/process.meta"
restore_mysql() {
  MYSQL_TEST_LOGIN_FILE=/dev/null mysql --no-defaults --protocol=SOCKET \
    --socket="$RESTORE_SOCKET" --user=root "$@"
}
for attempt in $(seq 1 60); do
  kill -0 "$RESTORE_PID" || exit 1
  if restore_mysql -e 'SELECT 1' > /dev/null 2>&1; then break; fi
  [ "$attempt" -lt 60 ] || exit 1
  sleep 1
done
[ "$(cat "$RESTORE_PIDFILE")" = "$RESTORE_PID" ] || exit 1
# Verify /proc/$RESTORE_PID/cmdline contains the exact datadir and socket;
# verify it owns no TCP listener and differs from SOURCE_MYSQL_PID before import.
[ "$RESTORE_PID" != "$SOURCE_MYSQL_PID" ] || exit 1
tr '\0' '\n' < "/proc/$RESTORE_PID/cmdline" | grep -Fxq -- "--datadir=$RESTORE_DIR/data"
tr '\0' '\n' < "/proc/$RESTORE_PID/cmdline" | grep -Fxq -- "--socket=$RESTORE_SOCKET"
if ss -H -ltnp | grep -Fq "pid=$RESTORE_PID,"; then exit 1; fi
restore_mysql < "$DUMP" > "$RESTORE_DIR/import.stdout" 2> "$RESTORE_DIR/import.stderr"
restore_mysql --database="$DB_SCHEMA" --batch --skip-column-names \
  -e 'SELECT DATABASE(), @@datadir, @@socket, @@skip_networking, @@server_uuid' \
  > "$RESTORE_DIR/identity.tsv"
```

This starts a passwordless **private Unix-socket-only** restore instance; its
root-only parent is the access boundary. Review the captured identity and
compare tables, columns, indexes, foreign keys, exact counts and saved draft
digests as required above before marking restore verified. On success or
failure, stop only the captured restore PID after rechecking its PID file,
executable, datadir and socket; wait for that process to exit and verify the
original system MySQL PID is unchanged. Never use `pkill mysqld` or stop the
system MySQL service. Retain the private directory and logs for review.

After importing and completing those comparisons (or after an import failure),
the exact-process cleanup in the same guest shell is:

```bash
[ "$(cat "$RESTORE_PIDFILE")" = "$RESTORE_PID" ] || exit 1
[ "$RESTORE_PID" != "$SOURCE_MYSQL_PID" ] || exit 1
[ "$(readlink -f "/proc/$RESTORE_PID/exe")" = "$(readlink -f "$MYSQLD")" ] || exit 1
tr '\0' '\n' < "/proc/$RESTORE_PID/cmdline" | grep -Fxq -- "--datadir=$RESTORE_DIR/data"
tr '\0' '\n' < "/proc/$RESTORE_PID/cmdline" | grep -Fxq -- "--socket=$RESTORE_SOCKET"
kill -TERM "$RESTORE_PID"
for attempt in $(seq 1 60); do
  if ! kill -0 "$RESTORE_PID" 2>/dev/null; then break; fi
  [ "$attempt" -lt 60 ] || { echo 'restore process has not exited; retain evidence and inspect' >&2; exit 1; }
  sleep 1
done
RESTORE_EXIT=0
wait "$RESTORE_PID" || RESTORE_EXIT=$?
# A clean mysqld shutdown normally exits 0; allow SIGTERM status without
# skipping the original-service checks. Other exits remain a failed drill.
[ ! -e "/proc/$RESTORE_PID" ] || exit 1
[ "$(systemctl show mysql.service -p MainPID --value)" = "$SOURCE_MYSQL_PID" ] || exit 1
systemctl is-active --quiet mysql.service
[ "$RESTORE_EXIT" = 0 ] || [ "$RESTORE_EXIT" = 143 ] || exit 1
```

An earlier `set -e` failure may end that shell before cleanup. In that case,
start a fresh root shell in the verified guest and recover the exact run
paths and launched PID from its private `process.meta` and PID file, then
repeat the identity checks before stopping it; do not guess a process from its
name. The fresh shell is not the parent: replace `wait` with the bounded
`kill -0` loop and `/proc` absence check, and record the exit status as
unavailable rather than claiming it was zero. If initialization failed before a server was started, there is no
restore process to stop.

The completed rehearsal compared all 13 tables and the saved draft. It
archived the complete uploads directory but restored and hash-checked one
pinned real image in a separate copy. That result is a one-image restore
check, not a claim that every archived media file was individually restored.

**Comment votes are a separate tool, not part of the SQL loop.** Run the
frozen `scripts/migrate_comment_votes.py` without `--apply` as a read-only
preflight, retaining stdout/stderr in new mode-0600 guest evidence files. Its
currently reviewed SHA is
`cd61986568cdc272e4385b18a0aa1482d2df6d948e5e9c18f70a61fedd9c0b85`.
Use an explicitly selected guest Python with PyMySQL; on the macOS host all
Python commands must instead use Anaconda base. The tool does not consume the
MySQL defaults file: a root-only launcher must read the already verified
runtime JSON, check the DB host/port/name/user against the backup identity,
and pass `DB_PASS` only in the child environment. Do not put passwords in argv,
shell history, logs or an exported report. Check the preflight exit code:
0 means a report was produced without hard blockers, 2 means blocked and 1
means an execution error; all require review of the actual reported state.

For the inspected `canonical_only` state, require valid schema/constraints,
no hard blockers, and an explicit reviewed no-op; do not run apply merely to
create a migration receipt. If the state is `none`, `legacy_only` or `both`,
stop and review the backup table set and mapping first. The 13-table backup
above deliberately does not cover `comment_vote`, so it cannot be reused as
proof of a legacy/both-state backup. If a changed state genuinely requires
apply, its invocation additionally requires all of:

```text
--apply --run-id RUN_ID --writes-frozen-run-id RUN_ID
--backup-file ROOT_ONLY_DUMP --backup-sha256 VERIFIED_DUMP_SHA256
--backup-restore-verified --preserve-comment-counts
--approved-preflight-sha256 REVIEWED_SNAPSHOT_SHA256
--approval-file ROOT_ONLY_REVIEWED_MAPPING_JSON
```

The approval file must bind the current preflight snapshot and every required
duplicate/ID-remap choice. `--backup-restore-verified` is an assertion by the
operator, not a test performed by the tool. Keep preflight, approval and apply
reports root-only and share only sanitized hashes/counts. A partial apply
requires a new preflight and review of the resulting snapshot, not source
table deletion or manual renaming. Preserve existing comment counters as the
iteration-21 contract requires; count repair is not part of this maintenance.

After migration, repeat the database identity/config comparison and exact
per-table counts; compare the new schema columns to the reviewed candidate-2
contract. Require the target schema and database user to remain identical to
the pre-migration backup manifest. Verify the saved draft by ID/content
semantics using the candidate API/UI after first deployment. Any mismatch,
unexplained count change, missing table, different schema, or failed backup
verification is a stop condition; preserve the backup and do not deploy.

Only then use the existing `deploy-first` helper command with the frozen
candidate-2 commit and a real, already-persisted upload file under
`/var/lib/woniunote-iter21-data`. The upload URL, guest file path, and SHA must
refer to that same existing file; do not create synthetic upload data for the
smoke test. The helper requires the old backend stopped, port 5173 unbound, an
empty fresh manager state, exact source SHA, real guest Node 22.13.0,
`npm ci`, and CMake build jobs limited to two. The first transition has no
manager rollback pointer by design. After success, open candidate 2 on the
isolated candidate origin in a fresh browser context and log in again.
The guest virtual host is `https://yunjinqi.top`: before using that hostname
in a host browser, verify an explicit host/browser mapping to this isolated
guest or use an independently verified loopback tunnel with the expected
virtual-host routing. An ordinary public DNS lookup could reach production
and must not be used for this drill. Record the final origin and prove it
serves this guest's expected build; a certificate warning still requires user
handoff. This is a
different origin from `https://localhost:18443`; browser cookies,
localStorage, and IndexedDB do not transfer. Verify the saved server-side
draft by its recorded identity, and test candidate-local editor recovery
separately on the stable candidate origin. Original-v2 remains emergency
degraded only after candidate writes begin.

After root explicitly hands the VM over, mutations require both the explicit
environment gate and the command flag below. Candidate staging also requires
a clean repository at the specified commit. Candidate 2 and 3 are copied with
their Git metadata intact; an existing destination is never overwritten.

```bash
WONIUNOTE_ITER21_D04_HANDOFF=approved \
  bash scripts/tests/iter21-business-runtime/run.sh stage candidate-2 /absolute/frozen/candidate-2 FULL_COMMIT_SHA --confirm-d04-mutation

WONIUNOTE_ITER21_D04_HANDOFF=approved \
  bash scripts/tests/iter21-business-runtime/run.sh stop-original ORIGINAL_BINARY_SHA256 --confirm-d04-mutation
```

The first managed deployment accepts only candidate 2, verifies that the
backend is stopped and port 5173 is free, then runs the real manager with real
`npm ci`, frontend build, CMake Release/system-libs build, and Nginx smoke. The
upload sample must already exist under the guest persistent data directory;
the helper checks its SHA before passing it to the manager. Its thumbnail URL
must be a real `/api/thumb/...` resource. The exact paths and hashes are
deliberately supplied by the operator after inspecting existing data.

Before this first deployment, the reviewer must persist a root-owned mode-0600
`initial-install.env` under the isolated evidence directory. It must bind the
candidate SHA and the **reviewed** first-maintenance `manifest.txt` digest:

```text
TO_SHA=FULL_CANDIDATE_2_COMMIT_SHA
MODE=maintenance
REVIEWED=PASS
EDITOR_HANDOFF=PASS
WRITE_FREEZE=PASS
BACKUP_RESTORE=PASS
SCHEMA=PASS
EVIDENCE=/var/lib/woniunote-iter21-business/evidence/first-maintenance/RUN_ID/manifest.txt
EVIDENCE_SHA256=VERIFIED_MANIFEST_SHA256
```

Use real values after checking the editor handoff, write freeze, independent
backup restore and migrated schema. Do not execute this template or create
PASS records merely to satisfy the gate. The helper requires canonical guest
paths, regular non-symlink files, root ownership and mode 0600 for the record;
it accepts only maintenance mode. It forwards the record only for
`deploy-first`, and the release manager independently validates it before
building. Its integrity check does not perform the business review itself.
The record is a new file; preserve the reviewed manifest and prior attempts.

```bash
WONIUNOTE_ITER21_D04_HANDOFF=approved \
  WONIUNOTE_ITER21_INITIAL_INSTALL_RECORD=/var/lib/woniunote-iter21-business/evidence/first-maintenance/RUN_ID/initial-install.env \
  bash scripts/tests/iter21-business-runtime/run.sh deploy-first candidate-2 FULL_COMMIT_SHA \
  /api/thumb/REAL_FILE /api/uploads/REAL_FILE \
  /var/lib/woniunote-iter21-data/uploads/REAL_FILE UPLOAD_SHA256 \
  first-install-after-maintenance --confirm-d04-mutation
```

After root-reviewed, hash-bound two-way compatibility evidence exists, use
`deploy` for candidate 2→3, `rollback` for 3→2, then `deploy` again for 2→3.
Both operations verify the current and target source SHA before invoking
`deploy_release.sh`; rollback also requires the reverse compatibility record.
The manager is configured for two build jobs and the VM's real Node 22.13.0.
No production credentials are passed on command lines or written into host
evidence. Runtime configuration is read from the existing guest mode-0600
file.

The category API probe requests only `/api/articles/types` over guest loopback
using `curl --resolve yunjinqi.top:443:127.0.0.1`; it does not follow external
redirects. It reports HTTP status, response size/hash, and the count of
non-empty visible categories without saving or printing the response body.
`capture` records read-only schema metadata when the guest MySQL client config
selects a database; estimated row counts are labeled as estimates. A healthy
API response and schema listing do not prove login, session, editor recovery,
or persisted user-data semantics. Root must perform the visual CAPTCHA and
browser flows manually through the local HTTPS tunnel.

Shell syntax and the read-only audit are not login, session, editor recovery,
or persistence acceptance. A successful helper command, manager smoke, or
synthetic runtime run alone is not D04 business acceptance.

Final candidate routing also accepts `candidate-4`. First maintenance remains restricted to `candidate-2`; rollback selects the unique frozen repository matching the current full source SHA and rejects unknown or ambiguous matches. Run `bash scripts/tests/iter21-business-runtime/test-candidate-routing.sh` for the isolated three-case routing check.

候选5增量：为编辑器DOM-ready修复后的静态制品提供独立候选标签；stage/deploy与精确SHA回滚选择支持candidate-5，首次安装仍只允许candidate-2，既有候选目录仍禁止覆盖。定向routing fixture保留4→3并增加5→4、未知/重复SHA拒绝；它只验证路由，不能替代VM部署和业务验收。
