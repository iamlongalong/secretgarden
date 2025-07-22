#!/usr/bin/env python3
"""
Example of using air environment sensor over MQTT.
This example shows how to handle multiple sensors on the same bus.
"""
import logging
import time
from typing import Dict, List

from src.core.constants import CommType
from src.plugins.air import AirSensor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_CONFIG = {
    "host": "192.168.2.4",
    "port": 1883,
    "username": "garden",
    "password": "garden123",
    "topic_down": "garden_weather/down",  # Commands TO sensors
    "topic_up": "garden_weather/up"      # Data FROM sensors
}

class AirSensorMonitor:
    """Monitor multiple air sensors."""
    
    def __init__(
        self,
        mqtt_config: Dict,
        unit_ids: List[int],
        read_interval: int = 60  # Read every 60 seconds
    ):
        """Initialize monitor.
        
        Args:
            mqtt_config: MQTT configuration
            unit_ids: List of sensor unit IDs to monitor
            read_interval: Data reading interval in seconds
        """
        # Create sensors for each unit ID
        self.sensors = {}
        for unit_id in unit_ids:
            sensor = AirSensor(
                modbus_type=CommType.MQTT,
                unit_id=unit_id,
                client_id=f"air_sensor_{unit_id}",
                request_topic=mqtt_config["topic_down"],
                response_topic=mqtt_config["topic_up"],
                host=mqtt_config["host"],
                port=mqtt_config["port"],
                username=mqtt_config["username"],
                password=mqtt_config["password"]
            )
            self.sensors[unit_id] = sensor
            
        self.read_interval = read_interval
        
    def start(self):
        """Start monitoring."""
        try:
            # Connect all sensors
            for unit_id, sensor in self.sensors.items():
                sensor.modbus.connect()
                logger.info(f"Connected sensor {unit_id}")
                
            logger.info(
                f"Monitoring started. Using topics: "
                f"up={MQTT_CONFIG['topic_up']}, "
                f"down={MQTT_CONFIG['topic_down']}"
            )
            
            # Start reading loop
            last_read = 0
            try:
                while True:
                    now = time.time()
                    if now - last_read >= self.read_interval:
                        self._read_and_log_data()
                        last_read = now
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("Stopping monitor")
                
        finally:
            # Disconnect all sensors
            for sensor in self.sensors.values():
                sensor.modbus.disconnect()
                
    def _read_and_log_data(self):
        """Read and log data from all sensors."""
        for unit_id, sensor in self.sensors.items():
            try:
                # Read all parameters in one request
                data = sensor.get_all()
                logger.info(
                    f"Sensor {unit_id}: "
                    f"Temperature={data['temperature']:.1f}°C, "
                    f"Humidity={data['humidity']:.1f}%, "
                    f"CO2={data['co2']:.0f}ppm, "
                    f"Light={data['light']:.0f}lux"
                )
                
            except Exception as e:
                logger.error(f"Error reading sensor {unit_id}: {e}")

def main():
    """Run the monitor."""
    try:
        # Create and start monitor with multiple sensors
        monitor = AirSensorMonitor(
            mqtt_config=MQTT_CONFIG,
            unit_ids=[1],  # Monitor two sensors with unit IDs 1 and 2
            read_interval=60  # Read every minute
        )
        
        monitor.start()
        
    except Exception as e:
        logger.error(f"Monitor error: {e}")

if __name__ == "__main__":
    main() 