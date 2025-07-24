#!/usr/bin/env python3
"""
Example of a Modbus-MQTT bridge that forwards raw Modbus data over MQTT.
"""
import logging
import time
import json
import os
from typing import Dict, Optional

from src.core.constants import (CommType, DEFAULT_MQTT_QOS, ModbusBaudRate,
                              ModbusFunction, SoilRegister)
from src.core.modbus import ModbusAdapter, ModbusMqttSource
from src.core.mqtt import MqttClient
from src.plugins.soil import SOIL_SENSOR_CONFIG, SoilSensor

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MQTT Configuration from environment variables
MQTT_CONFIG = {
    "host": os.environ.get("MQTT_HOST", "things.shanhehuhai.cn"),
    "port": int(os.environ.get("MQTT_PORT", 1883)),
    "username": os.environ.get("MQTT_USERNAME", "garden"),
    "password": os.environ.get("MQTT_PASSWORD", "garden123"),
    "topic_down": os.environ.get("MQTT_TOPIC_DOWN", "garden_weather/down"),  # Commands TO sensor
    "topic_up": os.environ.get("MQTT_TOPIC_UP", "garden_weather/up"),      # Data FROM sensor
    "unit_id": int(os.environ.get("MQTT_UNIT_ID", 2)),
    "telemetry_topic": os.environ.get("MQTT_TELEMETRY_TOPIC", "v1/devices/me/telemetry"),
    "telemetry_client_id": os.environ.get("MQTT_CLIENT_ID", "gardenx")
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
            client_id=mqtt_config["telemetry_client_id"],
            request_topic=mqtt_config["topic_down"],
            response_topic=mqtt_config["topic_up"],
            host=mqtt_config["host"],
            port=mqtt_config["port"],
            username=mqtt_config["username"],
            password=mqtt_config["password"]
        )

        # Set decimal places for all readings
        self.sensor.set_decimal_places(2)

        # 初始化上传遥测数据的 client
        self.telemetry_topic = mqtt_config["telemetry_topic"]
        self.telemetry_client_id = mqtt_config["telemetry_client_id"]
        self.telemetry_client = MqttClient(self.telemetry_client_id, host=mqtt_config["host"], port=mqtt_config["port"], username=mqtt_config["username"], password=mqtt_config["password"])
        self.telemetry_client.connect()
        
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

            self._upload_telemetry_data(basic)
            
            # Small delay between reads
            # time.sleep(1)
            
            # Read NPK values
            # npk = self.sensor.read_composite("npk")
            # logger.info(
            #     f"NPK values: "
            #     f"N={npk['nitrogen']}mg/kg, "
            #     f"P={npk['phosphorus']}mg/kg, "
            #     f"K={npk['potassium']}mg/kg"
            # )
            
        except Exception as e:
            logger.error(f"Error reading sensor data: {e}")

    def _upload_telemetry_data(self, data: Dict):
        """Upload telemetry data to ThingsBoard."""
        self.telemetry_client.publish(self.telemetry_topic, json.dumps(data), qos=1)

def main():
    """Run the bridge."""
    try:
        # Get read interval from environment or use default
        read_interval = int(os.environ.get("READ_INTERVAL", 20))
        
        # Create and start bridge
        bridge = SoilSensorBridge(
            mqtt_config=MQTT_CONFIG,
            read_interval=read_interval
        )
        
        bridge.start()
        
    except Exception as e:
        logger.error(f"Bridge error: {e}")

if __name__ == "__main__":
    main() 