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
from acts.test_utils.instrumentation.device.command.adb_commands import goog


class VzWDoUAutomationIdleTest(
    vzw_dou_automation_base_test.VzWDoUAutomationBaseTest):
  """Class for running VZW DoU idle test cases"""

  @repeated_test(
      num_passes=1,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_flight_mode_idle(self, attempt_number):
    """Measures power when the device is in airplane mode."""

    self.adb_run(goog.disable_playstore)
    self.adb_run(goog.remove_gmail_account)
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

    self.adb_run(goog.disable_betterbug)
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.IdleStandbyModeTests',
        'testIdleStandbyMode', attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  @repeated_test(
      num_passes=3,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_idle_wifi(self, attempt_number):
    """Measures power when the device is in idle mode with wifi connected."""

    self.adb_run(common.wifi_state.toggle(True))
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.IdleStandbyModeTests',
        'testIdleStandbyMode',
        extra_params=[('wifi_ssid', vzw_dou_automation_base_test.WIFI_SSID)],
        attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  @repeated_test(
      num_passes=1,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_idle_background_traffics(self, attempt_number):
    """Measures power when the device is in idle mode with background traffics."""

    self.install_facebook_apk()
    self.install_twitter_apk()
    exchange_email = self.generate_random_exchange_email_account(
        vzw_dou_automation_base_test.TestCase.TC34)
    additional_setting = self._instrumentation_config.get_config(
        'additional_setting')
    exchange_phrase = additional_setting.get('exchange_phrase')
    gmail_phrase = additional_setting.get('gmail_phrase')
    self.log_in_gmail_account(sync='true', wait_for_checkin='true')
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.IdleBackgroundTrafficsTests',
        'testIdleBackgroundTraffics',
        extra_params=[
            ('email_account', exchange_email),
            ('email_password', exchange_phrase),
            ('facebook_account', vzw_dou_automation_base_test.GMAIL_ACCOUNT),
            ('facebook_password', gmail_phrase),
            ('twitter_account', vzw_dou_automation_base_test.TWITTER_ACCOUNT),
            ('twitter_password', gmail_phrase),
            ('wifi_ssid', vzw_dou_automation_base_test.WIFI_SSID)
        ],
        attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)
