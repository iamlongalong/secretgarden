#!/usr/bin/env python3
"""
Example of a sensor monitoring application with data logging and alerts.
"""
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.core.constants import CommType, ModbusBaudRate, Unit
from src.plugins.soil import SoilSensor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SensorMonitor:
    """Sensor monitoring application."""
    
    def __init__(
        self,
        log_dir: str = "logs",
        alert_thresholds: Optional[Dict] = None
    ):
        """Initialize monitor.
        
        Args:
            log_dir: Directory for storing log files
            alert_thresholds: Dictionary of parameter thresholds for alerts
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Default thresholds
        self.thresholds = alert_thresholds or {
            "moisture": (20.0, 80.0),  # min, max percentage
            "temperature": (10.0, 35.0),  # min, max °C
            "ec": (500, 3000),  # min, max us/cm
            "ph": (5.5, 7.5)  # min, max pH
        }
        
        self.current_alerts: List[str] = []
        
    def start_monitoring(
        self,
        comm_type: CommType = CommType.SERIAL,
        **kwargs
    ):
        """Start monitoring sensors.
        
        Args:
            comm_type: Communication type (SERIAL or MQTT)
            **kwargs: Additional arguments for sensor initialization
        """
        try:
            # Initialize sensor
            sensor = SoilSensor(comm_type, **kwargs)
            
            # Connect to sensor
            if not sensor.modbus.connect():
                logger.error("Failed to connect to sensor")
                return
                
            try:
                while True:
                    try:
                        # Read sensor data
                        data = sensor.get_all()
                        npk = sensor.get_npk()
                        data.update(npk)
                        
                        # Process data
                        self._process_data(data)
                        
                        # Wait before next reading
                        time.sleep(60)  # Read every minute
                        
                    except Exception as e:
                        logger.error(f"Error reading sensor: {e}")
                        time.sleep(5)
                        
            except KeyboardInterrupt:
                logger.info("Stopping monitoring")
                
            finally:
                sensor.modbus.disconnect()
                
        except Exception as e:
            logger.error(f"Error initializing sensor: {e}")
            
    def _process_data(self, data: Dict):
        """Process sensor data.
        
        Args:
            data: Dictionary of sensor readings
        """
        # Check for alerts
        new_alerts = self._check_alerts(data)
        
        # Log data
        self._log_data(data, new_alerts)
        
        # Update current alerts
        if new_alerts != self.current_alerts:
            if new_alerts:
                logger.warning("Active alerts: " + ", ".join(new_alerts))
            elif self.current_alerts:
                logger.info("All alerts cleared")
            self.current_alerts = new_alerts
            
    def _check_alerts(self, data: Dict) -> List[str]:
        """Check for threshold violations.
        
        Args:
            data: Dictionary of sensor readings
            
        Returns:
            List of active alerts
        """
        alerts = []
        
        for param, (min_val, max_val) in self.thresholds.items():
            if param in data:
                value = data[param]
                if value < min_val:
                    alerts.append(
                        f"{param} too low: {value:.1f} (min: {min_val})"
                    )
                elif value > max_val:
                    alerts.append(
                        f"{param} too high: {value:.1f} (max: {max_val})"
                    )
                    
        return alerts
        
    def _log_data(self, data: Dict, alerts: List[str]):
        """Log sensor data and alerts.
        
        Args:
            data: Dictionary of sensor readings
            alerts: List of active alerts
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create log entry
        log_entry = {
            "timestamp": timestamp,
            "readings": data,
            "alerts": alerts
        }
        
        # Write to daily log file
        date = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f"sensor_log_{date}.jsonl")
        
        try:
            with open(log_file, "a") as f:
                json.dump(log_entry, f)
                f.write("\n")
        except Exception as e:
            logger.error(f"Error writing to log file: {e}")
            
        # Print current readings
        print(f"\nSensor Readings at {timestamp}")
        print("-" * 40)
        for key, value in data.items():
            unit = Unit[key.upper()].value if hasattr(Unit, key.upper()) else ""
            print(f"{key:12}: {value:8.1f} {unit}")
        if alerts:
            print("\nAlerts:")
            for alert in alerts:
                print(f"! {alert}")
        print("-" * 40)

def main():
    """Run the monitoring application."""
    try:
        # Create monitor instance
        monitor = SensorMonitor(
            log_dir="sensor_logs",
            alert_thresholds={
                "moisture": (30.0, 70.0),
                "temperature": (15.0, 30.0),
                "ec": (800, 2500),
                "ph": (6.0, 7.0)
            }
        )
        
        # Start monitoring with serial connection
        monitor.start_monitoring(
            comm_type=CommType.SERIAL,
            port="/dev/ttyUSB0",  # Change this to match your system
            baudrate=ModbusBaudRate.BAUD_4800
        )
        
    except Exception as e:
        logger.error(f"Application error: {e}")

if __name__ == "__main__":
    main() 