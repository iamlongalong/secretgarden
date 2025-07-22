"""
Utility functions for Modbus debugging and data analysis.
"""
import binascii
import struct
import logging
from typing import Dict, List, Optional, Tuple, Union

from ..core.constants import (ModbusDataType, ModbusFunction, RegisterType,
                            ScaleFactor, SoilRegister, Unit)

logger = logging.getLogger(__name__)

class ModbusCommand:
    """Modbus command generator."""
    
    @staticmethod
    def read_holding_registers(
        address: int,
        count: int = 1,
        slave: int = 1
    ) -> bytes:
        """Generate read holding registers command.
        
        Args:
            address: Starting register address
            count: Number of registers to read
            slave: Slave address
            
        Returns:
            Command bytes
        """
        cmd = bytes([
            slave,  # Slave address
            ModbusFunction.READ_HOLDING_REGISTERS.value,  # Function code
            (address >> 8) & 0xFF,  # Register address high byte
            address & 0xFF,         # Register address low byte
            (count >> 8) & 0xFF,    # Register count high byte
            count & 0xFF            # Register count low byte
        ])
        return cmd + ModbusTools.calculate_crc(cmd)
        
    @staticmethod
    def write_single_register(
        address: int,
        value: int,
        slave: int = 1
    ) -> bytes:
        """Generate write single register command.
        
        Args:
            address: Register address
            value: Value to write
            slave: Slave address
            
        Returns:
            Command bytes
        """
        cmd = bytes([
            slave,  # Slave address
            ModbusFunction.WRITE_SINGLE_REGISTER.value,  # Function code
            (address >> 8) & 0xFF,  # Register address high byte
            address & 0xFF,         # Register address low byte
            (value >> 8) & 0xFF,    # Value high byte
            value & 0xFF            # Value low byte
        ])
        return cmd + ModbusTools.calculate_crc(cmd)

class ModbusTools:
    """Modbus protocol utilities."""
    
    @staticmethod
    def calculate_crc(data: bytes) -> bytes:
        """Calculate Modbus CRC16.
        
        Args:
            data: Data bytes
            
        Returns:
            CRC bytes (low byte, high byte)
        """
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return bytes([crc & 0xFF, (crc >> 8) & 0xFF])
        
    @staticmethod
    def verify_crc(data: bytes) -> bool:
        """Verify Modbus CRC16.
        
        Args:
            data: Data bytes including CRC
            
        Returns:
            True if CRC is valid
        """
        if len(data) < 3:
            return False
        received_crc = data[-2:]
        calculated_crc = ModbusTools.calculate_crc(data[:-2])
        return received_crc == calculated_crc
        
    @staticmethod
    def parse_response(data: bytes) -> Dict:
        """Parse Modbus response.
        
        Args:
            data: Response bytes
            
        Returns:
            Parsed response with fields:
            - slave_id: Slave ID
            - function: Function code
            - byte_count: Number of data bytes (for read functions)
            - data: Data bytes
            - crc: CRC bytes
        """
        if len(data) < 3:
            raise ValueError("Response too short")
            
        # Skip CRC check for now
        # if not ModbusTools.verify_crc(data):
        #     raise ValueError("Invalid CRC")
        
        # For read functions (0x03, 0x04), byte 3 is the byte count
        if data[1] in [ModbusFunction.READ_HOLDING_REGISTERS.value, 
                      ModbusFunction.READ_INPUT_REGISTERS.value]:
            byte_count = data[2]
            return {
                "slave_id": data[0],
                "function": data[1],
                "byte_count": byte_count,
                "data": data[3:3+byte_count],  # Use byte_count to extract data
                "crc": data[-2:]
            }
        # For write functions (0x06), data is 2 bytes (address) + 2 bytes (value)
        elif data[1] == ModbusFunction.WRITE_SINGLE_REGISTER.value:
            return {
                "slave_id": data[0],
                "function": data[1],
                "register_address": (data[2] << 8) | data[3],
                "register_value": (data[4] << 8) | data[5],
                "crc": data[-2:]
            }
        # For other functions or error responses
        else:
            return {
                "slave_id": data[0],
                "function": data[1],
                "data": data[2:-2],
                "crc": data[-2:]
            }
        
    @staticmethod
    def format_bytes(data: bytes) -> str:
        """Format bytes as hex string.
        
        Args:
            data: Bytes to format
            
        Returns:
            Formatted hex string
        """
        return " ".join(f"{b:02X}" for b in data)
        
    @staticmethod
    def parse_register_value(
        value: int,
        data_type: ModbusDataType,
        scale: float = 1.0,
        signed: bool = False
    ) -> Union[int, float]:
        """Parse register value.
        
        Args:
            value: Raw register value
            data_type: Data type
            scale: Scale factor
            signed: Whether value is signed
            
        Returns:
            Parsed value
        """
        if data_type == ModbusDataType.INT16:
            if signed and value > 32767:
                value -= 65536
            return value * scale
        elif data_type == ModbusDataType.UINT16:
            return value * scale
        else:
            return value * scale

