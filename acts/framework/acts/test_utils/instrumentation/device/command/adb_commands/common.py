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

from acts.test_utils.instrumentation.device.command.adb_command_types import \
  DeviceBinaryCommandSeries
from acts.test_utils.instrumentation.device.command.adb_command_types import \
  DeviceSetprop
from acts.test_utils.instrumentation.device.command.adb_command_types import \
  DeviceSetting
from acts.test_utils.instrumentation.device.command.adb_command_types import \
  DeviceState
from acts.test_utils.instrumentation.device.command.adb_command_types import \
  GenericCommand

"""Common device settings for power testing."""

# Network/Connectivity

airplane_mode = DeviceBinaryCommandSeries(
    [
        DeviceSetting(DeviceSetting.GLOBAL, 'airplane_mode_on',
                      desc='Modifies the property that indicates whether '
                           'airplane mode is enabled. This command is always '
                           'used together with an activity manager broadcast.'),
        DeviceState(
            'am broadcast -a android.intent.action.AIRPLANE_MODE --ez state',
            on_val='true', off_val='false',
            desc='Modifies the airplane mode state. This is always done '
                 'after setting the airplane_mode_on global property.')
    ]
)

mobile_data = DeviceBinaryCommandSeries(
    [
        DeviceSetting(
            DeviceSetting.GLOBAL, 'mobile_data',
            desc='Modifies the property that indicates whether mobile data is '
                 'enabled. This is used always together with an svc data '
                 'command.'),
        DeviceState(
            'svc data', on_val='enable', off_val='disable',
            desc='Modifies the mobile data state. This is always done'
                 'after setting the mobile_data global property.')
    ]
)

cellular = DeviceSetting(
    DeviceSetting.GLOBAL, 'cell_on',
    desc='Modifies whether to enable the cellular radio.')

preferred_network_mode = DeviceSetting(
    DeviceSetting.GLOBAL, 'preferred_network_mode',
    desc='Sets the preferred network (lte/3g).')

wifi_global = DeviceSetting(DeviceSetting.GLOBAL, 'wifi_on',
                            desc='Modifies the property that indicates whether wifi '
                                 'is enabled. This is always used together with an'
                                 'svc wifi command.')

wifi_scan_always_enabled = DeviceSetting(DeviceSetting.GLOBAL, 'wifi_scan_always_enabled',
                                         desc='Modifies whether to enable the wifi scan always.')

wifi_state = DeviceState('svc wifi', on_val='enable', off_val='disable',
                         desc='Modifies the wifi state. This is always done after'
                              'setting the wifi_on global property.')

ethernet = DeviceState(
    'ifconfig eth0', on_val='up', off_val='down',
    desc='Modifies whether to enable ethernet.')

bluetooth = DeviceState(
    'service call bluetooth_manager',
    on_val='6',
    off_val='8',
    desc='Modifies whether bluetooth is enabled (6 means enabled, 8 disabled).'
         'TODO: add the source for these magic numbers. BluetoothAdapter '
         'http://shortn/_FTBWhfJJs7 makes reference to these enums '
         'http://shortn/_w9rcHX8jm4, but that doesn\'t seem to be the right '
         'source.')

nfc = DeviceState('svc nfc', on_val='enable', off_val='disable',
                  desc='Modifies whether to enable nfc.')

disable_modem = GenericCommand('pm disable com.google.android.apps.scone',
                               desc='Disables modem service.')

mobile_network_settings = GenericCommand('am start -n com.android.phone/'
                                         '.MobileNetworkSettings',
                                         desc='Opens network settings')

# Calling

disable_dialing = DeviceSetprop(
    'ro.telephony.disable-call', on_val='true', off_val='false',
    desc='Modifies whether to allow voice calls.')

# Screen

screen_adaptive_brightness = DeviceSetting(
    DeviceSetting.SYSTEM, 'screen_brightness_mode',
    desc='Modifies whether the adaptive brightness feature is enabled. Differs '
         'from ambient EQ modifies the color balance and this feature'
         'modifies the screen brightness. '
         'https://support.google.com/android/answer/9084191?hl=en '
         'http://shortn/_ptmpx4wuVW')

screen_brightness = DeviceSetting(DeviceSetting.SYSTEM, 'screen_brightness',
                                  desc='Sets the brightness level.')

