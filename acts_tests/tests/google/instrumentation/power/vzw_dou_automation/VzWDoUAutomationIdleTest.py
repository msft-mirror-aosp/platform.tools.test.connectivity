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

from acts.test_decorators import repeated_test
from acts.test_utils.instrumentation.power.vzw_dou_automation import \
    vzw_dou_automation_base_test
from acts.test_utils.instrumentation.device.command.adb_commands import common


class VzWDoUAutomationIdleTest(
    vzw_dou_automation_base_test.VzWDoUAutomationBaseTest):
  """Class for running VZW DoU idle test cases"""

  @repeated_test(
      num_passes=3,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_flight_mode_idle(self, attempt_number):
    """Measures power when the device is in airplane mode."""

    self.adb_run(common.airplane_mode.toggle(True))
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.IdleStandbyModeTests',
        'testIdleStandbyMode', attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  @repeated_test(
      num_passes=3,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_idle(self, attempt_number):
    """Measures power when the device is in idle mode."""

    self.log_in_gmail_account()
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.IdleStandbyModeTests',
        'testIdleStandbyMode', attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  def test_idle_wifi(self):
    """Measures power when the device is in idle mode with wifi connected."""

    self.log_in_gmail_account()
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.IdleStandbyModeTests',
        'testIdleStandbyMode',
        extra_params=[('wifi_ssid', vzw_dou_automation_base_test.WIFI_SSID)])
    self.record_metrics(metrics)
    self.validate_metrics(metrics)
