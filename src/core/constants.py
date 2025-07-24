"""
Global constants for sensor configuration.
"""
from enum import Enum, auto
from typing import Dict, Final

# Communication constants
class CommType(Enum):
    """Communication type enumeration."""
    SERIAL = auto()
    MQTT = auto()
    TCP = auto()

# Modbus constants
class ModbusBaudRate(Enum):
    """Modbus baudrate enumeration."""
    BAUD_1200 = 1200
    BAUD_2400 = 2400
    BAUD_4800 = 4800
    BAUD_9600 = 9600
    BAUD_19200 = 19200
    BAUD_38400 = 38400
    BAUD_57600 = 57600
    BAUD_115200 = 115200

class ModbusDataType(Enum):
    """Modbus data type enumeration."""
    UINT16 = auto()
    INT16 = auto()
    FLOAT32 = auto()
    UINT32 = auto()  # For light intensity high/low bits

# Register type constants
class RegisterType(Enum):
    """Register type enumeration."""
    HOLDING = auto()
    INPUT = auto()
    COIL = auto()
    DISCRETE_INPUT = auto()

# Unit constants
class Unit(Enum):
    """Measurement unit enumeration."""
    PERCENT = "%"
    CELSIUS = "°C"
    US_CM = "us/cm"
    PH = "pH"
    MG_KG = "mg/kg"
    PPT = "ppt"
    PPM = "ppm"
    LUX = "lux"  # For light intensity

# Default values
DEFAULT_TIMEOUT: Final[float] = 10.0
DEFAULT_BYTESIZE: Final[int] = 8
DEFAULT_PARITY: Final[str] = 'N'
DEFAULT_STOPBITS: Final[int] = 1
DEFAULT_MQTT_PORT: Final[int] = 1883
DEFAULT_MQTT_QOS: Final[int] = 1
DEFAULT_MODBUS_TCP_PORT: Final[int] = 502

# Register addresses
class SoilRegister:
    """Soil sensor register addresses."""
    MOISTURE = 0x0000
    TEMPERATURE = 0x0001
    EC = 0x0002
    PH = 0x0003
    NITROGEN = 0x0004
    PHOSPHORUS = 0x0005
    POTASSIUM = 0x0006
    SALINITY = 0x0007
    TDS = 0x0008
    
    # Calibration registers
    TEMP_CAL = 0x0050
    MOISTURE_CAL = 0x0051
    EC_CAL = 0x0052
    PH_CAL = 0x0053
    
    # Settings registers
    ADDRESS = 0x07D0
    BAUDRATE = 0x07D1

    # Coefficients
    EC_TEMP_COEF = 0x0022
    SALINITY_COEF = 0x0023
    TDS_COEF = 0x0024

# Modbus function codes
class ModbusFunction(Enum):
    """Modbus function codes."""
    READ_COILS = 0x01
    READ_DISCRETE_INPUTS = 0x02
    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_COIL = 0x05
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_COILS = 0x0F
    WRITE_MULTIPLE_REGISTERS = 0x10

# Scale factors
class ScaleFactor:
    """Scale factors for sensor readings."""
    TEMPERATURE = 0.1
    MOISTURE = 0.1
    PH = 0.1
    EC = 1.0
    NPK = 1.0
    HUMIDITY = 0.1        # 湿度值 0-1000 -> 0-100.0%
    CO2 = 1.0            # CO2值 0-5000 ppm
    LIGHT = 1.0          # 光照值

class AirRegister:
    """Air sensor register addresses."""
    # Basic parameters
    HUMIDITY = 0x0000      # 湿度值
    TEMPERATURE = 0x0001   # 温度值
    CO2 = 0x0002          # CO2浓度值
    LIGHT = 0x0003        # 光照值 (0-65535) 或高16位
    LIGHT_LOW = 0x0004    # 光照值低16位 (0-200000范围时)
    
    # Calibration values
    TEMP_CAL = 0x0050     # 温度校准值
    HUMIDITY_CAL = 0x0051 # 湿度校准值
    CO2_CAL = 0x0052      # CO2校准值
    LIGHT_CAL = 0x0053    # 光照校准值 (0-65535) 或高16位
    LIGHT_CAL_LOW = 0x0054 # 光照校准值低16位
    
    # Device settings
    DEVICE_ADDR = 0x07D0  # 设备地址
    BAUD_RATE = 0x07D1    # 设备波特率 