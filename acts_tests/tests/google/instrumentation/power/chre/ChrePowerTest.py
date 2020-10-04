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

from acts.test_utils.instrumentation.device.command.adb_commands import common
from acts.test_utils.instrumentation.device.command.adb_commands import goog
from acts.test_utils.instrumentation.power import instrumentation_power_test


BIG_FILE_PUSH_TIMEOUT = 600

class ChrePowerTest(instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running CHRE power tests."""

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()
        self.adb_run(goog.enable_chre)

    def _push_chre_power_power_test_files(self, micro_image=False):
        src_path = self.get_file_from_config('chre_power_host_app_path')
        dest_path = '/data/local/tmp/chre_power_test_client'
        self.push_to_external_storage(src_path, dest=dest_path, timeout = BIG_FILE_PUSH_TIMEOUT)

        src_path = self.get_file_from_config('chre_power_nanoapp_path')
        dest_path = '/data/local/tmp/power_test.so'
        if micro_image:
            src_path = self.get_file_from_config('chre_power_nanoapp_tcm_path')
            dest_path = '/data/local/tmp/power_test_tcm.so'

        self.push_to_external_storage(src_path, dest=dest_path, timeout = BIG_FILE_PUSH_TIMEOUT)

    def test_chre_audio(self):
        """Measures power for enabling CHRE audio buffering."""

        self._push_chre_power_power_test_files(False)
        test_params = [
            ('tcm_mode', 'false'),
            ('power_test_host_app_path', '/data/local/tmp/chre_power_test_client'),
            ('power_test_nanoapp_path', '/data/local/tmp/power_test.so'),
            ('duration_ns', '2000000000'),
        ]

        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.ChrePowerTests',
            'testChreAudio',
            extra_params = test_params)
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

    def test_chre_cell(self):
        """Measures power for CHRE cell scan."""

        self._push_chre_power_power_test_files(False)
        self.adb_run(common.cellular.toggle(True))
        test_params = [
            ('tcm_mode', 'false'),
            ('power_test_host_app_path', '/data/local/tmp/chre_power_test_client'),
            ('power_test_nanoapp_path', '/data/local/tmp/power_test.so'),
            ('interval_ns', '5000000000'),
        ]

        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.ChrePowerTests',
            'testChreCell',
            extra_params = test_params)
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

    def test_chre_gnss(self):
        """Measures power for CHRE gnss scan."""

        self._push_chre_power_power_test_files(False)
        self.adb_run(common.location_gps.toggle(True))
        test_params = [
            ('tcm_mode', 'false'),
            ('power_test_host_app_path', '/data/local/tmp/chre_power_test_client'),
            ('power_test_nanoapp_path', '/data/local/tmp/power_test.so'),
            ('interval_ms', '10000'),
        ]

        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.ChrePowerTests',
            'testChreGnss',
            extra_params = test_params)
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

    def test_chre_timer(self):
        """Measures power for CHRE timer wakeup scan."""

        self._push_chre_power_power_test_files(False)
        test_params = [
            ('tcm_mode', 'false'),
            ('power_test_host_app_path', '/data/local/tmp/chre_power_test_client'),
            ('power_test_nanoapp_path', '/data/local/tmp/power_test.so'),
            ('interval_ns', '1000000000'),
        ]

        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.ChrePowerTests',
            'testChreTimer',
            extra_params = test_params)
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

    def test_chre_wifi(self):
        """Measures power for CHRE wifi scan."""

        self._push_chre_power_power_test_files(False)
        self.adb_run(common.wifi_global.toggle(True))
        test_params = [
            ('tcm_mode', 'false'),
            ('power_test_host_app_path', '/data/local/tmp/chre_power_test_client'),
            ('power_test_nanoapp_path', '/data/local/tmp/power_test.so'),
            ('interval_ns', '5000000000'),
        ]

        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.ChrePowerTests',
            'testChreWifi',
            extra_params = test_params)
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

