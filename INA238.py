import smbus

class DeviceRangeError(Exception):
    pass

class INA238:
    # Register addresses for INA238 (as per datasheet)
    CONFIG_REGISTER = 0x00
    SHUNT_VOLTAGE_REGISTER = 0x01
    BUS_VOLTAGE_REGISTER = 0x02
    POWER_REGISTER = 0x03
    CURRENT_REGISTER = 0x04
    CALIBRATION_REGISTER = 0x05
    DIAG_ALRT_REGISTER = 0x06

    # Configuration constants (from datasheet or application requirements)
    RANGE_16V = 0x0000  # Example constant, INA238 supports up to 85V
    RANGE_32V = 0x0001  # Example constant, INA238 supports up to 85V

    GAIN_1_40MV = 0x0000
    GAIN_2_80MV = 0x0001
    GAIN_4_160MV = 0x0002
    GAIN_8_320MV = 0x0003

    ADC_9BIT = 0x0000
    ADC_10BIT = 0x0001
    ADC_11BIT = 0x0002
    ADC_12BIT = 0x0003
    ADC_2SAMP = 0x0009
    ADC_4SAMP = 0x000A
    ADC_8SAMP = 0x000B
    ADC_16SAMP = 0x000C
    ADC_32SAMP = 0x000D
    ADC_64SAMP = 0x000E
    ADC_128SAMP = 0x000F

    def __init__(self, i2c_bus=1, address=0x40):
        self.bus = smbus.SMBus(i2c_bus)
        self.address = address
        self.configure()

    def configure(self, voltage_range=RANGE_32V, gain=GAIN_1_40MV, bus_adc=ADC_12BIT, shunt_adc=ADC_12BIT):
        config = 0x0000
        config |= voltage_range
        config |= (gain << 1)
        config |= (bus_adc << 3)
        config |= (shunt_adc << 7)

        self.bus.write_word_data(self.address, INA238.CONFIG_REGISTER, config)
        self.bus.write_word_data(self.address, INA238.CALIBRATION_REGISTER, INA238.CALIBRATION_VALUE)

    def read_shunt_voltage(self):
        raw_value = self.bus.read_word_data(self.address, INA238.SHUNT_VOLTAGE_REGISTER)
        shunt_voltage = self._convert_raw_shunt_voltage(raw_value)
        return shunt_voltage

    def read_bus_voltage(self):
        raw_value = self.bus.read_word_data(self.address, INA238.BUS_VOLTAGE_REGISTER)
        bus_voltage = self._convert_raw_bus_voltage(raw_value)
        return bus_voltage

    def read_power(self):
        raw_value = self.bus.read_word_data(self.address, INA238.POWER_REGISTER)
        power = self._convert_raw_power(raw_value)
        return power

    def read_current(self):
        raw_value = self.bus.read_word_data(self.address, INA238.CURRENT_REGISTER)
        current = self._convert_raw_current(raw_value)
        return current

    def _convert_raw_shunt_voltage(self, raw_value):
        shunt_voltage = raw_value * 1.25e-6  # Convert to volts (example, based on 1.25 µV LSB)
        return shunt_voltage

    def _convert_raw_bus_voltage(self, raw_value):
        bus_voltage = raw_value * 3.125e-3  # Convert to volts (example, based on 3.125 mV LSB)
        return bus_voltage

    def _convert_raw_power(self, raw_value):
        power = raw_value * 25e-6  # Convert to watts (example, based on 25 µW LSB)
        return power

    def _convert_raw_current(self, raw_value):
        current = raw_value * 1e-6  # Convert to amps (example, based on 1 µA LSB)
        return current

    # INA219 compatible methods
    def voltage(self):
        return self.read_bus_voltage()

    def supply_voltage(self):
        return self.read_bus_voltage() + self.read_shunt_voltage()

    def current(self):
        current = self.read_current()
        if self.current_overflow():
            raise DeviceRangeError("Current overflow")
        return current * 1000  # Convert to mA

    def power(self):
        power = self.read_power()
        if self.current_overflow():
            raise DeviceRangeError("Current overflow")
        return power * 1000  # Convert to mW

    def shunt_voltage(self):
        shunt_voltage = self.read_shunt_voltage()
        if self.current_overflow():
            raise DeviceRangeError("Current overflow")
        return shunt_voltage * 1000  # Convert to mV

    def current_overflow(self):
        diag_alrt = self.bus.read_word_data(self.address, INA238.DIAG_ALRT_REGISTER)
        return bool(diag_alrt & 0x0001)  # Assuming overflow is indicated by the first bit

    def sleep(self):
        config = self.bus.read_word_data(self.address, INA238.CONFIG_REGISTER)
        config &= 0xFFF8  # Set MODE bits to 000 (shutdown)
        self.bus.write_word_data(self.address, INA238.CONFIG_REGISTER, config)

    def wake(self):
        config = self.bus.read_word_data(self.address, INA238.CONFIG_REGISTER)
        config |= 0x0007  # Set MODE bits to continuous mode
        self.bus.write_word_data(self.address, INA238.CONFIG_REGISTER, config)

    def reset(self):
        self.bus.write_word_data(self.address, INA238.CONFIG_REGISTER, 0x8000)  # Set RST bit to reset

    def is_conversion_ready(self):
        diag_alrt = self.bus.read_word_data(self.address, INA238.DIAG_ALRT_REGISTER)
        return bool(diag_alrt & 0x0008)  # Assuming CNVR bit is the 4th bit

# Usage example
# sensor = INA238()
# sensor.configure(voltage_range=INA238.RANGE_32V, gain=INA238.GAIN_1_40MV, bus_adc=INA238.ADC_12BIT, shunt_adc=INA238.ADC_12BIT)
# print("Bus Voltage: {:.2f} V".format(sensor.voltage()))
# print("Supply Voltage: {:.2f} V".format(sensor.supply_voltage()))
# print("Shunt Voltage: {:.2f} mV".format(sensor.shunt_voltage()))
# print("Current: {:.2f} mA".format(sensor.current()))
# print("Power: {:.2f} mW".format(sensor.power()))
# print("Current Overflow: {}".format(sensor.current_overflow()))
# sensor.sleep()
# sensor.wake()
# sensor.reset()
# print("Is Conversion Ready: {}".format(sensor.is_conversion_ready()))