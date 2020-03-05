#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
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

from acts.test_utils.instrumentation.power import instrumentation_power_test
from acts.test_utils.instrumentation.device.command.adb_commands import common


class RockBottomTest(instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running instrumentation test RockBottom."""

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()

    def run_idle_test_case(self):
        self.run_and_measure(
            'com.google.android.platform.powertests.IdleTestCase',
            'testIdleScreenOff')
        self.validate_power_results()

    def test_rock_bottom(self):
        """Measures power when the device is in a rock bottom state."""
        self.run_idle_test_case()

    def test_boot(self):
        """Makes sure the device comes back up after rebooting and measures
        power when the device is in a rock bottom state."""
        self.ad_dut.reboot(timeout=180)
        self.log.debug('giving device extra minute after booting before '
                       'starting instrumentation test.')
        time.sleep(60)
        self.run_idle_test_case()

    def test_display_always_on(self):
        """Measures power when the device is rock bottom state plus display
        always on (known as doze mode)."""
        self.adb_run(common.doze_always_on.toggle(True))
        self.adb_run(common.disable_sensors)
        self.run_idle_test_case()
