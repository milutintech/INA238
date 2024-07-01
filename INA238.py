import smbus
import time

class DeviceRangeError(Exception):
    pass

class INA238:
    # INA238 Register Addresses
    REG_CONFIG = 0x00
    REG_ADC_CONFIG = 0x01
    REG_SHUNT_CAL = 0x02
    REG_VSHUNT = 0x04
    REG_VBUS = 0x05
    REG_DIETEMP = 0x06
    REG_CURRENT = 0x07
    REG_POWER = 0x08
    REG_DIAG_ALRT = 0x0B
    REG_SOVL = 0x0C
    REG_SUVL = 0x0D
    REG_BOVL = 0x0E
    REG_BUVL = 0x0F
    REG_TEMP_LIMIT = 0x10
    REG_PWR_LIMIT = 0x11
    REG_MANUFACTURER_ID = 0x3E
    REG_DEVICE_ID = 0x3F

    # Default values
    DEFAULT_BUS = 10

    # Constants for configuration
    # Voltage range (note: INA238 supports up to 85V, but we'll define these for compatibility)
    RANGE_16V = 0x0000  # Voltage range 0-16V
    RANGE_32V = 0x0010  # Voltage range 0-32V (INA238 can handle up to 85V, but needs correct setup)

    # Gain for the shunt voltage
    GAIN_1_40MV = 0x0000  # Gain 1, 40mV range
    GAIN_2_80MV = 0x0001  # Gain 2, 80mV range
    GAIN_4_160MV = 0x0002  # Gain 4, 160mV range
    GAIN_8_320MV = 0x0003  # Gain 8, 320mV range

    # ADC resolution and sampling
    ADC_9BIT = 0x0000    # 9-bit resolution
    ADC_10BIT = 0x0001   # 10-bit resolution
    ADC_11BIT = 0x0002   # 11-bit resolution
    ADC_12BIT = 0x0003   # 12-bit resolution
    ADC_2SAMP = 0x0009   # Averaging 2 samples at 12-bit resolution
    ADC_4SAMP = 0x000A   # Averaging 4 samples at 12-bit resolution
    ADC_8SAMP = 0x000B   # Averaging 8 samples at 12-bit resolution
    ADC_16SAMP = 0x000C  # Averaging 16 samples at 12-bit resolution
    ADC_32SAMP = 0x000D  # Averaging 32 samples at 12-bit resolution
    ADC_64SAMP = 0x000E  # Averaging 64 samples at 12-bit resolution
    ADC_128SAMP = 0x000F # Averaging 128 samples at 12-bit resolution

    def __init__(self, bus_num=DEFAULT_BUS, addr=0x40, max_voltage=32, shunt_resistance=0.1, max_current=3.2):
        self.bus = smbus.SMBus(bus_num)
        self.addr = addr
        self.max_voltage = max_voltage
        self.shunt_resistance = shunt_resistance
        self.max_current = max_current
        self.reset()
        self.configure()

    def write_register(self, reg, value):
        # Swap byte order for correct writing
        value_swapped = ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)
        self.bus.write_word_data(self.addr, reg, value_swapped)

    def read_register(self, reg):
        value = self.bus.read_word_data(self.addr, reg)
        # Swap byte order for correct reading
        return ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)

    def configure(self, voltage_range=RANGE_32V, gain=GAIN_8_320MV, bus_adc=ADC_12BIT, shunt_adc=ADC_12BIT):
        # Configure the CONFIG register based on the datasheet
        voltage_range_config = self.RANGE_32V if voltage_range == self.RANGE_32V else self.RANGE_16V
        conv_delay = 0x00  # Default conversion delay (0 ms)

        config = (conv_delay << 6) | voltage_range_config
        self.write_register(self.REG_CONFIG, config)

        # Configure the ADC_CONFIG register
        mode = 0x0F  # Continuous bus voltage, shunt voltage, and temperature measurement
        vbusct = bus_adc
        vshct = shunt_adc
        vtct = shunt_adc  # Use the same value for temperature conversion time
        avg = 0x00  # ADC sample averaging count: 1

        adc_config = (mode << 12) | (vbusct << 9) | (vshct << 6) | (vtct << 3) | avg
        self.write_register(self.REG_ADC_CONFIG, adc_config)

        self.calibrate()

    def calibrate(self):
        # Calculate the calibration value
        current_lsb = self.max_current / 32768
        calibration_value = int(0.00512 / (current_lsb * self.shunt_resistance))
        calibration_value &= 0x7FFF  # Ensure bit 15 is reserved (set to 0)
        self.write_register(self.REG_SHUNT_CAL, calibration_value)

    def voltage(self):
        raw_vbus = self.read_register(self.REG_VBUS)
        return raw_vbus * 0.003125  # Conversion factor: 3.125 mV/LSB

    def shunt_voltage(self):
        raw_shunt_voltage = self.read_register(self.REG_VSHUNT)
        return raw_shunt_voltage * 0.00000125  # Conversion factor: 1.25 µV/LSB

    def current(self):
        raw_current = self.read_register(self.REG_CURRENT)
        current_lsb = self.max_current / 32768
        current = raw_current * current_lsb
        if self.current_overflow():
            raise DeviceRangeError("Current overflow")
        return current * 1000  # Convert to mA

    def power(self):
        raw_power = self.read_register(self.REG_POWER)
        power_lsb = 25 * (self.max_current / 32768)  # 25 times current LSB
        power = raw_power * power_lsb
        if self.current_overflow():
            raise DeviceRangeError("Current overflow")
        return power * 1000  # Convert to mW

    def supply_voltage(self):
        return self.voltage() + (self.shunt_voltage() / 1000)  # Convert shunt voltage to V

    def current_overflow(self):
        diag_alrt = self.read_register(self.REG_DIAG_ALRT)
        return bool(diag_alrt & 0x0020)

    def sleep(self):
        config = self.read_register(self.REG_CONFIG)
        config &= ~0x8000
        self.write_register(self.REG_CONFIG, config)

    def wake(self):
        config = self.read_register(self.REG_CONFIG)
        config |= 0x8000
        self.write_register(self.REG_CONFIG, config)

    def reset(self):
        self.write_register(self.REG_CONFIG, 0x8000)
        time.sleep(0.1)  # Delay to ensure reset

    def is_conversion_ready(self):
        diag_alrt = self.read_register(self.REG_DIAG_ALRT)
        return bool(diag_alrt & 0x0002)

    def get_temperature(self):
        raw_temp = self.read_register(self.REG_DIETEMP)
        raw_temp &= 0xFFF0  # Ensure bits 0-3 are reserved (set to 0)
        return (raw_temp >> 4) * 0.125  # Conversion factor: 125 m°C/LSB

    def set_overvoltage_threshold(self, threshold):
        self.write_register(self.REG_BOVL, int(threshold / 0.003125))  # Conversion factor: 3.125 mV/LSB

    def set_undervoltage_threshold(self, threshold):
        self.write_register(self.REG_BUVL, int(threshold / 0.003125))  # Conversion factor: 3.125 mV/LSB

    def set_power_limit(self, limit):
        self.write_register(self.REG_PWR_LIMIT, int(limit / (256 * 0.001)))  # Conversion factor: 256 * Power LSB

    def get_manufacturer_id(self):
        return self.read_register(self.REG_MANUFACTURER_ID)

    def get_device_id(self):
        return self.read_register(self.REG_DEVICE_ID)

    def read_config(self):
        return self.read_register(self.REG_CONFIG)

    def read_adc_config(self):
        return self.read_register(self.REG_ADC_CONFIG)

    def read_shunt_cal(self):
        return self.read_register(self.REG_SHUNT_CAL)

    def read_vshunt(self):
        return self.read_register(self.REG_VSHUNT)

    def read_vbus(self):
        return self.read_register(self.REG_VBUS)

    def read_dietemp(self):
        return self.read_register(self.REG_DIETEMP)

    def read_diag_alrt(self):
        return self.read_register(self.REG_DIAG_ALRT)

    def set_shunt_overvoltage_limit(self, limit):
        self.write_register(self.REG_SOVL, int(limit / 0.00125))  # Conversion factor: 1.25 mV/LSB

    def set_shunt_undervoltage_limit(self, limit):
        self.write_register(self.REG_SUVL, int(limit / 0.00125))  # Conversion factor: 1.25 mV/LSB

    def set_temperature_limit(self, limit):
        self.write_register(self.REG_TEMP_LIMIT, int(limit / 0.125))  # Conversion factor: 125 m°C/LSB

# Usage example
# sensor = INA238(max_voltage=32, shunt_resistance=0.1, max_current=3.2)
# sensor.configure(voltage_range=INA238.RANGE_32V, gain=INA238.GAIN_1_40MV, bus_adc=INA238.ADC_12BIT
# print("Bus Voltage: {:.2f} V".format(sensor.voltage()))
# print("Supply Voltage: {:.2f} V".format(sensor.supply_voltage()))
# print("Shunt Voltage: {:.2f} mV".format(sensor.shunt_voltage()))
# print("Current: {:.2f} mA".format(sensor.current()))
# print("Power: {:.2f} mW".format(sensor.power()))
# print("Current Overflow: {}".format(sensor.current_overflow()))
# print("Temperature: {:.2f} °C".format(sensor.get_temperature()))
# sensor.sleep()
# sensor.wake()
# sensor.reset()
# print("Is Conversion Ready: {}".format(sensor.is_conversion_ready()))