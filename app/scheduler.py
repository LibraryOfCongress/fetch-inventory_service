# /app/scheduler.py

import os
import gzip
import csv
import logging
from io import StringIO
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database.session import session_manager
from app.models.scheduled_exports import ScheduledExport, ExportHistory

logger = logging.getLogger("inventory_logger")

# Ensure export directory exists
EXPORT_DIR = "/code/app/data/exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

scheduler = BackgroundScheduler()

def resolve_dynamic_dates(range_type: str, base_time: datetime):
    """
    Calculates from_dt and to_dt based on a dynamic range keyword.
    """
    if range_type == "last_24h":
        return base_time - timedelta(hours=24), base_time
    
    elif range_type == "yesterday":
        # Full previous calendar day relative to base_time
        yesterday = base_time - timedelta(days=1)
        from_dt = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        to_dt = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        return from_dt, to_dt
    
    elif range_type == "last_7d":
        from_dt = (base_time - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        to_dt = base_time # Up to now
        return from_dt, to_dt
    
    elif range_type == "last_30d":
        from_dt = (base_time - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
        to_dt = base_time # Up to now
        return from_dt, to_dt
    
    return None, None

def run_export_job(export_id: int, scheduled_time: datetime):
    """
    Background task to execute a scheduled export.
    :param scheduled_time: The time this job was intended to run.
    """
    # Lazy import to avoid circular dependency with reporting router
    from app.routers.reporting import get_export_stmt_and_headers

    with session_manager() as session:
        # 1. Fetch config
        export_config = session.get(ScheduledExport, export_id)
        if not export_config or not export_config.is_active:
            return

        # 2. Create history record
        now_utc = datetime.now(timezone.utc)
        history = ExportHistory(
            scheduled_export_id=export_id,
            filename=f"{export_config.dataset}_{now_utc.strftime('%Y%m%d_%H%M%S')}.csv.gz",
            file_path="",  # set below
            status="running",
            expires_at=now_utc + timedelta(days=export_config.retention_days)
        )
        history.file_path = os.path.join(EXPORT_DIR, history.filename)
        session.add(history)
        session.commit()

        try:
            # 3. Resolve filters (Static vs Dynamic)
            from_dt = export_config.filters.get("from_dt") if export_config.filters else None
            to_dt = export_config.filters.get("to_dt") if export_config.filters else None
            
            if export_config.filters and export_config.filters.get("date_range_type") == "dynamic":
                range_type = export_config.filters.get("dynamic_range")
                d_from, d_to = resolve_dynamic_dates(range_type, scheduled_time)
                if d_from:
                    from_dt = d_from
                    to_dt = d_to
                    logger.info(f"Resolved dynamic range '{range_type}' to {from_dt} - {to_dt}")

            # 4. Get the SQL statement and headers
            stmt, headers = get_export_stmt_and_headers(
                export_config.dataset, 
                from_dt, 
                to_dt,
                session
            )

            # 5. Execute and stream to GZIP file
            with open(history.file_path, 'wb') as f:
                with gzip.GzipFile(fileobj=f, mode='wb', compresslevel=6) as gz:
                    # Write headers
                    csv_buffer = StringIO()
                    writer = csv.writer(csv_buffer, delimiter=',', quoting=csv.QUOTE_MINIMAL)
                    writer.writerow(headers)
                    gz.write(csv_buffer.getvalue().encode('utf-8'))
                    
                    # Stream rows
                    result = session.execute(stmt.execution_options(stream_results=True)).yield_per(1000)
                    for row in result:
                        csv_buffer.seek(0)
                        csv_buffer.truncate(0)
                        writer.writerow(row)
                        gz.write(csv_buffer.getvalue().encode('utf-8'))
            
            # 6. Update history status
            history.status = "completed"
            history.file_size_bytes = os.path.getsize(history.file_path)
            export_config.last_run_at = now_utc
            
            # Update next_run_at if recurring
            if export_config.schedule_type == "recurring":
                # FIX: Calculate next run based on scheduled_time to prevent drift
                if export_config.frequency == "daily":
                    export_config.next_run_at = scheduled_time + timedelta(days=1)
                elif export_config.frequency == "weekly":
                    export_config.next_run_at = scheduled_time + timedelta(weeks=1)
                elif export_config.frequency == "monthly":
                    # Simple monthly
                    export_config.next_run_at = scheduled_time + timedelta(days=30)
            else:
                # One-time job, deactivate after run
                export_config.is_active = False
                export_config.next_run_at = None

            session.commit()
            logger.info(f"Successfully completed scheduled export: {export_config.name}")

        except Exception as e:
            session.rollback()
            history.status = "failed"
            history.error_message = str(e)[:1000]
            session.commit()
            logger.error(f"Failed scheduled export {export_config.name}: {e}")

def cleanup_expired_exports():
    """
    Nightly task to delete expired export files.
    """
    logger.info("Running automated export cleanup...")
    with session_manager() as session:
        now = datetime.now(timezone.utc)
        expired = session.execute(
            select(ExportHistory).where(ExportHistory.expires_at < now)
        ).scalars().all()

        for record in expired:
            try:
                if os.path.exists(record.file_path):
                    os.remove(record.file_path)
                    logger.info(f"Deleted expired export file: {record.filename}")
                session.delete(record)
            except Exception as e:
                logger.error(f"Error deleting expired export {record.filename}: {e}")
        
        session.commit()

def init_scheduler():
    """
    Initializes and starts the background scheduler.
    """
    if not scheduler.running:
        # Add the nightly cleanup job
        scheduler.add_job(
            cleanup_expired_exports, 
            CronTrigger(hour=0, minute=0), 
            id="cleanup_expired_exports",
            replace_existing=True
        )
        
        # Add a job to check for due exports every minute
        scheduler.add_job(
            check_and_trigger_exports,
            "interval",
            minutes=1,
            id="check_and_trigger_exports",
            replace_existing=True
        )
        
        scheduler.start()
        print("Background Scheduler started.")

def check_and_trigger_exports():
    """
    Checks the database for any exports that are due to run.
    Sets next_run_at to None before spawning the job to prevent double-triggering.
    """
    with session_manager() as session:
        now = datetime.now(timezone.utc)
        due_exports = session.execute(
            select(ScheduledExport)
            .where(ScheduledExport.is_active == True)
            .where(ScheduledExport.next_run_at <= now)
        ).scalars().all()

        for export in due_exports:
            # Capture the scheduled time before clearing it
            intended_time = export.next_run_at
            
            # Guard: clear next_run_at so we don't re-trigger on the next poll
            export.next_run_at = None
            session.commit()

            # Trigger the job in another thread via APScheduler
            scheduler.add_job(
                run_export_job,
                args=[export.id, intended_time],
                id=f"run_export_{export.id}_{now.timestamp()}"
            )
