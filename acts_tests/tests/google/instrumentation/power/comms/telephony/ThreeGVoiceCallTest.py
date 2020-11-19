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

from acts_contrib.test_utils.instrumentation.power.instrumentation_power_test \
    import InstrumentationPowerTest
from acts_contrib.test_utils.instrumentation.device.command.adb_commands import common


class ThreeGVoiceCallTest(InstrumentationPowerTest):
    """Test class for running instrumentation test
    PhoneTestCases#testPhoneCall
    """

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()
        self.set_preferred_network('3g')
        self.adb_run(common.disable_dialing.toggle(False))

    def test_three_g_voice_call(self):
        """Measures power when the device is running
        PhoneTestCases#testPhoneCall
        """
        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.PhoneTestCases',
            'testPhoneCall',
            extra_params=[('PhoneNumber', '0988102544')])
        self.record_metrics(metrics)
        self.validate_metrics(metrics)
