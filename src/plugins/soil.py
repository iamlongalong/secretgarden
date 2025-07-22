"""
Soil sensor implementation.
"""
from typing import Any, Dict, List

from ..core.constants import (CommType, ModbusBaudRate, ModbusDataType,
                            ModbusFunction, RegisterType, ScaleFactor,
                            SoilRegister, Unit)
from ..core.modbus import ModbusAdapter
from ..core.sensor import BaseSensor

# Soil sensor configuration
SOIL_SENSOR_CONFIG = {
    "name": "soil",
    "type": "soil",
    "registers": {
        "moisture": {
            "reg": SoilRegister.MOISTURE,
            "type": ModbusDataType.INT16,
            "scale": ScaleFactor.MOISTURE,
            "signed": True,
            "unit": Unit.PERCENT
        },
        "temperature": {
            "reg": SoilRegister.TEMPERATURE,
            "type": ModbusDataType.INT16,
            "scale": ScaleFactor.TEMPERATURE,
            "signed": True,
            "unit": Unit.CELSIUS
        },
        "ec": {
            "reg": SoilRegister.EC,
            "type": ModbusDataType.UINT16,
            "scale": ScaleFactor.EC,
            "unit": Unit.US_CM
        },
        "ph": {
            "reg": SoilRegister.PH,
            "type": ModbusDataType.UINT16,
            "scale": ScaleFactor.PH,
            "unit": Unit.PH
        },
        "nitrogen": {
            "reg": SoilRegister.NITROGEN,
            "type": ModbusDataType.UINT16,
            "scale": ScaleFactor.NPK,
            "unit": Unit.MG_KG
        },
        "phosphorus": {
            "reg": SoilRegister.PHOSPHORUS,
            "type": ModbusDataType.UINT16,
            "scale": ScaleFactor.NPK,
            "unit": Unit.MG_KG
        },
        "potassium": {
            "reg": SoilRegister.POTASSIUM,
            "type": ModbusDataType.UINT16,
            "scale": ScaleFactor.NPK,
            "unit": Unit.MG_KG
        }
    },
    
    "composite": {
        "all": {
            "regs": [
                SoilRegister.MOISTURE,
                SoilRegister.TEMPERATURE,
                SoilRegister.EC,
                SoilRegister.PH
            ],
            "len": 4,
            "parse": "custom_soil_all"
        },
        "npk": {
            "regs": [
                SoilRegister.NITROGEN,
                SoilRegister.PHOSPHORUS,
                SoilRegister.POTASSIUM
            ],
            "len": 3,
            "parse": "custom_soil_npk"
        }
    }
}

