#!/usr/bin/env python3
"""
Example of a Modbus-MQTT bridge that forwards raw Modbus data over MQTT.
"""
import logging
import time
from typing import Dict, Optional

from src.core.constants import (CommType, DEFAULT_MQTT_QOS, ModbusBaudRate,
                              ModbusFunction, SoilRegister)
from src.core.modbus import ModbusAdapter, ModbusMqttSource
from src.plugins.soil import SOIL_SENSOR_CONFIG, SoilSensor

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_CONFIG = {
    "host": "192.168.2.4",
    "port": 1883,
    "username": "garden",
    "password": "garden123",
    "topic_down": "garden_weather/down",  # Commands TO sensor
    "topic_up": "garden_weather/up",      # Data FROM sensor
    "unit_id": 2
}

class SoilSensorBridge:
    """Bridge for soil sensor data using MQTT."""
    
    def __init__(
        self,
        mqtt_config: Dict,
        read_interval: int = 60  # Read every 60 seconds
    ):
        """Initialize bridge.
        
        Args:
            mqtt_config: MQTT configuration
            read_interval: Data reading interval in seconds
        """
        # Create soil sensor instance with MQTT configuration
        self.sensor = SoilSensor(
            modbus_type=CommType.MQTT,
            unit_id=mqtt_config["unit_id"],  # Pass unit_id to SoilSensor
            client_id="soil_sensor_bridge",
            request_topic=mqtt_config["topic_down"],
            response_topic=mqtt_config["topic_up"],
            host=mqtt_config["host"],
            port=mqtt_config["port"],
            username=mqtt_config["username"],
            password=mqtt_config["password"]
        )
        
        self.read_interval = read_interval
        
    def start(self):
        """Start the bridge."""
        try:
            # Connect to MQTT broker
            self.sensor.modbus.connect()
            
            logger.info(
                f"Bridge started. Using topics: up={self.sensor.modbus.source.response_topic}, "
                f"down={self.sensor.modbus.source.request_topic}"
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
                logger.info("Stopping bridge")
                
        finally:
            self.sensor.modbus.disconnect()
            
    def _read_and_log_data(self):
        """Read and log sensor data."""
        try:
            # Read all basic parameters in one request
            basic = self.sensor.read_composite("all")
            logger.info(
                f"Basic parameters: "
                f"Moisture={basic['moisture']}%, "
                f"Temperature={basic['temperature']}°C, "
                f"EC={basic['ec']}us/cm, "
                f"pH={basic['ph']}"
            )
            
            # Small delay between reads
            time.sleep(0.5)
            
            # Read NPK values
            npk = self.sensor.read_composite("npk")
            logger.info(
                f"NPK values: "
                f"N={npk['nitrogen']}mg/kg, "
                f"P={npk['phosphorus']}mg/kg, "
                f"K={npk['potassium']}mg/kg"
            )
            
        except Exception as e:
            logger.error(f"Error reading sensor data: {e}")

def main():
    """Run the bridge."""
    try:
        # Create and start bridge
        bridge = SoilSensorBridge(
            mqtt_config=MQTT_CONFIG,
            read_interval=60  # Read every minute
        )
        
        bridge.start()
        
    except Exception as e:
        logger.error(f"Bridge error: {e}")

if __name__ == "__main__":
    main() 