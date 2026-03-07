"""Beacon - Distribute knowledge contexts and skills for AI-assisted development teams."""

__version__ = "0.2.0"

from .cli import main
from .distributor import WarehouseDistributor
from .initializer import WarehouseInitializer

__all__ = ["main", "WarehouseDistributor", "WarehouseInitializer"]
