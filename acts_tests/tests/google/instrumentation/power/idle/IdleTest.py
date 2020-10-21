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

from acts import signals
from acts.libs.proc.job import TimeoutError
from acts.controllers.android_lib.errors import AndroidDeviceError
from acts_contrib.test_utils.instrumentation.power import instrumentation_power_test
from acts_contrib.test_utils.instrumentation.device.command.adb_commands import common
from acts_contrib.test_utils.instrumentation.device.command.adb_commands import goog


class IdleTest(instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running instrumentation test idle system cases."""

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()

    def run_idle_test_case(self):
        metrics = self.run_and_measure(
            'com.google.android.platform.powertests.IdleTestCase',
            'testIdleScreenOff')
        self.record_metrics(metrics)
        self.validate_metrics(metrics)

    def test_rock_bottom(self):
        """Measures power when the device is in a rock bottom state."""
        self.run_idle_test_case()

    def test_boot(self):
        """Makes sure the device comes back up after rebooting and measures
        power when the device is in a rock bottom state."""
        self._instr_cmd_builder.set_output_as_text()
        try:
            self.ad_dut.reboot(timeout=180)
        except (AndroidDeviceError, TimeoutError):
            raise signals.TestFailure('Device did not reboot successfully.')
        self.log.debug('Giving device extra minute after booting before '
                       'starting instrumentation test.')
        time.sleep(60)
        self.run_idle_test_case()

    def test_display_always_on(self):
        """Measures power when the device is rock bottom state plus display
        always on (known as doze mode)."""
        self.adb_run(common.doze_always_on.toggle(True))
        self.adb_run(common.disable_sensors)
        self.run_idle_test_case()

    def test_ambient(self):
        """Measures power when the device is rock bottom state plus ambient mode
        on, which means notifications are alowed to display on top of the
        mostly dark background screen."""
        self.adb_run(common.doze_mode.toggle(True))
        self.run_idle_test_case()

    def test_double_tap(self):
        """Measures power when the device is rock bottom state plus the double
        tap gesture is enabled."""
        self.adb_run(common.double_tap_gesture.toggle(True))
        self.run_idle_test_case()

    def test_edge_sensor(self):
        """Measures power when the device is rock bottom state plus the edge
        sensor (squeeze) is enabled."""
        self.adb_run(goog.edge_sensor.toggle(True))
        self.run_idle_test_case()

    def test_wake_gesture(self):
        """Measures power when the device is rock bottom state plus the wake
        gesture is enabled."""
        self.adb_run(common.wake_gesture.toggle(True))
        self.run_idle_test_case()

    def test_pick_up_gesture(self):
        """Measures power when the device is rock bottom state plus the pick up
        gesture is enabled."""
        self.adb_run(common.doze_pulse_on_pick_up.toggle(True))
        self.run_idle_test_case()
