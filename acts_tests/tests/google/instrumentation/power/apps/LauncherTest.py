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

class LauncherTest(instrumentation_power_test.InstrumentationPowerTest):
  """Test class for running app launcher test cases."""

  def _prepare_device(self):
    super()._prepare_device()
    self.base_device_configuration()

  def test_app_launcher(self):
    """Measures power when the device is on all apps screen."""
    metrics = self.run_and_measure(
        'com.google.android.platform.powertests.AppLauncherTests',
        'testAppLauncher')
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  def test_run_app_launch_test(self):
    """Measures power when apps are launched."""
    metrics = self.run_and_measure(
        'com.google.android.platform.powertests.AppLauncherTests',
        'testAppLaunch')
    self.record_metrics(metrics)
    self.validate_metrics(metrics)
