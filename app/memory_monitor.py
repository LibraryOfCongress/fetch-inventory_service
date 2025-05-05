# Used to trace Python memory allocations
# keep disabled  (in main) in most cases

import tracemalloc, time, threading
from app.logger import inventory_logger


tracemalloc.start()

def log_memory_growth(interval_sec: int = 60, top: int = 10):
    inventory_logger.disabled = False
    prev_snapshot = None

    while True:
        time.sleep(interval_sec)
        snapshot = tracemalloc.take_snapshot()

        if prev_snapshot:
            top_stats = snapshot.compare_to(prev_snapshot, 'lineno')
            inventory_logger.info("[Memory Monitor] Top memory differences since last check:")

            for stat in top_stats[:top]:
                inventory_logger.info(stat)

        prev_snapshot = snapshot

# Run in background thread
threading.Thread(target=log_memory_growth, daemon=True).start()
