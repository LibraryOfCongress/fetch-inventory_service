import threading
import uuid
from typing import Dict, Optional

from folioclient import FolioClient

_LOCK = threading.Lock()
_STORE: Dict[uuid.UUID, FolioClient] = {}


def get_client(config_id: uuid.UUID) -> Optional[FolioClient]:
    """
    Returns a cached, already-authenticated FolioClient for the given ILSConfiguration
    id, or None if there is no cached client yet. FolioClient refreshes its own access
    token internally as needed, so a cached instance stays valid for the life of the
    process (or until cleared) without any separate expiry bookkeeping here.
    """
    with _LOCK:
        return _STORE.get(config_id)


def set_client(config_id: uuid.UUID, client: FolioClient) -> None:
    """
    Caches a FolioClient for the given ILSConfiguration id. Clients are cached globally
    (module-level, keyed by ILSConfiguration.id) so they survive across the per-call
    adapter instances the factory constructs, instead of logging into FOLIO on every
    single operation.
    """
    with _LOCK:
        _STORE[config_id] = client


def clear_client(config_id: uuid.UUID) -> None:
    """
    Removes and closes any cached FolioClient for the given ILSConfiguration id.
    Primarily used by tests to avoid leaking state (and open HTTP connections) across
    test cases, since this store is module-level/process-global.
    """
    with _LOCK:
        client = _STORE.pop(config_id, None)

    if client is not None:
        try:
            client.close()
        except Exception:
            pass