class SoilSensor(BaseSensor):
    """Soil sensor implementation."""
    
    def __init__(
        self,
        modbus_type: CommType = CommType.SERIAL,
        unit_id: int = 1,
        **kwargs
    ):
        """Initialize soil sensor.
        
        Args:
            modbus_type: Communication type (SERIAL or MQTT)
            unit_id: Modbus unit/slave ID (1-254)
            **kwargs: Additional arguments for ModbusAdapter
        """
        # Create ModbusAdapter instance
        modbus_kwargs = kwargs.copy()  # Make a copy to avoid modifying the original
        modbus = ModbusAdapter(
            comm_type=modbus_type,
            **modbus_kwargs
        )
        
        # Create sensor config
        config = SOIL_SENSOR_CONFIG.copy()
        
        # Initialize base sensor with unit ID
        super().__init__(config, modbus, unit_id)
        
    def get_moisture(self) -> float:
        """Get soil moisture value.
        
        Returns:
            Moisture percentage value
        """
        return self.read_register("moisture")
        
    def get_temperature(self) -> float:
        """Get soil temperature value.
        
        Returns:
            Temperature in Celsius
        """
        return self.read_register("temperature")
        
    def get_conductivity(self) -> float:
        """Get soil electrical conductivity value.
        
        Returns:
            EC value in us/cm
        """
        return self.read_register("ec")
        
    def get_ph(self) -> float:
        """Get soil pH value.
        
        Returns:
            pH value
        """
        return self.read_register("ph")
        
    def get_all(self) -> Dict[str, float]:
        """Get all basic soil parameters.
        
        Returns:
            Dictionary with moisture, temperature, EC and pH values
        """
        return self.read_composite("all")
        
    def get_npk(self) -> Dict[str, float]:
        """Get NPK (Nitrogen, Phosphorus, Potassium) values.
        
        Returns:
            Dictionary with N, P, K values
        """
        return self.read_composite("npk")
        
    def calibrate_temperature(self, value: float) -> None:
        """Calibrate temperature reading.
        
        Args:
            value: Calibration value (x10)
        """
        self.modbus.write_register(SoilRegister.TEMP_CAL, int(value * 10))
        
    def calibrate_moisture(self, value: float) -> None:
        """Calibrate moisture reading.
        
        Args:
            value: Calibration value (x10)
        """
        self.modbus.write_register(SoilRegister.MOISTURE_CAL, int(value * 10))
        
    def calibrate_ec(self, value: float) -> None:
        """Calibrate EC reading.
        
        Args:
            value: Calibration value
        """
        self.modbus.write_register(SoilRegister.EC_CAL, int(value))
        
    def calibrate_ph(self, value: float) -> None:
        """Calibrate pH reading.
        
        Args:
            value: Calibration value (x10)
        """
        self.modbus.write_register(SoilRegister.PH_CAL, int(value * 10))
        
    def set_address(self, new_address: int) -> None:
        """Set sensor Modbus address.
        
        Args:
            new_address: New address (1-254)
        """
        if not 1 <= new_address <= 254:
            raise ValueError("Address must be between 1 and 254")
        self.modbus.write_register(SoilRegister.ADDRESS, new_address)
        
    def set_baudrate(self, baudrate: ModbusBaudRate) -> None:
        """Set sensor baudrate.
        
        Args:
            baudrate: Baudrate enum value
        """
        # Convert baudrate to code
        baudrate_map = {
            ModbusBaudRate.BAUD_2400: 0,
            ModbusBaudRate.BAUD_4800: 1,
            ModbusBaudRate.BAUD_9600: 2,
            ModbusBaudRate.BAUD_19200: 3,
            ModbusBaudRate.BAUD_38400: 4,
            ModbusBaudRate.BAUD_57600: 5,
            ModbusBaudRate.BAUD_115200: 6,
            ModbusBaudRate.BAUD_1200: 7
        }
        if baudrate not in baudrate_map:
            raise ValueError("Invalid baudrate")
        self.modbus.write_register(SoilRegister.BAUDRATE, baudrate_map[baudrate])
        
    def custom_soil_all(self, values: List[int]) -> Dict[str, float]:
        """Custom parser for all soil parameters.
        
        Args:
            values: Raw register values
            
        Returns:
            Processed values
        """
        moisture = values[0]
        if moisture > 32767:  # Handle signed value
            moisture -= 65536
        moisture *= ScaleFactor.MOISTURE
        
        temp = values[1]
        if temp > 32767:  # Handle signed value
            temp -= 65536
        temp *= ScaleFactor.TEMPERATURE
        
        ec = values[2] * ScaleFactor.EC
        ph = values[3] * ScaleFactor.PH
        
        return {
            "moisture": moisture,
            "temperature": temp,
            "ec": ec,
            "ph": ph
        }
        
    def custom_soil_npk(self, values: List[int]) -> Dict[str, float]:
        """Custom parser for NPK values.
        
        Args:
            values: Raw register values
            
        Returns:
            Processed values
        """
        return {
            "nitrogen": values[0] * ScaleFactor.NPK,
            "phosphorus": values[1] * ScaleFactor.NPK,
            "potassium": values[2] * ScaleFactor.NPK
        } 