screen_always_on = DeviceState(
    'svc power stayon', on_val='true', off_val='false',
    desc='Modifies whether the device should stay on while connected. '
         'http://shortn/_0DB29fy5HL')

screen_timeout_ms = DeviceSetting(
    DeviceSetting.SYSTEM, 'screen_off_timeout',
    desc='Sets the time to wait before turning the screen off.')

disable_doze = GenericCommand('dumpsys deviceidle disable',
                              desc = 'Disables device from going into doze mode')

doze_mode = DeviceSetting(
    DeviceSetting.SECURE, 'doze_enabled',
    desc='Modifies whether showing notifications in ambient (mostly dark) mode '
         'is enabled.')

doze_always_on = DeviceSetting(
    DeviceSetting.SECURE, 'doze_always_on',
    desc='Modifies whether ambient mode (mostly dark) is enabled. Ambient '
         'mode is the one where the device shows the time all the time.')

# Gestures
doze_pulse_on_pick_up = DeviceSetting(
    DeviceSetting.SECURE, 'doze_pulse_on_pick_up',
    desc='Modifies whether to enable gesture to wake up device when picked up.')

# TODO(mdb/android-system-infra): Add description
camera_double_tap_power_gesture_disabled = DeviceSetting(
    DeviceSetting.SECURE, 'camera_double_tap_power_gesture_disabled', desc=None)

# TODO(mdb/android-system-infra): Add description
camera_double_twist_to_flip_enabled = DeviceSetting(
    DeviceSetting.SECURE, 'camera_double_twist_to_flip_enabled', desc=None)

# TODO(mdb/android-system-infra): Add description
system_navigation_keys_enabled = DeviceSetting(
    DeviceSetting.SECURE, 'system_navigation_keys_enabled', desc=None)

# TODO(mdb/android-system-infra): Add description
camera_lift_trigger_enabled = DeviceSetting(
    DeviceSetting.SECURE, 'camera_lift_trigger_enabled', desc=None)

# TODO(mdb/android-system-infra): Add description
aware_enabled = DeviceSetting(
    DeviceSetting.SECURE, 'aware_enabled', desc=None)

# TODO(mdb/android-system-infra): Add description
doze_wake_screen_gesture = DeviceSetting(
    DeviceSetting.SECURE, 'doze_wake_screen_gesture', desc=None)

# TODO(mdb/android-system-infra): Add description
skip_gesture = DeviceSetting(
    DeviceSetting.SECURE, 'skip_gesture', desc=None)

# TODO(mdb/android-system-infra): Add description
silence_gesture = DeviceSetting(
    DeviceSetting.SECURE, 'silence_gesture', desc=None)

single_tap_gesture = DeviceSetting(
    DeviceSetting.SECURE, 'doze_tap_gesture',
    desc='Modifies whether the single tap gesture is enabled.')

double_tap_gesture = DeviceSetting(
    DeviceSetting.SECURE, 'doze_pulse_on_double_tap',
    desc='Modifies whether the double tap gesture is enabled.')

wake_gesture = DeviceSetting(
    DeviceSetting.SECURE, 'wake_gesture_enabled',
    desc='Modifies whether the device should wake when the wake gesture sensor '
         'detects motion.')

screensaver = DeviceSetting(
    DeviceSetting.SECURE, 'screensaver_enabled',
    desc='Modifies whether the screensaver is enabled.')

notification_led = DeviceSetting(
    DeviceSetting.SYSTEM, 'notification_light_pulse',
    desc='Modifies whether the notification led is enabled.')

# Audio

disable_audio = DeviceSetprop('ro.audio.silent',
                              desc='Modifies the audio silent property.')

# Accelerometer

auto_rotate = DeviceSetting(
    DeviceSetting.SYSTEM, 'accelerometer_rotation',
    desc='Modifies whether auto-rotation is enabled.')

# Time

auto_time = DeviceSetting(
    DeviceSetting.GLOBAL, 'auto_time',
    desc='Modifies whether the time is defined automatically.')

auto_timezone = DeviceSetting(
    DeviceSetting.GLOBAL, 'auto_timezone',
    desc='Modifies whether timezone is defined automatically.')

timezone = DeviceSetprop('persist.sys.timezone',
                         desc='Sets a specified timezone.')

# Location

location_gps = DeviceSetting(
    DeviceSetting.SECURE, 'location_providers_allowed',
    on_val='+gps', off_val='-gps',
    desc='Modifies whether gps is an allowed location provider.')

