from __future__ import annotations

import time
import RPi.GPIO as GPIO

from shuttercontrol.config import SettingsGPIO


class GPIOBoard:

    def __init__(self, settings: SettingsGPIO) -> None:
        self.settings = settings

        self.pin_close = settings.pin_close
        self.pin_open = settings.pin_open
        self.actuation_duration = settings.actuation_duration

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

        GPIO.setup (settings.pin_open, GPIO.OUT)
        GPIO.output(settings.pin_open, GPIO.HIGH)
        GPIO.setup (settings.pin_close, GPIO.OUT)
        GPIO.output(settings.pin_close, GPIO.HIGH)        

    def trigger_pin(self, pin: int) -> None:
        GPIO.output(pin, GPIO.LOW)
        time.sleep(self.actuation_duration)
        GPIO.output(pin, GPIO.HIGH)

    def trigger_open(self) -> None:
        self.trigger_pin(self.pin_open)

    def trigger_close(self) -> None:
        self.trigger_pin(self.pin_close)
