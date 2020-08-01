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
  DeviceGServices
from acts.test_utils.instrumentation.device.command.adb_command_types import \
  DeviceState
from acts.test_utils.instrumentation.device.command.adb_command_types import \
  DeviceSetprop
from acts.test_utils.instrumentation.device.command.adb_command_types import \
  DeviceSetting
from acts.test_utils.instrumentation.device.command.adb_command_types import \
  GenericCommand

"""Google-internal device settings for power testing."""

# TODO: add descriptions to each setting

# Location

location_collection = DeviceGServices(
    'location:collection_enabled', on_val='1', off_val='0',
    desc='Modifies whether collecting location is enabled.')

location_off_warning_dialog = DeviceGServices(
    'location:enable_location_off_warning_dialog', on_val='true', off_val='false',
    desc='Modifies whether the location off warning dialog should appear.'
)

location_opt_in = DeviceBinaryCommandSeries(
    [
        DeviceState('content insert --uri content://com.google.settings/'
                    'partner --bind name:s:use_location_for_services '
                    '--bind value:s:%s',
                    desc='Modifies whether using location for services is '
                         'allowed.'),
        DeviceState('content insert --uri content://com.google.settings/'
                    'partner --bind name:s:network_location_opt_in '
                    '--bind value:s:%s',
                    desc='Modifies whether to allow location over network.')
    ]
)

# Cast

# TODO(mdb/android-system-infra): Define what is 'cast broadcast' exactly.
cast_broadcast = DeviceGServices(
    'gms:cast:mdns_device_scanner:is_enabled',
    desc='Modifies whether the cast broadcast is enabled.')

# Apps
disable_chrome = GenericCommand('pm disable-user com.android.chrome',
                                desc='Disables the Google chrome.')

force_stop_nexuslauncher = GenericCommand('am force-stop com.google.android.apps.nexuslauncher',
                                desc='Force stop nexus launcher.')

disable_playstore = GenericCommand('pm disable-user com.android.vending',
                                   desc='Disables the Google playstore.')

# Volta

disable_volta = GenericCommand('pm disable-user com.google.android.volta',
                               desc='Disables the volta app.')

# CHRE

disable_chre = GenericCommand('setprop ctl.stop vendor.chre',
                              desc='Disables chre.')

# MusicIQ

disable_musiciq = GenericCommand(
    'pm disable-user com.google.intelligence.sense',
    desc='Disables the musiciq feature, which listens to surrounding music to '
         'show what is being played.')

# Email

remove_gmail_account = GenericCommand(
    'am instrument -w com.google.android.tradefed.account/.RemoveAccounts',
                                      desc='Removes gmail account.')

# Hotword

hotword = DeviceState(
    'am start -a com.android.intent.action.MANAGE_VOICE_KEYPHRASES '
    '--ei com.android.intent.extra.VOICE_KEYPHRASE_ACTION %s '
    '--es com.android.intent.extra.VOICE_KEYPHRASE_HINT_TEXT "demo" '
    '--es com.android.intent.extra.VOICE_KEYPHRASE_LOCALE "en-US" '
    'com.android.hotwordenrollment.okgoogle/'
    'com.android.hotwordenrollment.okgoogle.EnrollmentActivity',
    on_val='0',
    off_val='2',
    desc='Modifies whether hotword detection is enabled.')

camera_hdr_mode = DeviceSetprop(
    'camera.optbar.hdr', on_val='true', off_val='false',
    desc="Modifies whether to use HDR camera mode.")

# TODO(mdb/android-system-infra): Add description
compact_location_log = DeviceGServices(
    'location:compact_log_enabled')

# TODO(mdb/android-system-infra): Add description
magic_tether = DeviceGServices('gms:magictether:enable')

# TODO(mdb/android-system-infra): Add description
ocr = DeviceGServices('ocr.cc_ocr_enabled')

# TODO(mdb/android-system-infra): Add description
phenotype = DeviceGServices(
    'gms:phenotype:phenotype_flag:debug_bypass_phenotype')

# TODO(mdb/android-system-infra): Add description
icing = DeviceGServices('gms_icing_extension_download_enabled')

edge_sensor = DeviceBinaryCommandSeries([
    DeviceSetting(
        DeviceSetting.SECURE, 'assist_gesture_enabled',
        desc='Modifies whether the edge sensor gesture is enabled.'),
    DeviceSetting(
        DeviceSetting.SECURE, 'assist_gesture_wake_enabled',
        desc='Modifies whether the edge sensor gesture is allowed to wake up '
             'the device.'),
    DeviceSetting(
        DeviceSetting.SECURE, 'assist_gesture_setup_complete',
        desc='Triggers activation/deactivation of edge sensor gesture. It '
             'depends on the settings assist_gesture_enabled and '
             'assist_gesture_wake_enabled to be previously set.')
])
