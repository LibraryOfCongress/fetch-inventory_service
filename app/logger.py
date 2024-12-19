import logging

# output to stream
inventory_logger = logging.getLogger("inventory-log")
inventory_logger.setLevel(logging.DEBUG)
migration_logger = logging.getLogger("migration")
migration_logger.setLevel(logging.DEBUG)

# output to log file
data_activity_logger = logging.getLogger("security-log")
data_activity_logger.setLevel(logging.DEBUG)

# formatters
formatter = logging.Formatter(
    fmt=f"%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
migration_formatter = logging.Formatter(
    fmt=f"[%(asctime)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S"
)
data_activity_log_stream_formatter = logging.Formatter(
    fmt=f"%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# handlers
stream_handler = logging.StreamHandler()
data_activity_stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
data_activity_stream_handler.setLevel(logging.DEBUG)
migration_handler = logging.StreamHandler()
# file_handler = logging.FileHandler('app/logs/data_activity.log')
# sqlalchemy_handler = logging.FileHandler('sqlalchemy.log')

# register formatters
stream_handler.setFormatter(formatter)
data_activity_stream_handler.setFormatter(data_activity_log_stream_formatter)
migration_handler.setFormatter(migration_formatter)
# file_handler.setFormatter(data_activity_log_file_formatter) #(save for log rotate in future)
# sqlalchemy_handler.setFormatter(formatter)

# register handlers
inventory_logger.handlers = [
    stream_handler,
    # file_handler
]
migration_logger.handlers = [
    migration_handler
]
data_activity_logger.handlers = [
    # file_handler
    data_activity_stream_handler
]
# inventory_logger.addHandler(stream_handler)

# detach from root inventory_logger inheritance
inventory_logger.propagate = False
inventory_logger.disabled = False
migration_logger.propagate = False
migration_logger.disabled = False
data_activity_logger.propagate = False
data_activity_logger.disabled = False

# This filter is used to restrict logging only to these routes
security_log_route_filter = [
    '/auth',
    '/groups',
    '/users',
    '/permissions'
]
