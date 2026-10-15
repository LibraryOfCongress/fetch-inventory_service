# Migrating a Pre-Community Database to the Community Version

Run from a server with SSH access that can reach the database directly.

`migrate_to_squash.sql` is in this folder.

Values used below — adjust for your environment:

| Thing      | Value                |
| ---------- | -------------------- |
| DB host    | `inventory-database` |
| DB name    | `inventory_service`  |
| DB user    | `postgres`           |
| Namespace  | `fetch`              |
| Deployment | `inventory-service`  |

---

## 1. Back up the database

```bash
pg_dump -h inventory-database -U postgres -Fc -p <port>\
  -f /tmp/inventory_service_pre_community.dump inventory_service
```

## 2. Copy the backup to your workstation

Run from your local machine:

```bash
scp <user>@<server>:/tmp/inventory_service_pre_community.dump ./
```

## 3. Scale the application down

```bash
kubectl -n fetch scale deployment inventory-service --replicas=0
kubectl -n fetch rollout status deployment inventory-service --timeout=120s
```

## 4. Run the transform

```bash
psql -h inventory-database -U postgres -d inventory_service -p <port> \
  -f migrate_to_squash.sql
```

Takes 60-90 seconds. Single transaction — it either commits or rolls back whole.

## 5. Run the post-migration commands

```bash
psql -h inventory-database -U postgres -d inventory_service -p <port> <<'SQL'
CREATE INDEX IF NOT EXISTS ix_items_accession_job_id          ON items(accession_job_id);
CREATE INDEX IF NOT EXISTS ix_non_tray_items_accession_job_id ON non_tray_items(accession_job_id);
CREATE INDEX IF NOT EXISTS ix_trays_accession_job_id          ON trays(accession_job_id);

INSERT INTO group_permissions (permission_id, group_id)
SELECT p.id, 1
FROM permissions p
WHERE NOT EXISTS (
    SELECT 1 FROM group_permissions gp
    WHERE gp.permission_id = p.id AND gp.group_id = 1
);
SQL
```

## 6. Scale the application back up

```bash
kubectl -n fetch scale deployment inventory-service --replicas=1
kubectl -n fetch rollout status deployment inventory-service --timeout=180s
```
