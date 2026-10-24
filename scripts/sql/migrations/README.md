# SQL migrations (existing-database upgrades)

Fresh installs use the base schema in `scripts/sql/01_*.sql` … `09_*.sql`
(loaded in filename order by `scripts/init_db.sh` and the isolated
`backend_cpp/tests/integration/run_integration.sh`). Base SQL does not upgrade
an existing table. Neither startup nor the release manager automatically
applies these migrations.

Databases created **before** the dates below need the migrations in this
directory, applied in filename (date) order after schema inspection and a
verified backup. Re-running a migration is supported for its documented schema
states; missing or unexpected shapes are errors, not permission to recreate or
truncate an existing table.

| Order | File | Applies to | Why |
|---|---|---|---|
| 1 | `2026-06-01_widen_password_column.sql` | databases created before 2026-06-01 (`users.password` is `VARCHAR(100)`) | Portable PBKDF2-SHA256 hashes are 119 chars and overflowed the old column, failing registration/password changes on non-Linux hosts. Widen to `VARCHAR(255)`. |
| 2 | `2026-07-02_article_category_menu.sql` | databases created before 2026-07-02 (no `article_category` table) | Adds the editable article menu/category nodes used by the navigation and category-management features. |
| 3 | `2026-10-23_math_answers.sql` | known signed `INT NOT NULL` answer column, or already migrated `DOUBLE NULL` | Preserves old values while supporting skipped (`NULL`) and finite decimal answers. Unknown shapes are rejected. |
| 4 | `2026-10-24_article_thumbnail.sql` | known nullable `article.thumbnail VARCHAR(30)`, or already migrated nullable `VARCHAR(512)` | Stores complete same-origin upload URLs without truncating values. Preserves NULL, existing values and column character set/collation; unknown shapes are rejected. |

## How to apply (upgrade drill)

```bash
# Stop the backend first, then:
for f in scripts/sql/migrations/*.sql; do
  mysql -h "$DB_HOST" -u "$DB_USER" -p "$DB_NAME" < "$f"
done
```

Verify on a restored copy (or a synthetic equivalent schema) before touching
production, and record the evidence — see iteration 20 / Epic 20.7 (R20-05) for
the required upgrade-and-restore drill. Do not treat `database_transfer.sh
import --replace` as a lossless rollback path.

Iteration 21 also has a separate comment-vote migration tool,
`scripts/migrate_comment_votes.py`; its four-state preflight and maintenance
procedure are not performed by the SQL loop above. Follow the iteration plan
for that tool rather than renaming or dropping vote tables manually.

Before reopening writes, read back the migrated types and run the matching
application candidate against a disposable upgrade copy. For thumbnails,
check upload, draft creation, edit replacement, detailed/list DTOs, and actual
image bytes through the public entry point. Do not shrink the column back to
30 characters after new URLs have been stored. Normal rollback requires an
application version proven to understand the new schema and URL contract;
the original v2 renderer is not such a version. A pre-upgrade backup restore
is a separate emergency operation and loses later writes unless separately
reconciled.