class SoilSensorTools:
    """Soil sensor specific tools."""
    
    # Common command templates
    READ_ALL = ModbusCommand.read_holding_registers(
        SoilRegister.MOISTURE,  # Start from moisture
        4,                      # Read 4 registers (moisture, temp, ec, ph)
        1                       # Default slave ID
    )
    
    READ_NPK = ModbusCommand.read_holding_registers(
        SoilRegister.NITROGEN,  # Start from nitrogen
        3,                      # Read 3 registers (N, P, K)
        1                       # Default slave ID
    )
    
    @staticmethod
    def parse_raw_data(
        data: Union[bytes, str],
        register_type: Optional[str] = None
    ) -> Dict:
        """Parse raw sensor data.
        
        Args:
            data: Raw data bytes or hex string
            register_type: Register type for parsing
            
        Returns:
            Parsed data
        """
        if isinstance(data, str):
            # Convert hex string to bytes
            data = bytes.fromhex(data.replace(" ", ""))
            
        response = ModbusTools.parse_response(data)
        values = []
        
        # Extract register values
        for i in range(0, len(response["data"]), 2):
            value = (response["data"][i] << 8) | response["data"][i + 1]
            values.append(value)
            
        # Parse based on register type
        if register_type == "all":
            return {
                "moisture": values[0] * 0.1,  # Scale by 0.1
                "temperature": (values[1] - 65536 if values[1] > 32767 else values[1]) * 0.1,
                "ec": values[2],
                "ph": values[3] * 0.1
            }
        elif register_type == "npk":
            return {
                "nitrogen": values[0],
                "phosphorus": values[1],
                "potassium": values[2]
            }
        else:
            return {"values": values}
            
    @staticmethod
    def generate_command(
        command_type: str,
        **kwargs
    ) -> Tuple[bytes, str]:
        """Generate command bytes.
        
        Args:
            command_type: Command type
            **kwargs: Command parameters
            
        Returns:
            (command bytes, description)
        """
        if command_type == "read_all":
            return (SoilSensorTools.READ_ALL, "Read all parameters")
        elif command_type == "read_npk":
            return (SoilSensorTools.READ_NPK, "Read NPK values")
        elif command_type == "calibrate_ph":
            value = int(float(kwargs["value"]) * 10)
            cmd = ModbusCommand.write_single_register(
                SoilRegister.PH_CAL,
                value,
                kwargs.get("slave", 1)
            )
            return (cmd, f"Calibrate pH to {value/10}")
        else:
            raise ValueError(f"Unknown command type: {command_type}")
            
    @staticmethod
    def analyze_response(command: bytes, response: bytes) -> Dict:
        """Analyze command-response pair.
        
        Args:
            command: Command bytes
            response: Response bytes
            
        Returns:
            Analysis results
        """
        cmd_parsed = ModbusTools.parse_response(command)
        resp_parsed = ModbusTools.parse_response(response)
        
        return {
            "command": {
                "raw": ModbusTools.format_bytes(command),
                "slave_id": cmd_parsed["slave_id"],
                "function": cmd_parsed["function"],
                "data": ModbusTools.format_bytes(cmd_parsed["data"]),
                "crc_valid": ModbusTools.verify_crc(command)
            },
            "response": {
                "raw": ModbusTools.format_bytes(response),
                "slave_id": resp_parsed["slave_id"],
                "function": resp_parsed["function"],
                "data": ModbusTools.format_bytes(resp_parsed["data"]),
                "crc_valid": ModbusTools.verify_crc(response)
            }
        } 