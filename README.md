# Secret Garden

A Python library for managing garden sensors using Modbus RTU protocol over both serial and MQTT connections.

## Features

- 🌱 Support for multiple sensor types:
  - Soil sensor (moisture, temperature, EC, pH, NPK)
  - Air environment sensor (humidity, temperature, CO2, light)
- 🔌 Flexible communication:
  - Direct serial (RS485) connection
  - MQTT bridge for remote access
- 🛠 Advanced features:
  - Configuration-driven sensor definitions
  - Composite register reading for better performance
  - Comprehensive debugging tools
  - Support for multiple sensors on the same bus
- 📊 Data handling:
  - Automatic scaling and unit conversion
  - Support for various data types (INT16, UINT16, FLOAT32)
  - Proper handling of signed values
- ✨ Developer friendly:
  - Clean, layered architecture
  - Extensive documentation
  - Full test coverage
  - Type hints throughout

## Installation

1. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows
```

2. Install the package:
```bash
pip install -r requirements.txt
pip install -e .
```

## Quick Start

### Using a Soil Sensor via Serial

```python
from src.plugins.soil import SoilSensor
from src.core.constants import CommType

# Create sensor instance
sensor = SoilSensor(
    modbus_type=CommType.SERIAL,
    port="/dev/ttyUSB0",
    baudrate=4800,
    unit_id=1  # Modbus slave ID
)

# Connect
sensor.modbus.connect()

try:
    # Read all parameters at once
    data = sensor.get_all()
    print(f"Temperature: {data['temperature']}°C")
    print(f"Moisture: {data['moisture']}%")
    print(f"EC: {data['ec']}us/cm")
    print(f"pH: {data['ph']}")
    
    # Read NPK values
    npk = sensor.get_npk()
    print(f"N: {npk['nitrogen']}mg/kg")
    print(f"P: {npk['phosphorus']}mg/kg")
    print(f"K: {npk['potassium']}mg/kg")
    
finally:
    sensor.modbus.disconnect()
```

### Using an Air Sensor via MQTT

```python
from src.plugins.air import AirSensor
from src.core.constants import CommType

# Create sensor instance
sensor = AirSensor(
    modbus_type=CommType.MQTT,
    unit_id=2,  # Modbus slave ID
    client_id="air_sensor_1",
    request_topic="garden/air/down",
    response_topic="garden/air/up",
    host="mqtt.example.com",
    port=1883,
    username="user",
    password="pass"
)

# Connect
sensor.modbus.connect()

try:
    # Read all parameters
    data = sensor.get_all()
    print(f"Temperature: {data['temperature']}°C")
    print(f"Humidity: {data['humidity']}%")
    print(f"CO2: {data['co2']}ppm")
    print(f"Light: {data['light']}lux")
    
finally:
    sensor.modbus.disconnect()
```

## Architecture

The library uses a three-layer architecture:

1. **Communication Layer** (`src/core/modbus.py`, `src/core/mqtt.py`)
   - Handles raw Modbus communication
   - Supports both serial and MQTT transport
   - Manages connections and data transfer

2. **Base Layer** (`src/core/sensor.py`)
   - Provides common sensor functionality
   - Handles register reading and writing
   - Manages sensor configuration

3. **Sensor Layer** (`src/plugins/`)
   - Implements specific sensor types
   - Defines register maps and data processing
   - Provides high-level sensor methods

## Examples

Check the `examples/` directory for more detailed examples:

- `soil_sensor_example.py`: Basic soil sensor usage
- `air_mqtt_example.py`: Air sensor with MQTT
- `mqtt_bridge_example.py`: MQTT bridge implementation
- `debug_tools_example.py`: Using debugging utilities
- `sensor_monitor.py`: Continuous monitoring example

## Development

### Running Tests

```bash
python run_tests.py
```

### Code Style

The project follows PEP 8 guidelines. Key points:
- Use type hints
- Document all public methods
- Keep methods focused and small
- Use constants for magic values

## Supported Hardware

### Soil Sensor
- Protocol: Modbus RTU
- Baud Rate: 4800
- Parameters:
  - Moisture: 0-100%
  - Temperature: -40 to 100°C
  - EC: 0-5000us/cm
  - pH: 0-14
  - NPK: 0-1999mg/kg

### Air Environment Sensor
- Protocol: Modbus RTU
- Baud Rate: 2400/4800/9600
- Parameters:
  - Humidity: 0-100%
  - Temperature: -40 to 100°C
  - CO2: 0-5000ppm
  - Light: 0-200000lux

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request 