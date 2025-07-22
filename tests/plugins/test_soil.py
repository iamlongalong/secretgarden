"""
Tests for soil sensor plugin functionality.
"""
import unittest
from unittest.mock import MagicMock, patch

from src.core.constants import (CommType, ModbusBaudRate, ModbusDataType,
                              ModbusFunction, SoilRegister)
from src.plugins.soil import SOIL_SENSOR_CONFIG, SoilSensor

class TestSoilSensor(unittest.TestCase):
    """Test SoilSensor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sensor with mocked modbus
        self.sensor = SoilSensor(
            modbus_type=CommType.SERIAL,
            port="/dev/ttyUSB0",
            baudrate=ModbusBaudRate.BAUD_4800
        )
        self.sensor.modbus = MagicMock()
        
    def test_config_validation(self):
        """Test sensor configuration."""
        # Test default config
        self.assertEqual(self.sensor.name, SOIL_SENSOR_CONFIG["name"])
        self.assertEqual(
            self.sensor.registers["moisture"]["reg"],
            SoilRegister.MOISTURE
        )
        
    def test_get_moisture(self):
        """Test getting moisture value."""
        # Setup mock
        self.sensor.read_register = MagicMock(return_value=65.8)
        
        # Test
        result = self.sensor.get_moisture()
        self.assertAlmostEqual(result, 65.8, places=1)
        self.sensor.read_register.assert_called_with("moisture")
        
    def test_get_temperature(self):
        """Test getting temperature value."""
        # Setup mock
        self.sensor.read_register = MagicMock(return_value=-10.1)
        
        # Test
        result = self.sensor.get_temperature()
        self.assertAlmostEqual(result, -10.1, places=1)
        self.sensor.read_register.assert_called_with("temperature")
        
    def test_get_all(self):
        """Test getting all parameters."""
        # Setup mock
        expected = {
            "moisture": 65.8,
            "temperature": -10.1,
            "ec": 1000,
            "ph": 5.6
        }
        self.sensor.read_composite = MagicMock(return_value=expected)
        
        # Test
        result = self.sensor.get_all()
        self.assertEqual(result, expected)
        self.sensor.read_composite.assert_called_with("all")
        
    def test_get_npk(self):
        """Test getting NPK values."""
        # Setup mock
        expected = {
            "nitrogen": 100,
            "phosphorus": 200,
            "potassium": 300
        }
        self.sensor.read_multiple = MagicMock(return_value=expected)
        
        # Test
        result = self.sensor.get_npk()
        self.assertEqual(result, expected)
        self.sensor.read_multiple.assert_called_with(
            ["nitrogen", "phosphorus", "potassium"]
        )
        
    def test_calibrate_temperature(self):
        """Test temperature calibration."""
        self.sensor.calibrate_temperature(25.5)
        self.sensor.modbus.write_register.assert_called_once_with(
            SoilRegister.TEMP_CAL,
            255  # 25.5 * 10
        )
        
    def test_calibrate_moisture(self):
        """Test moisture calibration."""
        self.sensor.calibrate_moisture(30.0)
        self.sensor.modbus.write_register.assert_called_once_with(
            SoilRegister.MOISTURE_CAL,
            300  # 30.0 * 10
        )
        
    def test_calibrate_ec(self):
        """Test EC calibration."""
        self.sensor.calibrate_ec(1000)
        self.sensor.modbus.write_register.assert_called_once_with(
            SoilRegister.EC_CAL,
            1000
        )
        
    def test_calibrate_ph(self):
        """Test pH calibration."""
        self.sensor.calibrate_ph(7.0)
        self.sensor.modbus.write_register.assert_called_once_with(
            SoilRegister.PH_CAL,
            70  # 7.0 * 10
        )
        
    def test_settings(self):
        """Test device settings."""
        # Test setting address
        self.sensor.set_address(2)
        self.sensor.modbus.write_register.assert_called_with(
            SoilRegister.ADDRESS,
            2
        )
        
        # Test invalid address
        with self.assertRaises(ValueError):
            self.sensor.set_address(0)
        with self.assertRaises(ValueError):
            self.sensor.set_address(255)
            
        # Test setting baudrate
        self.sensor.set_baudrate(ModbusBaudRate.BAUD_9600)
        self.sensor.modbus.write_register.assert_called_with(
            SoilRegister.BAUDRATE,
            2  # Code for 9600 baud
        )
        
        # Test invalid baudrate
        with self.assertRaises(ValueError):
            self.sensor.set_baudrate("invalid")

if __name__ == '__main__':
    unittest.main() 