"""
Tests for Modbus adapter functionality.
"""
import unittest
from unittest.mock import MagicMock, patch

from src.core.constants import CommType, ModbusBaudRate, ModbusFunction
from src.core.modbus import ModbusAdapter, ModbusMqttSource, ModbusSerialSource

class TestModbusSerialSource(unittest.TestCase):
    """Test ModbusSerialSource class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.port = "/dev/ttyUSB0"
        self.baudrate = ModbusBaudRate.BAUD_4800
        self.source = ModbusSerialSource(self.port, self.baudrate)
        
    @patch('pymodbus.client.ModbusSerialClient')
    def test_connect(self, mock_client):
        """Test connection establishment."""
        # Setup mock
        mock_client.return_value.connect.return_value = True
        self.source.client = mock_client.return_value
        
        # Test
        result = self.source.connect()
        self.assertTrue(result)
        mock_client.return_value.connect.assert_called_once()
        
    @patch('pymodbus.client.ModbusSerialClient')
    def test_read_registers(self, mock_client):
        """Test reading registers."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.registers = [1234, 5678]
        mock_response.isError.return_value = False
        mock_client.return_value.read_holding_registers.return_value = mock_response
        self.source.client = mock_client.return_value
        
        # Test
        result = self.source.read_registers(0x0000, 2, 1)
        self.assertEqual(result, [1234, 5678])
        mock_client.return_value.read_holding_registers.assert_called_with(
            address=0x0000,
            count=2,
            slave=1
        )
        
    @patch('pymodbus.client.ModbusSerialClient')
    def test_write_register(self, mock_client):
        """Test writing register."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.isError.return_value = False
        mock_client.return_value.write_register.return_value = mock_response
        self.source.client = mock_client.return_value
        
        # Test
        self.source.write_register(0x0000, 1234, 1)
        mock_client.return_value.write_register.assert_called_with(
            address=0x0000,
            value=1234,
            slave=1
        )

class TestModbusMqttSource(unittest.TestCase):
    """Test ModbusMqttSource class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.source = ModbusMqttSource(
            client_id="test",
            request_topic="test/request",
            response_topic="test/response"
        )
        self.source.mqtt = MagicMock()
        
    def test_connect(self):
        """Test MQTT connection."""
        # Setup mock
        self.source.mqtt.connect.return_value = None
        
        # Test
        result = self.source.connect()
        self.assertTrue(result)
        self.source.mqtt.connect.assert_called_once()
        self.source.mqtt.subscribe.assert_called_once_with(
            "test/response",
            self.source._handle_response
        )
        
    def test_read_registers(self):
        """Test reading registers via MQTT."""
        # Setup expected request/response
        expected_request = {
            "unit": 1,
            "function": ModbusFunction.READ_HOLDING_REGISTERS,
            "address": 0x0000,
            "count": 2
        }
        expected_response = {
            "registers": [1234, 5678]
        }
        
        # Mock MQTT publish and response
        def mock_publish(topic, payload, qos):
            self.source._handle_response("test/response", expected_response)
            
        self.source.mqtt.publish.side_effect = mock_publish
        
        # Test
        result = self.source.read_registers(0x0000, 2, 1)
        self.assertEqual(result, [1234, 5678])
        self.source.mqtt.publish.assert_called_with(
            "test/request",
            expected_request,
            qos=0
        )

class TestModbusAdapter(unittest.TestCase):
    """Test ModbusAdapter class."""
    
    def test_init_serial(self):
        """Test initialization with serial communication."""
        adapter = ModbusAdapter(
            comm_type=CommType.SERIAL,
            address=1,
            port="/dev/ttyUSB0",
            baudrate=ModbusBaudRate.BAUD_4800
        )
        self.assertIsInstance(adapter.source, ModbusSerialSource)
        
    def test_init_mqtt(self):
        """Test initialization with MQTT communication."""
        adapter = ModbusAdapter(
            comm_type=CommType.MQTT,
            address=1,
            client_id="test",
            request_topic="test/request",
            response_topic="test/response"
        )
        self.assertIsInstance(adapter.source, ModbusMqttSource)
        
    def test_invalid_comm_type(self):
        """Test initialization with invalid communication type."""
        with self.assertRaises(ValueError):
            ModbusAdapter(comm_type="invalid", address=1)
            
    @patch('src.core.modbus.ModbusSerialSource')
    def test_read_float(self, mock_source):
        """Test reading float value."""
        # Setup mock
        mock_source.return_value.read_registers.return_value = [0x4048, 0x0000]  # 3.125 in IEEE 754
        
        # Create adapter
        adapter = ModbusAdapter(
            comm_type=CommType.SERIAL,
            address=1,
            port="/dev/ttyUSB0"
        )
        adapter.source = mock_source.return_value
        
        # Test
        result = adapter.read_float(0x0000)
        self.assertAlmostEqual(result, 3.125, places=3)
        mock_source.return_value.read_registers.assert_called_with(
            0x0000, 2, 1, ModbusFunction.READ_HOLDING_REGISTERS
        )

if __name__ == '__main__':
    unittest.main() 