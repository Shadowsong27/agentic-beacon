"""Beacon - Distribute knowledge contexts and skills for AI-assisted development teams."""

__version__ = "0.1.0"

from .cli import main
from .distributor import WarehouseDistributor

__all__ = ["main", "WarehouseDistributor"]
