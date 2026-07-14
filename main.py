from machine import Pin, PWM, I2C

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