# INA238 Python Library

## Introduction

The INA238 Python Library provides a user-friendly interface for interacting with the INA238 sensor over I2C. The library allows for easy configuration and data acquisition, supporting various settings for voltage range, ADC resolution, and averaging samples.

If you have any questions, please contact the Repo-Owner.

## Repo-Owner
Luca-Timo

## Getting Started

Follow these steps to get the code up and running on your system:

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/INA238-python-library.git
   cd INA238-python-library
   ```

2. **Install the required Python packages:**
   ```bash
   pip install smbus
   ```

### Software Dependencies

- Python 3.x
- smbus library for I2C communication

## Usage Example

Here's an example of how to use the library:

```python
from ina238 import INA238

# Initialize the sensor
sensor = INA238(bus_num=1, addr=0x40, max_voltage=32, shunt_resistance=0.1, max_current=3.2)

# Configure the sensor
sensor.configure(voltage_range=INA238.RANGE_32V, gain=INA238.GAIN_1_40MV, bus_adc=INA238.ADC_12BIT, shunt_adc=INA238.ADC_12BIT)

# Read values
print("Bus Voltage: {:.2f} V".format(sensor.voltage()))
print("Supply Voltage: {:.2f} V".format(sensor.supply_voltage()))
print("Shunt Voltage: {:.2f} mV".format(sensor.shunt_voltage()))
print("Current: {:.2f} mA".format(sensor.current()))
print("Power: {:.2f} mW".format(sensor.power()))
print("Temperature: {:.2f} °C".format(sensor.get_temperature()))
```

### API Overview

#### Initialization

```python
sensor = INA238(bus_num=1, addr=0x40, max_voltage=32, shunt_resistance=0.1, max_current=3.2)
```
- `bus_num`: The I2C bus number (default is 10).
- `addr`: The I2C address of the INA238 sensor (default is 0x40).
- `max_voltage`: The maximum expected bus voltage (default is 32V).
- `shunt_resistance`: The shunt resistor value in ohms (default is 0.1 ohms).
- `max_current`: The maximum expected current in amps (default is 3.2A).

#### Configuration

```python
sensor.configure(voltage_range=INA238.RANGE_32V, gain=INA238.GAIN_1_40MV, bus_adc=INA238.ADC_12BIT, shunt_adc=INA238.ADC_12BIT)
```
- `voltage_range`: The voltage range setting (16V or 32V).
- `gain`: The gain setting for the shunt voltage.
- `bus_adc`: The ADC resolution/averaging for the bus voltage.
- `shunt_adc`: The ADC resolution/averaging for the shunt voltage.

#### Reading Values

```python
bus_voltage = sensor.voltage()
supply_voltage = sensor.supply_voltage()
shunt_voltage = sensor.shunt_voltage()
current = sensor.current()
power = sensor.power()
temperature = sensor.get_temperature()
```

- `voltage()`: Returns the bus voltage in volts (V).
- `supply_voltage()`: Returns the supply voltage (bus voltage + shunt voltage) in volts (V).
- `shunt_voltage()`: Returns the shunt voltage in millivolts (mV).
- `current()`: Returns the current in milliamps (mA).
- `power()`: Returns the power consumption in milliwatts (mW).
- `get_temperature()`: Returns the temperature in degrees Celsius (°C).

### Error Handling

The library raises a `DeviceRangeError` if there is an overflow condition when reading the current or power values. Ensure to handle this exception in your code:

```python
try:
    current = sensor.current()
    power = sensor.power()
except DeviceRangeError as e:
    print(f"Error: {e}")
```

## Build and Test

To build and test the library, follow these steps:

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

2. **Install dependencies:**
   ```bash
   pip install smbus
   ```

3. **Run tests:**
   Ensure that the INA238 sensor is connected to your system correctly and run the example script to verify the functionality.

After a release, new contributions are only allowed in new branches. After the modifications have been checked by a second person, a new release will be created.

## Contribute

We welcome contributions from everyone. To contribute to this repository, follow these guidelines:

1. **Fork the repository.**
2. **Create a new branch for your changes:**
   ```bash
   git checkout -b my-feature-branch
   ```

3. **Make your changes and commit them with clear messages:**
   ```bash
   git commit -m "Description of my changes"
   ```

4. **Push your changes to your forked repository:**
   ```bash
   git push origin my-feature-branch
   ```

5. **Create a pull request** to merge your changes into the main repository.

If you notice any errors and are unable to correct them, please create an issue in the GitHub repository.

For more information on creating good readme files, refer to the following [guidelines](https://docs.microsoft.com/en-us/azure/devops/repos/git/create-a-readme?view=azure-devops). You can also seek inspiration from the below readme files:
- [ASP.NET Core](https://github.com/aspnet/Home)
- [Visual Studio Code](https://github.com/Microsoft/vscode)
- [Chakra Core](https://github.com/Microsoft/ChakraCore)

## To Do's:
- [ ] Add more configuration options.
- [ ] Improve error handling and documentation.
```

This documentation provides a comprehensive guide on how to use the INA238 Python library, including installation, configuration, usage examples, and contribution guidelines.
