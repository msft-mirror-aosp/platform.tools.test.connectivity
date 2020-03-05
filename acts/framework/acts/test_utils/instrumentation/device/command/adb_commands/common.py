#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from acts.test_utils.instrumentation.device.command.adb_command_types \
    import DeviceBinaryCommandSeries
from acts.test_utils.instrumentation.device.command.adb_command_types import \
    DeviceSetprop
from acts.test_utils.instrumentation.device.command.adb_command_types import \
    DeviceSetting
from acts.test_utils.instrumentation.device.command.adb_command_types import \
    DeviceState

GLOBAL = 'global'
SYSTEM = 'system'
SECURE = 'secure'

"""Common device settings for power testing."""

# TODO: add descriptions to each setting

# Network/Connectivity

airplane_mode = DeviceBinaryCommandSeries(
    [
        DeviceSetting(GLOBAL, 'airplane_mode_on'),
        DeviceState(
            'am broadcast -a android.intent.action.AIRPLANE_MODE --ez state',
            'true', 'false')
    ]
)

mobile_data = DeviceBinaryCommandSeries(
    [
        DeviceSetting(GLOBAL, 'mobile_data'),
        DeviceState('svc data', 'enable', 'disable')
    ]
)

cellular = DeviceSetting(GLOBAL, 'cell_on')

preferred_network_mode = DeviceSetting(GLOBAL, 'preferred_network_mode')

wifi = DeviceBinaryCommandSeries(
    [
        DeviceSetting(GLOBAL, 'wifi_on'),
        DeviceState('svc wifi', 'enable', 'disable')
    ]
)

ethernet = DeviceState('ifconfig eth0', 'up', 'down')

bluetooth = DeviceState('service call bluetooth_manager', '6', '8')

nfc = DeviceState('svc nfc', 'enable', 'disable')

# Disables the ModemService

disable_modem = 'pm disable com.google.android.apps.scone'

# Calling

disable_dialing = DeviceSetprop('ro.telephony.disable-call', 'true', 'false')


# Screen

screen_adaptive_brightness = DeviceSetting(SYSTEM, 'screen_brightness_mode')

screen_brightness = DeviceSetting(SYSTEM, 'screen_brightness')

screen_always_on = DeviceState('svc power stayon', 'true', 'false')

screen_timeout_ms = DeviceSetting(SYSTEM, 'screen_off_timeout')

# enables/disables showing notifications in ambient (mostly dark) mode.
doze_mode = DeviceSetting(SECURE, 'doze_enabled')

# enables/disables ambient mode (mostly dark) always showing the time
doze_always_on = DeviceSetting(SECURE, 'doze_always_on')

#Disables single tap gesture for P19+ devices
doze_tap_gesture = DeviceSetting(SECURE, 'doze_tap_gesture')

wake_gesture = DeviceSetting(SECURE, 'wake_gesture_enabled')

screensaver = DeviceSetting(SECURE, 'screensaver_enabled')

notification_led = DeviceSetting(SYSTEM, 'notification_light_pulse')


# Audio

disable_audio = DeviceSetprop('ro.audio.silent')


# Accelerometer

auto_rotate = DeviceSetting(SYSTEM, 'accelerometer_rotation')


# Time

auto_time = DeviceSetting(GLOBAL, 'auto_time')

auto_timezone = DeviceSetting(GLOBAL, 'auto_timezone')

timezone = DeviceSetprop('persist.sys.timezone')


# Location

location_gps = DeviceSetting(SECURE, 'location_providers_allowed',
                             '+gps', '-gps')

location_network = DeviceSetting(SECURE, 'location_providers_allowed',
                                 '+network', '-network')

# if set to true(3), enable location mode(set to high accuracy)
# if set to false(0), disable location mode(set to OFF)
location_mode = DeviceSetting(SECURE, 'location_mode', '3', '0')

# Power

battery_saver_mode = DeviceSetting(GLOBAL, 'low_power')

battery_saver_trigger = DeviceSetting(GLOBAL, 'low_power_trigger_level')

enable_full_batterystats_history = 'dumpsys batterystats --enable full-history'

disable_doze = 'dumpsys deviceidle disable'


# Sensors

disable_sensors = 'dumpsys sensorservice restrict blah'

# Disable moisture detection

MOISTURE_DETECTION_SETTING_FILE = '/sys/class/power_supply/usb/moisture_detection_enabled'
disable_moisture_detection = 'echo 0 > %s' % MOISTURE_DETECTION_SETTING_FILE
stop_moisture_detection = 'setprop vendor.usb.contaminantdisable true'

## Ambient EQ: https://support.google.com/googlenest/answer/9137130?hl=en
ambient_eq = DeviceSetting(SECURE, 'display_white_balance_enabled')

# Disables System apps

disable_pixellogger = 'pm disable com.android.pixellogger'

# Miscellaneous

test_harness = DeviceBinaryCommandSeries(
    [
        DeviceSetprop('ro.monkey'),
        DeviceSetprop('ro.test_harness')
    ]
)

dismiss_keyguard = 'wm dismiss-keyguard'
