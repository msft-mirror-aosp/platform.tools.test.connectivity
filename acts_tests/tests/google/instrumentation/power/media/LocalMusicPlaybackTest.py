#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from acts.test_utils.instrumentation.device.apps.dismiss_dialogs import \
    DialogDismissalUtil
from acts.test_utils.instrumentation.device.command.adb_commands import common
from acts.test_utils.instrumentation.power import instrumentation_power_test

BIG_FILE_PUSH_TIMEOUT = 600


class LocalMusicPlaybackTest(
  instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running instrumentation test
    MusicTests#testLocalPlaybackBackground.
    """

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()
        self.push_to_external_storage(
            self.get_file_from_config('music_file'),
            timeout=BIG_FILE_PUSH_TIMEOUT)
        self.trigger_scan_on_external_storage()
        self.adb_run(common.disable_audio.toggle(False))
        self._dialog_util = DialogDismissalUtil(
            self.ad_dut,
            self.get_file_from_config('dismiss_dialogs_apk')
        )
        self._dialog_util.dismiss_dialogs('PlayMusic')

    def test_local_music_playback(self):
        """Measures power when the device is playing music."""
        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.MusicTests',
            'testLocalPlaybackBackground'
        )
        self.record_metrics(metrics)
        self.validate_metrics(metrics)
