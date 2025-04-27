import sqltap

from app.config.config import get_settings


# Enable profiling only in certain environments
USE_PROFILER = get_settings().APP_ENVIRONMENT in {"debug", "local"}

# Global SQLTap profiler instance
profiler = sqltap.start() if USE_PROFILER else None
