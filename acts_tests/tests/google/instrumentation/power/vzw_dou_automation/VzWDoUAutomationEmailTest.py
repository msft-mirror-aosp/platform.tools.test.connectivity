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
from acts_contrib.test_utils.instrumentation.power.vzw_dou_automation import \
  vzw_dou_automation_base_test


class VzWDoUAutomationEmailTest(
    vzw_dou_automation_base_test.VzWDoUAutomationBaseTest):
  """Class for running VZW DoU email test cases"""

  def test_send_email(self):
    """Measures power for device sending email."""

    exchange_email = self.generate_random_exchange_email_account(
        vzw_dou_automation_base_test.TestCase.TC28)
    additional_setting = self._instrumentation_config.get_config('additional_setting')
    exchange_phrase = additional_setting.get('exchange_phrase')
    self.log_in_gmail_account(sync='true', wait_for_checkin='true')
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.GmailSendExchangeTests',
        'testSendEmail',
        extra_params=[('email_account', exchange_email),
                      ('email_password', exchange_phrase)])
    self.record_metrics(metrics)
    self.validate_metrics(metrics)
