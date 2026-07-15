from machine import Pin, PWM, I2C
import ubluetooth
import uasyncio as asyncio
import neopixel
import time
import ustruct

#SETTINGS--------------------------------------------------------------------------------------------

# Левый драйвер (канал A)
PWMA_pin = 
AIN1_pin = 
AIN2_pin = 
# Правый драйвер (канал B)
PWMB_pin = 
BIN1_pin = 
BIN2_pin = 
# Общий STBY (включение драйверов)
STBY_pin = 

# === ПИНЫ ДЛЯ СЕРВОПРИВОДОВ ===
SERVO_GRIP =    # захват (открытие/закрытие)
SERVO_LIFT =    # подъём/опускание

# === ПИНЫ ДЛЯ ДАТЧИКА ЦВЕТА (I2C) ===
SCL_pin = 
SDA_pin = 

LED_pin = 
NUM_LEDS = 

SPEED_FWD =     
SPEED_TURN =    

GRIP_OPEN = 0      # захват полностью открыт
GRIP_CLOSE = 90    # захват закрыт 
LIFT_UP = 0        # груз поднят вверх
LIFT_DOWN = 90     # груз опущен вниз

BLE_NAME = "7777777"

# датчик цвета ----------------------------------------------------------------------------------------

class TCS34725:
    # Константы регистров
    _COMMAND_BIT = const(0x80)
    _COMMAND_AUTO_INC = const(0x20)
    _REG_ENABLE = const(0x00)
    _REG_ATIME = const(0x01)
    _REG_AILT = const(0x04)
    _REG_AIHT = const(0x06)
    _REG_ID = const(0x12)
    _REG_APERS = const(0x0C)
    _REG_CONTROL = const(0x0F)
    _REG_STATUS = const(0x13)
    _REG_CDATA = const(0x14)
    _REG_RDATA = const(0x16)
    _REG_GDATA = const(0x18)
    _REG_BDATA = const(0x1A)
    _ENABLE_AIEN = const(0x10)
    _ENABLE_WEN = const(0x08)
    _ENABLE_AEN = const(0x02)
    _ENABLE_PON = const(0x01)
    _GAINS = (1, 4, 16, 60)

    def __init__(self, i2c, address=0x29):
        self.i2c = i2c
        self.address = address
        self._active = False
        self._integration_time = 2.4
        sensor_id = self._read8(self._REG_ID)
        if sensor_id not in (0x4D, 0x10):
            raise RuntimeError("TCS34725 не найден (ID=0x{:02X})".format(sensor_id))
        self.integration_time(2.4)
        self.gain(4)
        self.active(False)

    def _read8(self, reg):
        reg |= self._COMMAND_BIT
        return self.i2c.readfrom_mem(self.address, reg, 1)[0]

    def _write8(self, reg, value):
        reg |= self._COMMAND_BIT
        self.i2c.writeto_mem(self.address, reg, ustruct.pack('<B', value))

    def _read16(self, reg):
        reg |= self._COMMAND_BIT
        data = self.i2c.readfrom_mem(self.address, reg, 2)
        return ustruct.unpack('<H', data)[0]

    def active(self, value=None):
        if value is None:
            return self._active
        value = bool(value)
        if self._active == value:
            return
        self._active = value
        enable = self._read8(self._REG_ENABLE)
        if value:
            self._write8(self._REG_ENABLE, enable | self._ENABLE_PON)
            time.sleep_ms(3)
            self._write8(self._REG_ENABLE, enable | self._ENABLE_PON | self._ENABLE_AEN)
        else:
            self._write8(self._REG_ENABLE, enable & ~(self._ENABLE_PON | self._ENABLE_AEN))

    def integration_time(self, value=None):
        if value is None:
            return self._integration_time
        value = min(614.4, max(2.4, value))
        cycles = int(value / 2.4)
        self._integration_time = cycles * 2.4
        self._write8(self._REG_ATIME, 256 - cycles)
        return self._integration_time

    def gain(self, value=None):
        if value is None:
            return self._GAINS[self._read8(self._REG_CONTROL) & 0x03]
        if value not in self._GAINS:
            raise ValueError("Усиление должно быть 1, 4, 16 или 60")
        self._write8(self._REG_CONTROL, self._GAINS.index(value))
        return value

    def _valid(self):
        return bool(self._read8(self._REG_STATUS) & 0x01)

    def read(self, raw=False):
        was_active = self.active()
        self.active(True)
        timeout = 500
        start = time.ticks_ms()
        while not self._valid():
            if time.ticks_diff(time.ticks_ms(), start) > timeout:
                self.active(was_active)
                raise RuntimeError("Таймаут TCS34725")
            time.sleep_ms(1)
        r = self._read16(self._REG_RDATA)
        g = self._read16(self._REG_GDATA)
        b = self._read16(self._REG_BDATA)
        c = self._read16(self._REG_CDATA)
        self.active(was_active)
        if raw:
            return (r, g, b, c)
        else:
            if c == 0:
                return (0.0, 0.0)
            x = -0.14282 * r + 1.54924 * g + -0.95641 * b
            y = -0.32466 * r + 1.57837 * g + -0.73191 * b
            z = -0.68202 * r + 0.77073 * g + 0.56332 * b
            d = x + y + z
            if d == 0:
                return (0.0, 0.0)
            n = (x / d - 0.3320) / (0.1858 - y / d)
            cct = 449.0 * n**3 + 3525.0 * n**2 + 6823.3 * n + 5520.33
            lux = y / 100.0
            return (cct, lux)

