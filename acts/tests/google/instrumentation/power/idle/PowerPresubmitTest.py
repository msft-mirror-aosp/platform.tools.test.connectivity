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

from acts.test_utils.instrumentation.power import instrumentation_power_test
from acts.test_utils.instrumentation import config_wrapper


class PowerPresubmitTest(instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running ACTS instrumentation based power framework
    presubmit tests."""

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()

    def test_quick_idle(self):
        """Measures power when the device is in a rock bottom state, hard-coding
        only 20 seconds worth of measurement and 10 of on device test."""
        # TODO: max_current and voltage should also be hardcoded somehow.
        self._instr_cmd_builder.set_output_as_text()
        overrides = self.context_specific_config({
            'Monsoon': {'duration': 20,
                        'frequency': 100,
                        'delay': 0 }
        })
        self._instrumentation_config = config_wrapper.merge(
            self._instrumentation_config, overrides)

        self.run_and_measure(
            'com.google.android.platform.powertests.IdleTestCase',
            'testIdleScreenOff',
            extra_params=[('IdleTestCase-testIdleScreenOff', '10')])
        self.validate_power_results()
