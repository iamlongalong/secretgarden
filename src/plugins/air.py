"""
Air environment sensor implementation.
"""
from typing import Any, Dict, List

from ..core.constants import (AirRegister, CommType, ModbusBaudRate, ModbusDataType,
                          ModbusFunction, RegisterType, ScaleFactor, Unit)
from ..core.modbus import ModbusAdapter
from ..core.sensor import BaseSensor

# Air sensor configuration
AIR_SENSOR_CONFIG = {
    "name": "air",
    "type": "air",
    "registers": {
        "humidity": {
            "reg": AirRegister.HUMIDITY,
            "type": ModbusDataType.UINT16,
            "scale": ScaleFactor.HUMIDITY,
            "unit": Unit.PERCENT
        },
        "temperature": {
            "reg": AirRegister.TEMPERATURE,
            "type": ModbusDataType.INT16,
            "scale": ScaleFactor.TEMPERATURE,
            "signed": True,
            "unit": Unit.CELSIUS
        },
        "co2": {
            "reg": AirRegister.CO2,
            "type": ModbusDataType.UINT16,
            "scale": ScaleFactor.CO2,
            "unit": Unit.PPM
        },
        "light": {
            "reg": AirRegister.LIGHT,
            "type": ModbusDataType.UINT32,  # Special handling for 32-bit value
            "scale": ScaleFactor.LIGHT,
            "unit": Unit.LUX
        }
    },
    
    "composite": {
        "all": {
            "regs": [
                AirRegister.HUMIDITY,
                AirRegister.TEMPERATURE,
                AirRegister.CO2,
                AirRegister.LIGHT,
                AirRegister.LIGHT_LOW
            ],
            "len": 5,
            "parse": "custom_air_all"
        }
    }
}

class AirSensor(BaseSensor):
    """Air environment sensor implementation."""
    
    def __init__(
        self,
        modbus_type: CommType = CommType.SERIAL,
        unit_id: int = 1,
        **kwargs
    ):
        """Initialize air sensor.
        
        Args:
            modbus_type: Communication type (SERIAL or MQTT)
            unit_id: Modbus unit/slave ID (1-254)
            **kwargs: Additional arguments for ModbusAdapter
        """
        # Create ModbusAdapter instance
        modbus = ModbusAdapter(
            comm_type=modbus_type,
            **kwargs
        )
        
        # Create sensor config
        config = AIR_SENSOR_CONFIG.copy()
        
        # Initialize base sensor with unit ID
        super().__init__(config, modbus, unit_id)
        
    def get_humidity(self) -> float:
        """Get air humidity value.
        
        Returns:
            Humidity percentage value (0-100%)
        """
        return self.read_register("humidity")
        
    def get_temperature(self) -> float:
        """Get air temperature value.
        
        Returns:
            Temperature in Celsius (-40.0 to 100.0°C)
        """
        return self.read_register("temperature")
        
    def get_co2(self) -> float:
        """Get CO2 concentration value.
        
        Returns:
            CO2 concentration in PPM (0-5000)
        """
        return self.read_register("co2")
        
    def get_light(self) -> float:
        """Get light intensity value.
        
        Returns:
            Light intensity in lux (0-65535 or 0-200000)
        """
        # Read both high and low registers for full range
        values = self.modbus.read_register(AirRegister.LIGHT, 2)
        if len(values) != 2:
            raise ValueError("Failed to read light intensity")
            
        # Combine high and low values for full range
        return (values[0] << 16) | values[1]
        
    def get_all(self) -> Dict[str, float]:
        """Get all environment parameters.
        
        Returns:
            Dictionary with humidity, temperature, CO2 and light values
        """
        return self.read_composite("all")
        
    def calibrate_temperature(self, value: float) -> None:
        """Calibrate temperature reading.
        
        Args:
            value: Calibration value (-40.0 to 100.0°C)
        """
        if not -40.0 <= value <= 100.0:
            raise ValueError("Temperature must be between -40.0 and 100.0°C")
        self.modbus.write_register(AirRegister.TEMP_CAL, int(value * 10))
        
    def calibrate_humidity(self, value: float) -> None:
        """Calibrate humidity reading.
        
        Args:
            value: Calibration value (0-100%)
        """
        if not 0 <= value <= 100:
            raise ValueError("Humidity must be between 0 and 100%")
        self.modbus.write_register(AirRegister.HUMIDITY_CAL, int(value * 10))
        
    def calibrate_co2(self, value: float) -> None:
        """Calibrate CO2 reading.
        
        Args:
            value: Calibration value (-2000 to 2000)
        """
        if not -2000 <= value <= 2000:
            raise ValueError("CO2 calibration must be between -2000 and 2000")
        self.modbus.write_register(AirRegister.CO2_CAL, int(value))
        
    def calibrate_light(self, value: float) -> None:
        """Calibrate light intensity reading.
        
        Args:
            value: Calibration value (-32768 to 32767)
        """
        if not -32768 <= value <= 32767:
            raise ValueError("Light calibration must be between -32768 and 32767")
            
        # Split into high and low 16-bit values
        high = (int(value) >> 16) & 0xFFFF
        low = int(value) & 0xFFFF
        
        # Write both registers
        self.modbus.write_register(AirRegister.LIGHT_CAL, high)
        self.modbus.write_register(AirRegister.LIGHT_CAL_LOW, low)
        
    def set_address(self, new_address: int) -> None:
        """Set sensor Modbus address.
        
        Args:
            new_address: New address (1-254)
        """
        if not 1 <= new_address <= 254:
            raise ValueError("Address must be between 1 and 254")
        self.modbus.write_register(AirRegister.DEVICE_ADDR, new_address)
        
    def set_baudrate(self, baudrate: ModbusBaudRate) -> None:
        """Set sensor baudrate.
        
        Args:
            baudrate: Baudrate enum value
        """
        # Convert baudrate to code
        baudrate_map = {
            ModbusBaudRate.BAUD_2400: 0,
            ModbusBaudRate.BAUD_4800: 1,
            ModbusBaudRate.BAUD_9600: 2
        }
        if baudrate not in baudrate_map:
            raise ValueError("Invalid baudrate. Only 2400, 4800, and 9600 are supported")
        self.modbus.write_register(AirRegister.BAUD_RATE, baudrate_map[baudrate])
        
    def custom_air_all(self, values: List[int]) -> Dict[str, float]:
        """Custom parser for all air parameters.
        
        Args:
            values: Raw register values
            
        Returns:
            Processed values
        """
        humidity = values[0] * ScaleFactor.HUMIDITY
        
        temp = values[1]
        if temp > 32767:  # Handle signed value
            temp -= 65536
        temp *= ScaleFactor.TEMPERATURE
        
        co2 = values[2] * ScaleFactor.CO2
        
        # Combine high and low light values
        light = (values[3] << 16) | values[4]
        
        return {
            "humidity": humidity,
            "temperature": temp,
            "co2": co2,
            "light": light
        } 