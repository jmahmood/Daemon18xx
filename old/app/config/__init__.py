import importlib

def load_config(name: str):
    """Dynamically load a rules configuration module."""
    return importlib.import_module(f'app.config.{name}')
