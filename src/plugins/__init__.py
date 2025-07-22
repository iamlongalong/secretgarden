"""
Sensor-specific plugin implementations.
"""

from .soil import SoilSensor
from .air import AirSensor

__all__ = [
    'SoilSensor',
    'AirSensor'
] 