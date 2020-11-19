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


class VzWDoUAutomationFileTest(
    vzw_dou_automation_base_test.VzWDoUAutomationBaseTest):
  """Class for running VZW DoU file test cases"""

  @repeated_test(
      num_passes=1,
      acceptable_failures=0,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_download_file(self, attempt_number):
    """Measures power for device download file."""
    gmail_phrase = self._instrumentation_config.get_config(
        'additional_setting').get('gmail_phrase')
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.DriveDownloadFileTests',
        'testDownloadFile',
        extra_params=[('gmail_account',
                       vzw_dou_automation_base_test.GMAIL_ACCOUNT),
                      ('gmail_password', gmail_phrase)],
        attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)
