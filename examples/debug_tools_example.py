#!/usr/bin/env python3
"""
Example demonstrating the use of Modbus debugging tools.
"""
import logging
from typing import Dict

from src.core.constants import ModbusDataType, SoilRegister
from src.utils.modbus_tools import ModbusCommand, ModbusTools, SoilSensorTools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def print_analysis(title: str, data: Dict) -> None:
    """Print analysis results in a formatted way."""
    print(f"\n=== {title} ===")
    print("-" * 40)
    
    if "command" in data:
        print("Command:")
        for key, value in data["command"].items():
            print(f"  {key:15}: {value}")
            
    if "response" in data:
        print("\nResponse:")
        for key, value in data["response"].items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k:13}: {v}")
            else:
                print(f"  {key:15}: {value}")
                
    if "parsed_values" in data:
        print("\nParsed Values:")
        for key, value in data["parsed_values"].items():
            print(f"  {key:15}: {value}")
            
    print("-" * 40)

def example_1_parse_raw_data():
    """Example 1: Parse raw Modbus data."""
    print("\nExample 1: Parse raw Modbus data")
    
    # Example raw data (slave 1, function 3, reading 4 registers)
    # Response: Moisture=65.8%, Temp=-10.1°C, EC=1000us/cm, pH=5.6
    raw_data = "01 03 08 02 92 FF 9B 03 E8 00 38 57 B6"
    
    # Parse the data
    result = SoilSensorTools.parse_raw_data(raw_data, "all")
    print("\nParsed sensor data:")
    for key, value in result.items():
        print(f"{key:12}: {value}")

def example_2_generate_commands():
    """Example 2: Generate common commands."""
    print("\nExample 2: Generate common commands")
    
    # Generate some common commands
    commands = [
        ("read_all", {}),
        ("read_npk", {}),
        ("set_address", {"address": 2}),
        ("calibrate_temp", {"value": 25.5})
    ]
    
    for cmd_type, kwargs in commands:
        cmd, desc = SoilSensorTools.generate_command(cmd_type, **kwargs)
        print(f"\n{desc}:")
        print(f"Hex: {ModbusTools.format_bytes(cmd)}")

def example_3_analyze_communication():
    """Example 3: Analyze command-response pairs."""
    print("\nExample 3: Analyze command-response communication")
    
    # Example: Reading all parameters
    command = SoilSensorTools.READ_ALL
    response = bytes.fromhex("01 03 08 02 92 FF 9B 03 E8 00 38 57 B6")
    
    analysis = SoilSensorTools.analyze_response(command, response)
    print_analysis("Read All Parameters", analysis)
    
    # Example: Setting new address
    command = ModbusCommand.write_single_register(SoilRegister.ADDRESS, 2)
    response = bytes.fromhex("01 06 07 D0 00 02 08 86")
    
    analysis = SoilSensorTools.analyze_response(command, response)
    print_analysis("Set New Address", analysis)

def example_4_debug_unknown_data():
    """Example 4: Debug unknown register values."""
    print("\nExample 4: Debug unknown register values")
    
    # Example: Unknown register response
    raw_data = "01 03 04 0B B8 00 64 74 3D"
    
    # Parse without register type hint
    result = SoilSensorTools.parse_raw_data(raw_data)
    
    print("\nAnalyzing unknown register values:")
    for reg, values in result.items():
        print(f"\n{reg}:")
        for key, value in values.items():
            print(f"  {key:12}: {value}")

def main():
    """Run all examples."""
    try:
        example_1_parse_raw_data()
        example_2_generate_commands()
        example_3_analyze_communication()
        example_4_debug_unknown_data()
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")

if __name__ == "__main__":
    main() 