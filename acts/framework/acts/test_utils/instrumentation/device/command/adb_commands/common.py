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
            on_val='true', off_val='false')
    ]
)

mobile_data = DeviceBinaryCommandSeries(
    [
        DeviceSetting(GLOBAL, 'mobile_data'),
        DeviceState('svc data', on_val='enable', off_val='disable')
    ]
)

cellular = DeviceSetting(GLOBAL, 'cell_on')

preferred_network_mode = DeviceSetting(GLOBAL, 'preferred_network_mode')

wifi = DeviceBinaryCommandSeries(
    [
        DeviceSetting(GLOBAL, 'wifi_on'),
        DeviceState('svc wifi', on_val='enable', off_val='disable')
    ]
)

ethernet = DeviceState('ifconfig eth0', on_val='up', off_val='down')

bluetooth = DeviceState('service call bluetooth_manager', on_val='6',
                        off_val='8')

nfc = DeviceState('svc nfc', on_val='enable', off_val='disable')

# Disables the ModemService

disable_modem = 'pm disable com.google.android.apps.scone'

# Calling

disable_dialing = DeviceSetprop('ro.telephony.disable-call', on_val='true',
                                off_val='false')

# Screen

screen_adaptive_brightness = DeviceSetting(SYSTEM, 'screen_brightness_mode')

screen_brightness = DeviceSetting(SYSTEM, 'screen_brightness')

screen_always_on = DeviceState('svc power stayon', on_val='true',
                               off_val='false')

screen_timeout_ms = DeviceSetting(SYSTEM, 'screen_off_timeout')

# enables/disables showing notifications in ambient (mostly dark) mode.
doze_mode = DeviceSetting(SECURE, 'doze_enabled')

# enables/disables ambient mode (mostly dark) always showing the time
doze_always_on = DeviceSetting(SECURE, 'doze_always_on')

# Handles single tap gesture.
doze_tap_gesture = DeviceSetting(SECURE, 'doze_tap_gesture')

# Handles double tap gesture.
double_tap_gesture = DeviceSetting(SECURE, 'doze_pulse_on_double_tap')

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
                             on_val='+gps', off_val='-gps')

location_network = DeviceSetting(SECURE, 'location_providers_allowed',
                                 on_val='+network', off_val='-network')

# if set to true(3), enable location mode(set to high accuracy)
# if set to false(0), disable location mode(set to OFF)
location_mode = DeviceSetting(SECURE, 'location_mode', on_val='3', off_val='0')

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
