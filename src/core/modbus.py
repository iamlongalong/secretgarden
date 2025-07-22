"""
Modbus protocol adapter supporting both serial and MQTT data sources.
"""
import logging
import struct
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusException

from .constants import (CommType, DEFAULT_BYTESIZE, DEFAULT_MQTT_PORT,
                      DEFAULT_MQTT_QOS, DEFAULT_PARITY, DEFAULT_STOPBITS,
                      DEFAULT_TIMEOUT, ModbusBaudRate, ModbusFunction,
                      ModbusDataType)
from .mqtt import MqttClient
from ..utils.modbus_tools import ModbusCommand, ModbusTools

logger = logging.getLogger(__name__)

class ModbusDataSource(ABC):
    """Abstract base class for Modbus data sources."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to data source."""
        pass
        
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from data source."""
        pass
        
    @abstractmethod
    def read_registers(
        self,
        address: int,
        count: int,
        unit: int,
        function_code: int = ModbusFunction.READ_HOLDING_REGISTERS
    ) -> List[int]:
        """Read registers from data source."""
        pass
        
    @abstractmethod
    def write_register(
        self,
        address: int,
        value: int,
        unit: int,
        function_code: int = ModbusFunction.WRITE_SINGLE_REGISTER
    ) -> None:
        """Write register to data source."""
        pass

class ModbusSerialSource(ModbusDataSource):
    """Modbus RTU serial data source."""
    
    def __init__(
        self,
        port: str,
        baudrate: ModbusBaudRate = ModbusBaudRate.BAUD_4800,
        bytesize: int = DEFAULT_BYTESIZE,
        parity: str = DEFAULT_PARITY,
        stopbits: int = DEFAULT_STOPBITS,
        timeout: float = DEFAULT_TIMEOUT
    ):
        """Initialize serial data source."""
        self.client = ModbusSerialClient(
            port=port,
            baudrate=baudrate.value,
            bytesize=bytesize,
            parity=parity,
            stopbits=stopbits,
            timeout=timeout,
            framer='rtu'
        )
        
    def connect(self) -> bool:
        return self.client.connect()
        
    def disconnect(self) -> None:
        self.client.close()
        
    def read_registers(
        self,
        address: int,
        count: int,
        unit: int,
        function_code: int = ModbusFunction.READ_HOLDING_REGISTERS
    ) -> List[int]:
        """Read registers from serial device."""
        try:
            if function_code == ModbusFunction.READ_HOLDING_REGISTERS:
                response = self.client.read_holding_registers(
                    address=address,
                    count=count,
                    slave=unit
                )
            elif function_code == ModbusFunction.READ_INPUT_REGISTERS:
                response = self.client.read_input_registers(
                    address=address,
                    count=count,
                    slave=unit
                )
            else:
                raise ValueError(f"Unsupported function code: {function_code}")
                
            if response and not response.isError():
                return response.registers
            raise ModbusException(f"Failed to read register {address}")
        except Exception as e:
            logger.error(f"Error reading register {address}: {e}")
            raise
            
    def write_register(
        self,
        address: int,
        value: int,
        unit: int,
        function_code: int = ModbusFunction.WRITE_SINGLE_REGISTER
    ) -> None:
        """Write register to serial device."""
        try:
            if function_code == ModbusFunction.WRITE_SINGLE_REGISTER:
                response = self.client.write_register(
                    address=address,
                    value=value,
                    slave=unit
                )
            elif function_code == ModbusFunction.WRITE_MULTIPLE_REGISTERS:
                response = self.client.write_registers(
                    address=address,
                    values=[value],
                    slave=unit
                )
            else:
                raise ValueError(f"Unsupported function code: {function_code}")
                
            if response and response.isError():
                raise ModbusException(f"Failed to write register {address}")
        except Exception as e:
            logger.error(f"Error writing register {address}: {e}")
            raise

class ModbusMqttSource(ModbusDataSource):
    """Modbus over MQTT data source."""
    
    def __init__(
        self,
        client_id: str,
        request_topic: str,
        response_topic: str,
        host: str = "localhost",
        port: int = DEFAULT_MQTT_PORT,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """Initialize MQTT data source.
        
        Args:
            client_id: MQTT client ID
            request_topic: Topic for sending requests
            response_topic: Topic for receiving responses
            host: MQTT broker host
            port: MQTT broker port
            username: Optional username for authentication
            password: Optional password for authentication
        """
        self.mqtt = MqttClient(
            client_id=client_id,
            host=host,
            port=port,
            username=username,
            password=password
        )
        self.request_topic = request_topic
        self.response_topic = response_topic
        self._last_response: Optional[bytes] = None
        
    def connect(self) -> bool:
        try:
            self.mqtt.connect()
            self.mqtt.subscribe(
                self.response_topic,
                self._handle_response
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
            
    def disconnect(self) -> None:
        self.mqtt.disconnect()
        
    def read_registers(
        self,
        address: int,
        count: int,
        unit: int,
        function_code: int = ModbusFunction.READ_HOLDING_REGISTERS
    ) -> List[int]:
        """Read registers via MQTT."""
        # Generate Modbus RTU request
        request = ModbusCommand.read_holding_registers(
            address=address,
            count=count,
            slave=unit
        )
        
        # Clear previous response
        self._last_response = None
        
        # Publish request
        self.mqtt.publish(
            self.request_topic,
            request,  # Send raw bytes
            qos=DEFAULT_MQTT_QOS
        )
        
        # Wait for response
        timeout = DEFAULT_TIMEOUT
        while timeout > 0 and self._last_response is None:
            time.sleep(0.1)
            timeout -= 0.1
            
        if self._last_response is None:
            raise ModbusException("Timeout waiting for MQTT response")
            
        response = self._last_response
        self._last_response = None
        
        # Parse response
        if not ModbusTools.verify_crc(response):
            raise ModbusException("Invalid CRC in response")
            
        parsed = ModbusTools.parse_response(response)
        if parsed["function"] & 0x80:
            raise ModbusException(f"Modbus error response: {parsed}")
            
        # Extract register values
        values = []
        data = parsed["data"]
        for i in range(0, len(data), 2):
            value = (data[i] << 8) | data[i + 1]
            values.append(value)
            
        return values
        
    def write_register(
        self,
        address: int,
        value: int,
        unit: int,
        function_code: int = ModbusFunction.WRITE_SINGLE_REGISTER
    ) -> None:
        """Write register via MQTT."""
        # Generate Modbus RTU request
        request = ModbusCommand.write_single_register(
            address=address,
            value=value,
            slave=unit
        )
        
        self._last_response = None
        
        self.mqtt.publish(
            self.request_topic,
            request,  # Send raw bytes
            qos=DEFAULT_MQTT_QOS
        )
        
        timeout = DEFAULT_TIMEOUT
        while timeout > 0 and self._last_response is None:
            time.sleep(0.1)
            timeout -= 0.1
            
        if self._last_response is None:
            raise ModbusException("Timeout waiting for MQTT response")
            
        response = self._last_response
        self._last_response = None
        
        # Verify response
        if not ModbusTools.verify_crc(response):
            raise ModbusException("Invalid CRC in response")
            
        parsed = ModbusTools.parse_response(response)
        if parsed["function"] & 0x80:
            raise ModbusException(f"Modbus error response: {parsed}")
            
    def _handle_response(self, topic: str, payload: bytes) -> None:
        """Handle MQTT response messages."""
        self._last_response = payload

class ModbusAdapter:
    """Modbus protocol adapter supporting multiple data sources."""
    
    def __init__(
        self,
        comm_type: CommType,
        **kwargs
    ):
        """Initialize Modbus adapter.
        
        Args:
            comm_type: Communication type (SERIAL or MQTT)
            **kwargs: Additional arguments for data source
        """
        if comm_type == CommType.SERIAL:
            self.source = ModbusSerialSource(**kwargs)
        elif comm_type == CommType.MQTT:
            self.source = ModbusMqttSource(**kwargs)
        else:
            raise ValueError(f"Unsupported communication type: {comm_type}")
            
    def connect(self) -> bool:
        """Connect to data source."""
        return self.source.connect()
        
    def disconnect(self) -> None:
        """Disconnect from data source."""
        self.source.disconnect()
        
    def read_register(
        self,
        register: int,
        count: int = 1,
        unit: Optional[int] = None,
        function_code: int = ModbusFunction.READ_HOLDING_REGISTERS
    ) -> List[int]:
        """Read register(s)."""
        return self.source.read_registers(register, count, unit or 1, function_code)
        
    def write_register(
        self,
        register: int,
        value: Union[int, float],
        unit: Optional[int] = None,
        function_code: int = ModbusFunction.WRITE_SINGLE_REGISTER
    ) -> None:
        """Write register."""
        if isinstance(value, float):
            value = int(value)
        self.source.write_register(register, value, unit or 1, function_code)
        
    def read_float(
        self,
        register: int,
        byte_order: str = '>f',
        unit: Optional[int] = None
    ) -> float:
        """Read float value from two consecutive registers."""
        values = self.read_register(register, 2, unit)
        bytes_val = struct.pack('>HH', values[0], values[1])
        return struct.unpack(byte_order, bytes_val)[0]
        
    def write_float(
        self,
        register: int,
        value: float,
        byte_order: str = '>f',
        unit: Optional[int] = None
    ) -> None:
        """Write float value to two consecutive registers."""
        bytes_val = struct.pack(byte_order, value)
        values = struct.unpack('>HH', bytes_val)
        self.write_register(register, values[0], unit)
        self.write_register(register + 1, values[1], unit)

    def read_registers_as_dict(
        self,
        registers: Dict[str, Dict[str, Any]],
        unit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read multiple registers and return as dictionary.
        
        Args:
            registers: Dictionary of register configurations
            unit: Unit ID (defaults to self.address)
            
        Returns:
            Dictionary of register names and values
        """
        result = {}
        for name, config in registers.items():
            reg = config['reg']
            length = config.get('len', 1)
            scale = config.get('scale', 1)
            signed = config.get('signed', False)
            
            try:
                values = self.read_register(reg, length, unit)
                
                if length == 1:
                    value = values[0]
                    if signed and value > 32767:
                        value -= 65536
                    value *= scale
                elif length == 2 and config.get('type') == 'float':
                    value = self.read_float(reg, unit=unit)
                else:
                    value = values
                    
                result[name] = value
            except Exception as e:
                logger.error(f"Error reading register {name}: {e}")
                result[name] = None
                
        return result 