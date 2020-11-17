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
from acts_contrib.test_utils.instrumentation.device.apps.app_installer import \
  AppInstaller
from acts_contrib.test_utils.instrumentation.device.command.adb_commands import goog


class DuoTest(instrumentation_power_test.InstrumentationPowerTest):
  """Test class for running duo instrumentation tests."""

  def _prepare_device(self):
    super()._prepare_device()
    self.base_device_configuration()

    self._duo_apk = AppInstaller(
        self.ad_dut, self.get_file_from_config('duo_faketachyon_apk'))
    self._duo_apk.install('-g')

  def test_duo_preview(self):
    """Measures power when the device is on duo preview screen."""
    metrics = self.run_and_measure(
        'com.google.android.platform.powertests.DuoPowerTests',
        'testDuoPreview')
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  def test_duo_loopback(self):
    """Measures power when the device is making a loopback call through duo."""
    self.adb_run(goog.duo_grant_camera)
    self.adb_run(goog.duo_grant_audio)
    self.adb_run(goog.duo_grant_contacts)

    metrics = self.run_and_measure(
        'com.google.android.platform.powertests.DuoPowerTests',
        'testDuoLoopbackMode')
    self.record_metrics(metrics)
    self.validate_metrics(metrics)
