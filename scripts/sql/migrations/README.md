# SQL migrations (existing-database upgrades)

Fresh installs use the base schema in `scripts/sql/01_*.sql` … `09_*.sql`
(loaded in filename order by `backend_cpp/tests/integration/run_integration.sh`
and by the deployment steps in the root `README.md`).

Databases created **before** the dates below need the migrations in this
directory, applied in filename (date) order. All of them are idempotent, so
re-running is safe.

| Order | File | Applies to | Why |
|---|---|---|---|
| 1 | `2026-06-01_widen_password_column.sql` | databases created before 2026-06-01 (`users.password` is `VARCHAR(100)`) | Portable PBKDF2-SHA256 hashes are 119 chars and overflowed the old column, failing registration/password changes on non-Linux hosts. Widen to `VARCHAR(255)`. |
| 2 | `2026-07-02_article_category_menu.sql` | databases created before 2026-07-02 (no `article_category` table) | Adds the editable article menu/category nodes used by the navigation and category-management features. |

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
