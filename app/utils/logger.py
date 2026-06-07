import logging

def get_logger(name: str = "spc_spi"):
    # Library helper must not mutate root logger configuration.
    # Entrypoints (e.g., main/check scripts) are responsible for basicConfig.
    return logging.getLogger(name)
