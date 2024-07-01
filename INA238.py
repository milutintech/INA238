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

    def __init__(self, bus_num=DEFAULT_BUS, addr=0x40, max_voltage=32, shunt_resistance=0.1, max_current=3.2):
        self.bus = smbus.SMBus(bus_num)
        self.addr = addr
        self.max_voltage = max_voltage
        self.shunt_resistance = shunt_resistance
        self.max_current = max_current
        self.reset()
        self.configure()

    def write_register(self, reg, value):
        self.bus.write_word_data(self.addr, reg, value)

    def read_register(self, reg):
        return self.bus.read_word_data(self.addr, reg)

    def configure(self):
        voltage_range = 0x0000 if self.max_voltage <= 16 else 0x2000
        adc_range = 0x0000  # Assume a default ADC range, can be set based on actual requirements
        bus_adc = 0x0780  # Default 12-bit ADC
        shunt_adc = 0x0078  # Default 12-bit ADC

        config = voltage_range | adc_range
        adc_config = bus_adc | shunt_adc
        self.write_register(self.REG_CONFIG, config)
        self.write_register(self.REG_ADC_CONFIG, adc_config)

        self.calibrate(self.shunt_resistance)

    def calibrate(self, shunt_resistance):
        calibration_value = int(8192 / (shunt_resistance * 0.00512))
        self.write_register(self.REG_SHUNT_CAL, calibration_value)

    def voltage(self):
        return self.read_register(self.REG_VBUS) * 0.003125

    def shunt_voltage(self):
        raw_shunt_voltage = self.read_register(self.REG_VSHUNT)
        return raw_shunt_voltage * 0.00125 if raw_shunt_voltage & 0x8000 else raw_shunt_voltage * 0.005

    def current(self):
        current = self.read_register(self.REG_CURRENT) * 0.001
        if self.current_overflow():
            raise DeviceRangeError("Current overflow")
        return current

    def power(self):
        power = self.read_register(self.REG_POWER) * 0.001
        if self.current_overflow():
            raise DeviceRangeError("Current overflow")
        return power

    def supply_voltage(self):
        return self.voltage() + self.shunt_voltage()

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
        return (raw_temp >> 4) * 0.125  # Conversion factor: 125 m°C/LSB

    def set_overvoltage_threshold(self, threshold):
        self.write_register(self.REG_BOVL, int(threshold / 0.003125))  # Conversion factor: 3.125 mV/LSB

    def set_undervoltage_threshold(self, threshold):
        self.write_register(self.REG_BUVL, int(threshold / 0.003125))  # Conversion factor: 3.125 mV/LSB

    def set_power_limit(self, limit):
        self.write_register(self.REG_PWR_LIMIT, int(limit / (256 * 0.001)))  # Conversion factor: 256 * Power LSB

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