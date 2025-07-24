#!/usr/bin/env python3
"""
Complete soil and air monitoring system using Modbus TCP.
This example demonstrates:
1. Reading soil and air sensor data via Modbus TCP
2. Logging data to a CSV file
3. Publishing data to HTTP endpoint
"""
import csv
import logging
import os
import sys
import json
import time
import threading
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dotenv import load_dotenv

from src.core.constants import CommType, SoilRegister, Unit, DEFAULT_MODBUS_TCP_PORT, ModbusFunction
from src.plugins.soil import SoilSensor, SOIL_SENSOR_CONFIG
from src.plugins.air import AirSensor, AIR_SENSOR_CONFIG
from src.core.modbus import ModbusAdapter, ModbusTCPSource, ModbusDataSource
from pymodbus.client import ModbusTcpClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # 改为DEBUG级别
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# TCP Configuration from environment variables
TCP_CONFIG = {
    "host": os.environ.get("MODBUS_HOST", "192.168.2.73"),  # Replace with your Modbus TCP server IP
    "port": int(os.environ.get("MODBUS_PORT", 502)),        # Default Modbus TCP port
    "soil_unit_id": int(os.environ.get("SOIL_UNIT_ID", 2)), # Modbus unit/slave ID for soil sensor
    "air_unit_id": int(os.environ.get("AIR_UNIT_ID", 1))    # Modbus unit/slave ID for air sensor
}


class SoilAndAirMonitor:
    """Soil and air monitoring system using Modbus TCP."""
    
    def __init__(
        self,
        tcp_config: Dict,
        read_interval: int = 60,  # Read every 60 seconds
        api_url: str = None,      # HTTP API URL for sending data
    ):
        """Initialize monitor.
        
        Args:
            tcp_config: TCP configuration
            read_interval: Data reading interval in seconds
            api_url: URL for HTTP API endpoint
        """
        
        # 创建共享的Modbus TCP客户端
        self.tcp_client = ModbusTcpClient(
            host=tcp_config["host"],
            port=tcp_config["port"]
        )
        # 创建锁，确保同一时间只有一个请求在处理中
        self.modbus_lock = threading.Lock()
        
        # 创建ModbusTCPSource，使用共享客户端
        tcp_source = ModbusTCPSource(
            host=tcp_config["host"],
            port=tcp_config["port"],
            client=self.tcp_client
        )
        
        
        # 创建传感器实例，直接传入source参数
        self.soil_sensor = SoilSensor(
            unit_id=tcp_config["soil_unit_id"],
            source=tcp_source  # 通过kwargs传递source参数给ModbusAdapter
        )
        
        self.air_sensor = AirSensor(
            unit_id=tcp_config["air_unit_id"],
            source=tcp_source  # 通过kwargs传递source参数给ModbusAdapter
        )

        # Set decimal places for all readings
        self.soil_sensor.set_decimal_places(2)
        self.air_sensor.set_decimal_places(2)
        
        self.read_interval = read_interval
        self.host = tcp_config["host"]
        self.port = tcp_config["port"]
        self.api_url = api_url
        
    def start(self):
        """Start monitoring."""
        connected = False
        
        try:
            # 连接到Modbus TCP服务器
            logger.info(f"Connecting to Modbus TCP server at {self.host}:{self.port}...")
            if self.tcp_client.connect():
                connected = True
                logger.info("Connected to Modbus TCP server")
            else:
                logger.error("Failed to connect to Modbus TCP server")
                return
                
            logger.info(f"Reading interval: {self.read_interval} seconds")
            if self.api_url:
                logger.info(f"Sending data to HTTP endpoint: {self.api_url}")
            else:
                logger.warning("No API URL provided. Data will not be sent to HTTP endpoint.")
            
            # Start monitoring loop
            last_read = 0
            try:
                while True:
                    now = time.time()
                    if now - last_read >= self.read_interval:
                        self._read_and_process_data()
                        last_read = now
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                logger.info("Stopping monitoring")
                
        finally:
            if connected:
                logger.info("Disconnecting from Modbus TCP server...")
                try:
                    self.tcp_client.close()
                    logger.info("Disconnected from Modbus TCP server")
                except Exception as e:
                    logger.error(f"Error disconnecting: {e}")
            
    def _read_and_process_data(self):
        """Read, process, and log sensor data."""
        soil_data = {}
        air_data = {}
        
        # 读取土壤传感器数据
        try:
            soil_data = self.soil_sensor.read_composite("all")

            soild_temp_diff = os.environ.get("SOIL_TEMP_DIFF", 0)

            # 处理温度误差
            soil_data["temperature"] = soil_data["temperature"] + soild_temp_diff
            logger.info(
                f"Soil Data: "
                f"Moisture={soil_data['moisture']}%, "
                f"Temperature={soil_data['temperature']}°C, "
                f"EC={soil_data['ec']}us/cm, "
                f"pH={soil_data['ph']}"
            )
        except Exception as e:
            logger.error(f"Error reading soil sensor data: {e}")
            
        # 读取空气传感器数据
        try:
            air_data = self.air_sensor.read_composite("all")

            air_temp_diff = os.environ.get("AIR_TEMP_DIFF", 0)

            # 处理温度误差
            air_data["temperature"] = air_data["temperature"] + air_temp_diff
            logger.info(
                f"Air Data: "
                f"Humidity={air_data['humidity']}%, "
                f"Temperature={air_data['temperature']}°C, "
                f"CO2={air_data['co2']}ppm, "
                f"Light={air_data['light']}lux"
            )
        except Exception as e:
            logger.error(f"Error reading air sensor data: {e}")
        
        # Only proceed if we have at least some data
        if soil_data or air_data:
            # Add prefixes to distinguish data sources
            soil_data_with_prefix = {f"soil_{k}": v for k, v in soil_data.items()}
            air_data_with_prefix = {f"air_{k}": v for k, v in air_data.items()}
            
            # Combine data
            combined_data = {**soil_data_with_prefix, **air_data_with_prefix}
            
            # Send data via HTTP POST
            if self.api_url:
                try:
                    headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'SoilAndAirMonitor/1.0',
                        'Accept': '*/*'
                    }
                    
                    # 使用 data 参数而不是 json 参数，更接近 curl 的行为
                    data = json.dumps(combined_data)

                    response = requests.post(
                        url=self.api_url,
                        data=data,
                        headers=headers,
                        timeout=10,
                        proxies={'http': None, 'https': None}  # 明确禁用代理
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"Data sent to HTTP endpoint successfully")
                    else:
                        logger.error(f"Failed to send data to HTTP endpoint. Status code: {response.status_code}")
                except Exception as e:
                    logger.error(f"Error sending data to HTTP endpoint: {e}")


def main():
    """Run the soil and air monitoring system."""
    try:
        # Load environment variables from .env file
        load_dotenv()
        
        # Get API URL from environment variable with fallback
        api_url = os.environ.get('API_URL', "")
        
        # Get read interval from environment or use default
        read_interval = int(os.environ.get("READ_INTERVAL", 30))
        
        # Create and start monitor
        monitor = SoilAndAirMonitor(
            tcp_config=TCP_CONFIG,
            read_interval=read_interval,
            api_url=api_url
        )
        
        monitor.start()
        
    except Exception as e:
        logger.error(f"Monitor error: {e}")

if __name__ == "__main__":
    main()