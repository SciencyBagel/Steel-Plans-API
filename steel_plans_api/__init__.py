import importlib.metadata

try:
    __version__ = importlib.metadata.version("steel-plans-api")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0"  # fallback if not installed

from .endpoints import *
from .enums import *
