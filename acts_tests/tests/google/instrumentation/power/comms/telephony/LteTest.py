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
import time

from acts.test_utils.instrumentation.power.instrumentation_power_test \
    import InstrumentationPowerTest
from acts.test_utils.instrumentation.device.command.adb_commands import common

from acts import signals
from acts.libs.proc.job import TimeoutError
from acts.controllers.android_lib.errors import AndroidDeviceError


class LteTest(InstrumentationPowerTest):
    """Test class for running instrumentation test
    ImsTestCases#testVoLTEOnSuspend
    """

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()
        self.set_preferred_network('lte')
        self.adb_run(common.mobile_network_settings)

        try:
            self.ad_dut.reboot(timeout=180)
        except (AndroidDeviceError, TimeoutError):
            raise signals.TestFailure('Device did not reboot successfully.')
        self.log.debug('Giving device extra minute after booting before '
                       'starting instrumentation test.')
        time.sleep(60)

        self.adb_run(common.disable_doze)

    def test_lte_hotspot(self):
        """Measures power when the device is running
        making a hotspot through LTE
        """
        self.adb_run(common.disable_dialing.toggle(False))
        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.WifiTests',
            'testWifiHotspot')
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

    def test_lte_standby(self):
        """Measures power when the device is running
        ImsTestCases#testVoLTEOnSuspend
        """
        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.ImsTestCases',
            'testVoLTEOnSuspend')
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

    def test_lte_voicecall(self):
        """Measures power when the device is running
        making a voice call through LTE
        """
        self.adb_run(common.disable_dialing.toggle(False))
        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.PhoneTestCases',
            'testPhoneCall',
            extra_params=[('PhoneNumber', '4049789061')])
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

