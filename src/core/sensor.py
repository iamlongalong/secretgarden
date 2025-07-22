"""
Sensor management and base sensor implementation.
"""
import importlib
import logging
import os
from typing import Any, Dict, List, Optional, Type

import yaml

from .modbus import ModbusAdapter
from .constants import ModbusDataType, RegisterType

logger = logging.getLogger(__name__)

class BaseSensor:
    """Base class for all sensors."""
    
    def __init__(self, config: Dict[str, Any], modbus: ModbusAdapter, unit_id: int = 1):
        """Initialize sensor.
        
        Args:
            config: Sensor configuration dictionary containing:
                - name: Sensor name
                - type: Sensor type
                - registers: Dictionary of register configurations
                - composite: Optional dictionary of composite register groups
            modbus: ModbusAdapter instance for communication
            unit_id: Modbus unit/slave ID (1-254)
        """
        if not 1 <= unit_id <= 254:
            raise ValueError("Unit ID must be between 1 and 254")
            
        self.name = config["name"]
        self.type = config["type"]
        self.registers = config["registers"]
        self.composite = config.get("composite", {})
        self.modbus = modbus
        self.unit_id = unit_id
        
    def read_register(self, name: str) -> Any:
        """Read single register by name.
        
        Args:
            name: Register name from configuration
            
        Returns:
            Parsed register value
        """
        if name not in self.registers:
            raise ValueError(f"Unknown register: {name}")
            
        reg_config = self.registers[name]
        reg_addr = reg_config["reg"]
        reg_type = reg_config.get("type", ModbusDataType.UINT16)
        reg_scale = reg_config.get("scale", 1.0)
        reg_signed = reg_config.get("signed", False)
        
        # Read register with unit ID
        value = self.modbus.read_register(reg_addr, 1, self.unit_id)[0]
        
        # Scale value
        if reg_type == ModbusDataType.INT16 and reg_signed and value > 32767:
            value -= 65536
        return value * reg_scale
        
    def read_multiple(self, names: List[str]) -> Dict[str, Any]:
        """Read multiple registers by name.
        
        Args:
            names: List of register names
            
        Returns:
            Dictionary of register name to value
        """
        result = {}
        for name in names:
            result[name] = self.read_register(name)
        return result
        
    def read_composite(self, name: str) -> Dict[str, Any]:
        """Read composite register group.
        
        Args:
            name: Composite group name from configuration
            
        Returns:
            Dictionary of parsed values
        """
        if name not in self.composite:
            raise ValueError(f"Unknown composite group: {name}")
            
        comp_config = self.composite[name]
        start_reg = comp_config["regs"][0]
        reg_count = comp_config["len"]
        
        # Read registers with unit ID
        values = self.modbus.read_register(start_reg, reg_count, self.unit_id)
        
        # Parse based on custom function if specified
        if "parse" in comp_config:
            parse_func = getattr(self, comp_config["parse"])
            return parse_func(values)
            
        # Default parsing
        result = {}
        for i, reg in enumerate(comp_config["regs"]):
            reg_name = f"register_{reg:04X}"
            result[reg_name] = values[i]
        return result
        
    def _get_parser(self, parser_name: str):
        """Get parser function from plugins.
        
        Args:
            parser_name: Name of parser function
            
        Returns:
            Parser function
        """
        try:
            module_path = f"src.plugins.{self.name.lower()}"
            module = importlib.import_module(module_path)
            return getattr(module, parser_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load parser {parser_name}: {e}")
            return lambda x: x
            
class SensorManager:
    """Manager for sensor instances."""
    
    def __init__(self, config_dir: str):
        """Initialize sensor manager.
        
        Args:
            config_dir: Directory containing sensor configuration files
        """
        self.config_dir = config_dir
        self.sensors: Dict[str, BaseSensor] = {}
        self._load_configs()
        
    def _load_configs(self) -> None:
        """Load all sensor configurations from config directory."""
        if not os.path.exists(self.config_dir):
            logger.warning(f"Config directory not found: {self.config_dir}")
            return
            
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.yaml'):
                path = os.path.join(self.config_dir, filename)
                try:
                    with open(path, 'r') as f:
                        config = yaml.safe_load(f)
                    if not isinstance(config, dict):
                        logger.error(f"Invalid config format in {filename}")
                        continue
                    sensor_type = config.get('type', 'base').lower()
                    self.sensors[sensor_type] = self._create_sensor(sensor_type, config)
                except Exception as e:
                    logger.error(f"Error loading config {filename}: {e}")
                    
    def _create_sensor(
        self,
        sensor_type: str,
        config: Dict[str, Any]
    ) -> BaseSensor:
        """Create sensor instance from configuration.
        
        Args:
            sensor_type: Type of sensor to create
            config: Sensor configuration
            
        Returns:
            Sensor instance
        """
        # Try to load custom sensor class
        try:
            module_path = f"src.plugins.{sensor_type}"
            module = importlib.import_module(module_path)
            sensor_class = getattr(module, f"{sensor_type.capitalize()}Sensor")
        except (ImportError, AttributeError):
            logger.debug(f"No custom class for {sensor_type}, using BaseSensor")
            sensor_class = BaseSensor
            
        # Create ModbusAdapter instance
        modbus = ModbusAdapter(
            port=config['port'],
            address=config['address'],
            baudrate=config.get('baudrate', 4800)
        )
        
        return sensor_class(config, modbus)
        
    def get_sensor(self, sensor_type: str) -> BaseSensor:
        """Get sensor instance by type.
        
        Args:
            sensor_type: Type of sensor to get
            
        Returns:
            Sensor instance
            
        Raises:
            KeyError: If sensor type not found
        """
        if sensor_type not in self.sensors:
            raise KeyError(f"Unknown sensor type: {sensor_type}")
        return self.sensors[sensor_type] 