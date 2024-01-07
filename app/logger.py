import logging


inventory_logger = logging.getLogger("inventory-log")
inventory_logger.setLevel(logging.DEBUG)

# formatters
formatter = logging.Formatter(
    fmt=f"%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# handlers
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
# file_handler = logging.FileHandler('app.log')
# sqlalchemy_handler = logging.FileHandler('sqlalchemy.log')

# register formatters
stream_handler.setFormatter(formatter)
# file_handler.setFormatter(formatter) #(save for log rotate in future)
# sqlalchemy_handler.setFormatter(formatter)

# register handlers
inventory_logger.handlers = [
    stream_handler,
    # file_handler
]
# inventory_logger.addHandler(stream_handler)

# detach from root inventory_logger inheritance
inventory_logger.propagate = False
inventory_logger.disabled = False
