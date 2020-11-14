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

from acts_contrib.test_utils.instrumentation.power import instrumentation_power_test


class ApolloNoSetupTest(instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running a test with no setup being applied to the device.
     Useful for when you need to manually do some changes that could be
     reversed with the regular preparation steps. Tests in this class should be
     executed assuming there is no SL4A installed."""

    def setup_test(self):
        super().setup_test()
        # clear command options that won't work on OEM devices.
        self._instr_cmd_builder.set_output_as_text()
        self._instr_cmd_builder.remove_flag('--no-isolated-storage')

    def test_idle_screen_off(self):
        """Calls an instrumentation test that turns the screen off and measures
        power."""
        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.IdleTestCase',
            'testIdleScreenOff')
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

    def test_partial_wake_lock(self):
        """Measures power when the device is idle with a partial wake lock."""
        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.IdleTestCase',
            'testPartialWakelock')
        self.record_metrics(metrics)
        self.validate_metrics(metrics)
