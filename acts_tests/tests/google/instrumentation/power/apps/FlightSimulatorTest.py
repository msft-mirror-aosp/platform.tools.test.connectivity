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
from acts.test_utils.instrumentation.device.apps.app_installer import \
  AppInstaller


class FlightSimulatorTest(instrumentation_power_test.InstrumentationPowerTest):
  """Test class for running flight simulator tests."""

  def _prepare_device(self):
    super()._prepare_device()
    self.base_device_configuration()

    self._flight_simulator_apk = AppInstaller(
        self.ad_dut, self.get_file_from_config('flight_simulator_apk'))
    self._flight_simulator_apk.install('-g')

  def test_flight_demo(self):
    """Measures power during a flight demo test."""
    metrics = self.run_and_measure(
        'com.google.android.platform.powertests.FlightSimulatorTests',
        'testFlightDemo')
    self.record_metrics(metrics)
    self.validate_metrics(metrics)