location_network = DeviceSetting(
    DeviceSetting.SECURE, 'location_providers_allowed',
    on_val='+network', off_val='-network',
    desc='Modifies whether network is an allowed location provider.')

location_mode = DeviceSetting(
    DeviceSetting.SECURE, 'location_mode', on_val='3', off_val='0',
    desc='Sets location mode to either high accuracy (3) or off (0).')

# Power

battery_saver_mode = DeviceSetting(
    DeviceSetting.GLOBAL, 'low_power',
    desc='Modifies whether to enable battery saver mode.')

battery_saver_trigger = DeviceSetting(
    DeviceSetting.GLOBAL, 'low_power_trigger_level',
    desc='Defines the battery level [1-100] at which low power mode '
         'automatically turns on. If 0, it will not automatically turn on. For '
         'Q and newer, it will only automatically turn on if the value is '
         'greater than 0 and is set to '
         'PowerManager.POWER_SAVE_MODE_TRIGGER_PERCENTAGE. '
         'http://shortn/_aGYdmJ8mvf')

enable_full_batterystats_history = GenericCommand(
    'dumpsys batterystats --enable full-history',
    desc='Enables full battery stats history.')

disable_doze = GenericCommand(
    'dumpsys deviceidle disable',
    desc='Disables device\'s deep sleep also known as doze (not to be confused '
         'with ambient, which is also referred to as doze).')

power_stayon = GenericCommand('vc power stayon true',
                              desc='Keep awake from entering sleep.')

# Sensors

disable_sensors = GenericCommand('dumpsys sensorservice restrict blah',
                                 desc='Disables sensors.')

MOISTURE_DETECTION_SETTING_FILE = '/sys/class/power_supply/usb/moisture_detection_enabled'
disable_moisture_detection = GenericCommand(
    'echo 0 > %s' % MOISTURE_DETECTION_SETTING_FILE,
    desc='Modifies /sys/class/power_supply/usb/moisture_detection_enabled so '
         'that moisture detection will be disabled next time it is read.')
stop_moisture_detection = GenericCommand(
    'setprop vendor.usb.contaminantdisable true',
    desc='Triggers a re-read of '
         '/sys/class/power_supply/usb/moisture_detection_enabled'
         'which will enable / disable moisture detection based on its content.')

ambient_eq = DeviceSetting(
    DeviceSetting.SECURE, 'display_white_balance_enabled',
    desc='Modifies ambient EQ, which is auto balance of brightness and color '
         'temperature feature. Differs from adaptive brightness in that this '
         'also changes the color balance.'
         'https://support.google.com/googlenest/answer/9137130?hl=en. ')

disable_pixellogger = GenericCommand('pm disable com.android.pixellogger',
                                     desc="Disables system apps.")

oslo_gating = DeviceSetprop('pixel.oslo.gating',
                            desc='Disables oslo gating.')

# Miscellaneous

hidden_api_exemption = GenericCommand('settings put global hidden_api_blacklist_exemptions *',
                                      desc='Allows all private apis for testing')

test_harness = DeviceBinaryCommandSeries(
    [
        DeviceSetprop('ro.monkey', desc='Modifies monkey state.'),
        DeviceSetprop('ro.test_harness', desc='Modifies test_harness property.')
    ]
)

crashed_activities = GenericCommand('dumpsys activity processes | grep -e'
                                    ' .*crashing=true.*AppErrorDialog.* -e'
                                    ' .*notResponding=true.'
                                    '*AppNotRespondingDialog.*',
                                    desc = 'Logs crashed processes')

dismiss_keyguard = GenericCommand('wm dismiss-keyguard',
                                  desc='Dismisses the lockscreen.')

home_button = GenericCommand('input keyevent 3',
                             desc='Goes to home screen')

menu_button = GenericCommand('input keyevent 82',
                             desc='Unlocks screen by pressing menu button')

modem_diag = DeviceBinaryCommandSeries(
    [
        DeviceSetprop('persist.vendor.sys.modem.diag.mdlog', 'true', 'false',
                      desc='Modifies vendor modem logging property'),
        DeviceSetprop('persist.sys.modem.diag.mdlog', 'true', 'false',
                      desc='Modifies modem logging property'),
    ]
)

reboot_power = GenericCommand('svc power reboot null',
                              desc='Reboots device')
