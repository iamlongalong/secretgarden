#!/usr/bin/env python3
"""
Example script demonstrating the usage of the soil sensor library.
"""
import logging
import time
from typing import Dict

from src.core.constants import CommType, ModbusBaudRate, Unit
from src.plugins.soil import SoilSensor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_sensor_data(data: Dict) -> None:
    """Print sensor data in a formatted way."""
    print("\nSensor Readings:")
    print("-" * 40)
    for key, value in data.items():
        if isinstance(value, (int, float)):
            unit = Unit[key.upper()].value if hasattr(Unit, key.upper()) else ""
            print(f"{key.capitalize():12}: {value:8.2f} {unit}")
        else:
            print(f"{key.capitalize():12}: {value}")
    print("-" * 40)

def serial_example():
    """Example using serial communication."""
    try:
        # Initialize soil sensor with serial communication
        soil = SoilSensor(
            modbus_type=CommType.SERIAL,
            port="/dev/ttyUSB0",  # Change this to match your system
            baudrate=ModbusBaudRate.BAUD_4800
        )
        
        # Connect to sensor
        if not soil.modbus.connect():
            logger.error("Failed to connect to sensor")
            return
            
        try:
            while True:
                try:
                    # Read all basic parameters
                    data = soil.get_all()
                    print_sensor_data(data)
                    
                    # Read NPK values
                    npk = soil.get_npk()
                    print("\nNPK Values:")
                    print_sensor_data(npk)
                    
                    # Wait before next reading
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error reading sensor: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Stopping sensor readings")
            
        finally:
            soil.modbus.disconnect()
            
    except Exception as e:
        logger.error(f"Error initializing sensor: {e}")

def mqtt_example():
    """Example using MQTT communication."""
    try:
        # Initialize soil sensor with MQTT communication
        soil = SoilSensor(
            modbus_type=CommType.MQTT,
            client_id="soil_sensor_1",
            host="localhost",
            port=1883,
            topic_prefix="modbus/soil_1"
        )
        
        # Connect to MQTT broker
        if not soil.modbus.connect():
            logger.error("Failed to connect to MQTT broker")
            return
            
        try:
            while True:
                try:
                    # Read all basic parameters
                    data = soil.get_all()
                    print_sensor_data(data)
                    
                    # Read NPK values
                    npk = soil.get_npk()
                    print("\nNPK Values:")
                    print_sensor_data(npk)
                    
                    # Wait before next reading
                    time.sleep(5)
                    
                except Exception as e:
                    logger.error(f"Error reading sensor: {e}")
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info("Stopping sensor readings")
            
        finally:
            soil.modbus.disconnect()
            
    except Exception as e:
        logger.error(f"Error initializing sensor: {e}")

def main():
    """Run the example."""
    # Choose which example to run
    use_mqtt = False  # Set to True to use MQTT example
    
    if use_mqtt:
        mqtt_example()
    else:
        serial_example()

if __name__ == "__main__":
    main() 