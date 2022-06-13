# main

import busio
import time
import board
import atexit
import digitalio
import microcontroller
import wifi
import socketpool
import ipaddress

import neopixel
import adafruit_ds1307
import adafruit_dotstar
import adafruit_htu21d
import adafruit_mpl3115a2
#import adafruit_sps30.i2c
from adafruit_sps30.i2c import SPS30_I2C

from secrets import secrets

#############################################################################

# SPS30 limits I2C rate to 100kHz
i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
# I2C addresses found: 0xb, 0x40, 0x60, 0x68, 0x69

# Create the I2C sensor instances
ds1307  = adafruit_ds1307.DS1307(i2c)
htu21d  = adafruit_htu21d.HTU21D(i2c)
mpl3115 = adafruit_mpl3115a2.MPL3115A2(i2c)
#sps30   = adafruit_sps30.i2c(i2c, fp_mode=True)
sps30 = SPS30_I2C(i2c, fp_mode=True)

# dotstar strip on hardware SPI
NUM_DOTS = 4
dots = adafruit_dotstar.DotStar(board.SCK, board.MOSI, NUM_DOTS, brightness=0.1)

#############################################################################

__version__ = "0.0.0"
__repo__ = "https://github.com/mew-cx/CircuitPython_logger_rfc5424"

class Facility:
    "Syslog facilities, RFC5424 section 6.2.1"
    KERN, USER, MAIL, DAEMON, AUTH, SYSLOG, LPR, NEWS, UUCP, CRON, \
        AUTHPRIV, FTP = range(0,12)
    LOCAL0, LOCAL1, LOCAL2, LOCAL3, LOCAL4, LOCAL5, LOCAL6, \
        LOCAL7 = range(16, 24)

class Severity:
    "Syslog severities, RFC5424 section 6.2.1"
    EMERG, ALERT, CRIT, ERR, WARNING, NOTICE, INFO, DEBUG = range(0,8)

def FormatTimestamp(t):
    "RFC5424 section 6.2.3"
    result = "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z".format(
        t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
    return result

def FormatRFC5424(facility = Facility.USER,
                  severity = Severity.NOTICE,
                  timestamp = None,
                  hostname = None,
                  app_name = None,
                  procid = None,
                  msgid = None,
                  structured_data = None,
                  msg = None) :
    "RFC5424 section 6"

    # Sect 9.1: RFC5424's VERSION is "1"
    # Sect 6.2: HEADER MUST be ASCII
    header = "<{}>1 {} {} {} {} {} ".format(
        (facility << 3) + severity,
        timestamp or "-",
        hostname or "-",
        app_name or "-",
        procid or "-",
        msgid or "-")
    result = header.encode("ascii")

    # Sect 6.3: STRUCTURED-DATA has complicated encoding requirements,
    # so we require it to already be properly encoded.
    if not structured_data:
        structured_data = b"-"
    result += structured_data

    # Sect 6.4: # MSG SHOULD be UTF-8, but MAY be other encoding.
    # If using UTF-8, MSG MUST start with Unicode BOM.
    # Sect 6 ABNF: MSG is optional.
    #enc = "utf-8-sig"
    enc = "ascii"       # we're using ASCII
    if msg:
        result += b" " + msg.encode(enc)

    #print(repr(result))
    return result

#############################################################################

def InitializeDevices():
    # Turn off I2C VSENSOR to save power
    i2c_power = digitalio.DigitalInOut(board.I2C_POWER)
    i2c_power.switch_to_input()

    # Turn off onboard D13 red LED to save power
    led = digitalio.DigitalInOut(board.LED)
    led.direction = digitalio.Direction.OUTPUT
    led.value = False

    # Turn off onboard NeoPixel to save power
    pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
    pixel.brightness = 0.0
    pixel.fill((0, 0, 0))
    # TODO disable board.NEOPIXEL_POWER

    # Don't care about altitude, so use Standard Atmosphere [pascals]
    mpl3115.sealevel_pressure = 101325


@atexit.register
def shutdown():
    for dot in range(NUM_DOTS):
        dots[dot] = (0,0,0)

#############################################################################

def DayOfWeek(wday):
    # https://docs.python.org/3/library/time.html#time.struct_time
    # describes tm_wday as "range [0, 6], Monday is 0"
    return ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[wday]

#############################################################################
# main

while True:

    print()

    t = ds1307.datetime
    print("{} {}-{:02}-{:02}T{:02}:{:02}:{:02}Z".format(
        DayOfWeek(t.tm_wday),
        t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec))

    print("cpu: {:0.1f}C".format(microcontroller.cpu.temperature))

    print("htu21d : {:0.1f}C {:0.1f}%RH".format(
        htu21d.temperature,
        htu21d.relative_humidity
        ))

    print("mpl3115 : {:0.0f}pa {:0.0f}m {:0.1f}C".format(
        mpl3115.pressure,
        mpl3115.altitude,
        mpl3115.temperature
        ))

    try:
        x = sps30.read()
        #print(x)
    except RuntimeError as ex:
        print("Cant read SPS30, skipping: " + str(ex))
        continue

    print(
        x["tps"],"-",
        x["particles 05um"],
        x["particles 10um"],
        x["particles 25um"],
        x["particles 40um"],
        x["particles 100um"],"-",
        x["pm10 standard"],
        x["pm25 standard"],
        x["pm40 standard"],
        x["pm100 standard"]
        )

    time.sleep(5)

#############################################################################

# rfc5424_formatter.py

#############################################################################

while False:
    print("Concentration Units (standard):")
    print("\tPM 1.0: {}\tPM2.5: {}\tPM10: {}".format(
            aqdata["pm10 standard"], aqdata["pm25 standard"], aqdata["pm100 standard"]
        )
    )
    print("Concentration Units (number count):")
    print("\t0.3-0.5um  / cm3:", aqdata["particles 05um"])
    print("\t0.3-1.0um  / cm3:", aqdata["particles 10um"])
    print("\t0.3-2.5um  / cm3:", aqdata["particles 25um"])
    print("\t0.3-4.0um  / cm3:", aqdata["particles 40um"])
    print("\t0.3-10.0um / cm3:", aqdata["particles 100um"])
