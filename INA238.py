import smbus
import time
from enum import Enum, IntEnum

class DeviceRangeError(Exception):
    pass

class Mode(IntEnum):
    """MODE field values in the ADC_CONFIG device register"""
    SHUTDOWN0 = 0x0
    TRIGGERED_VBUS = 0x1
    TRIGGERED_VSHUNT = 0x2
    TRIGGERED_VBUS_VSHUNT = 0x3
    TRIGGERED_DIETEMP = 0x4
    TRIGGERED_VBUS_DIETEMP = 0x5
    TRIGGERED_VSHUNT_DIETEMP = 0x6
    TRIGGERED_VBUS_VSHUNT_DIETEMP = 0x7
    SHUTDOWN8 = 0x8
    CONTINUOUS_VBUS = 0x9
    CONTINUOUS_VSHUNT = 0xA
    CONTINUOUS_VBUS_VSHUNT = 0xB
    CONTINUOUS_DIETEMP = 0xC
    CONTINUOUS_VBUS_DIETEMP = 0xD
    CONTINUOUS_VSHUNT_DIETEMP = 0xE
    CONTINUOUS_VBUS_VSHUNT_DIETEMP = 0xF

class ConversionTime(IntEnum):
    """Conversion time values in the VBUSCT, VSHCT, and VTCT fields of the ADC_CONFIG device register"""
    T_50_US = 0x0
    T_84_US = 0x1
    T_150_US = 0x2
    T_280_US = 0x3
    T_540_US = 0x4
    T_1052_US = 0x5
    T_2074_US = 0x6
    T_4120_US = 0x7

class Samples(IntEnum):
    """ADC sample averaging count values in the AVG field of the ADC_CONFIG device register"""
    AVG_1 = 0x0
    AVG_4 = 0x1
    AVG_16 = 0x2
    AVG_64 = 0x3
    AVG_128 = 0x4
    AVG_256 = 0x5
    AVG_512 = 0x6
    AVG_1024 = 0x7

class ADCRange(Enum):
    """ADCRANGE field values in the CONFIG device register"""
    HIGH = False  # ±163.84 mV
    LOW = True   # ±40.96 mV

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

    # Default I2C bus number
    DEFAULT_BUS = 10

    def __init__(self, bus_num=DEFAULT_BUS, addr=0x40, max_voltage=32, shunt_resistance=0.1, max_current=3.2):
        self.bus = smbus.SMBus(bus_num)
        self.addr = addr
        self.max_voltage = max_voltage
        self.shunt_resistance = shunt_resistance
        self.max_current = max_current
        self.reset()
        self.configure()
        self.calibrate()

    def write_register(self, reg, value):
        # Swap byte order for correct writing
        value_swapped = ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)
        self.bus.write_word_data(self.addr, reg, value_swapped)

    def read_register(self, reg):
        value = self.bus.read_word_data(self.addr, reg)
        # Swap byte order for correct reading
        return ((value & 0xFF) << 8) | ((value >> 8) & 0xFF)

    def configure(self, voltage_range=ADCRange.HIGH, mode=Mode.CONTINUOUS_VBUS_VSHUNT_DIETEMP, bus_adc=ConversionTime.T_1052_US, shunt_adc=ConversionTime.T_1052_US, avg=Samples.AVG_128):
        # Adjust voltage range based on the input
        voltage_range_config = 0x0010 if voltage_range == ADCRange.HIGH else 0x0000
        conv_delay = 0x00  # Default conversion delay (0 ms)

        # Set the configuration register with voltage range and conversion delay
        config = (conv_delay << 6) | voltage_range_config
        self.write_register(self.REG_CONFIG, config)

        # Set the ADC configuration register
        adc_config = (mode << 12) | (bus_adc << 9) | (shunt_adc << 6) | (avg << 3) | avg
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

    def get_device_id(self):
        """Read the device ID register"""
        return self.read_register(self.REG_DEVICE_ID)

    def read_config(self):
        return self.read_register(self.REG_CONFIG)

    def read_adc_config(self):
        return self.read_register(self.REG_ADC_CONFIG)

    def read_shunt_cal(self):
        return self.read_register(self.REG_SHUNT_CAL)

   
