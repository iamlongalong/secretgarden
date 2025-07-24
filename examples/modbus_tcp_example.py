#!/usr/bin/env python3
"""
Example of using ModbusTCPSource to communicate with a Modbus TCP soil sensor.
"""
import logging
import sys
import time
import json
import os
from typing import Dict, Any

# Add the src directory to the path so we can import our modules
sys.path.insert(0, ".")

from src.core.constants import CommType, ModbusFunction, SoilRegister
from src.core.modbus import ModbusAdapter
from src.plugins.soil import SOIL_SENSOR_CONFIG, SoilSensor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# TCP Configuration from environment variables
TCP_CONFIG = {
    "host": os.environ.get("MODBUS_HOST", "192.168.2.4"),  # Replace with your Modbus TCP server IP
    "port": int(os.environ.get("MODBUS_PORT", 502)),       # Default Modbus TCP port
    "unit_id": int(os.environ.get("MODBUS_UNIT_ID", 1))    # Modbus unit/slave ID
}

class SoilSensorTCP:
    """Class for soil sensor data using Modbus TCP."""
    
    def __init__(
        self,
        tcp_config: Dict,
        read_interval: int = 60  # Read every 60 seconds
    ):
        """Initialize TCP soil sensor reader.
        
        Args:
            tcp_config: TCP configuration
            read_interval: Data reading interval in seconds
        """
        # Create soil sensor instance with TCP configuration
        self.sensor = SoilSensor(
            modbus_type=CommType.TCP,
            unit_id=tcp_config["unit_id"],
            host=tcp_config["host"],
            port=tcp_config["port"]
        )
        
        # Set decimal places for all readings
        self.sensor.set_decimal_places(2)
        
        self.read_interval = read_interval
        self.host = tcp_config["host"]
        self.port = tcp_config["port"]
        
    def start(self):
        """Start reading data from the sensor."""
        try:
            # Connect to Modbus TCP server
            self.sensor.modbus.connect()
            
            logger.info(f"Connected to Modbus TCP server at {self.host}:{self.port}")
            
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
                logger.info("Stopping sensor reading")
                
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
            time.sleep(1)
            
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
    """Run the soil sensor TCP reader."""
    try:
        # Get read interval from environment or use default
        read_interval = int(os.environ.get("READ_INTERVAL", 20))
        
        # Create and start sensor reader
        sensor_reader = SoilSensorTCP(
            tcp_config=TCP_CONFIG,
            read_interval=read_interval
        )
        
        sensor_reader.start()
        
    except Exception as e:
        logger.error(f"Sensor reader error: {e}")

if __name__ == "__main__":
    main() 