# все включаем ----------------------------------------------------------------------

pwm_left = PWM(Pin(PWMA_pin), freq=1900)
pwm_right = PWM(Pin(PWMB_pin), freq=1900)

ain1 = Pin(AIN1_pin, Pin.OUT)
ain2 = Pin(AIN2_pin, Pin.OUT)
bin1 = Pin(BIN1_pin, Pin.OUT)
bin2 = Pin(BIN2_pin, Pin.OUT)

stby = Pin(STBY_pin, Pin.OUT)
stby.value(1)   

i2c = I2C(0, scl=Pin(SCL_pin), sda=Pin(SDA_pin), freq=100000)
sensor = TCS34725(i2c)
sensor.active(True)
sensor.integration_time(100) 

ring = neopixel.NeoPixel(Pin(LED_pin), NUM_LEDS)

# движение ----------------------------------------------------------------------------------------

def stop():
    ain1.value(0); ain2.value(0)
    bin1.value(0); bin2.value(0)
    pwm_left.duty(0); pwm_right.duty(0)

def forward(speed=SPEED_FWD):
    ain1.value(1); ain2.value(0)   
    bin1.value(1); bin2.value(0)   
    pwm_left.duty(speed)
    pwm_right.duty(speed)

def backward(speed=SPEED_FWD):
    ain1.value(0); ain2.value(1)   
    bin1.value(0); bin2.value(1)  
    pwm_left.duty(speed)
    pwm_right.duty(speed)

def turn_left(speed=SPEED_TURN):
    ain1.value(0); ain2.value(1)  
    bin1.value(1); bin2.value(0)  
    pwm_left.duty(speed)
    pwm_right.duty(speed)

def turn_right(speed=SPEED_TURN):
    ain1.value(1); ain2.value(0) 
    bin1.value(0); bin2.value(1)  
    pwm_left.duty(speed)
    pwm_right.duty(speed)

# захват подъем -----------------------------------------------------------------------------------

def set_servo(pin, angle):
    duty = int(26 + (angle / 180) * 102)
    p = PWM(Pin(pin), freq=50)
    p.duty(duty)
    time.sleep_ms(250)   # время на отработку
    p.deinit()           # отключаем ШИМ (экономия энергии)

# датчик цвета -----------------------------------------------------------------------------------

def read_color():
    r, g, b, clear = sensor.read(raw=True)
    if clear == 0:
        return (0, 0, 0)
    maxv = max(r, g, b)
    if maxv > 0:
        r = int((r / maxv) * 30)
        g = int((g / maxv) * 30)
        b = int((b / maxv) * 30)
    return (r, g, b)

def show_color():
    col = read_color()
    ring.fill(col)
    ring.write()
    return col

# связь -------------------------------------------------------------------------------------------

_UART_SERVICE = ubluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
_RX_CHAR = ubluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
_TX_CHAR = ubluetooth.UUID("")

class BLE_UART:
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.connected = False
        self.ble.irq(self._irq)
        self._register()
        self._advertise()

    def _irq(self, event, data):
        if event == 1:          
            self.connected = True
        elif event == 2:        
            self.connected = False
            if self.callback:
                self.callback('S')   
            self._advertise()
        elif event == 3:        # получены данные
            _, data_type = data
            if data_type == self.rx_handle:
                raw = self.ble.gatts_read(self.rx_handle)
                cmd = raw.decode('utf-8').strip()
                if cmd and self.callback:
                    self.callback(cmd)

    def _register(self):
        rx = (_RX_CHAR, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_WRITE_NO_RESPONSE)
        tx = (_TX_CHAR, ubluetooth.FLAG_NOTIFY | ubluetooth.FLAG_READ)
        services = (_UART_SERVICE, (rx, tx),)
        ((self.tx_handle, self.rx_handle),) = self.ble.gatts_register_services((services,))
        self.ble.gatts_write(self.tx_handle, b'\x00')

    def _advertise(self):
        adv = b'\x02\x01\x06' + b'\x03\x03\xAA\xFE' + bytes([len(self.name)+1, 0x09]) + self.name.encode()
        self.ble.gap_advertise(100, adv)