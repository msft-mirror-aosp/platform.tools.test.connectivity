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
import copy

from acts.test_decorators import repeated_test
from acts.test_utils.instrumentation.power.vzw_dou_automation import \
  vzw_dou_automation_comp_base_test
from acts.test_utils.instrumentation.power.vzw_dou_automation import \
  vzw_dou_automation_base_test


class VzWDoUAutomationPhoneCallTest(
    vzw_dou_automation_comp_base_test.VzWDoUAutomationCompBaseTest):
  """Class for running VZW DoU phone call test cases"""

  @repeated_test(
      num_passes=3,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_voice_call_over_lte_band4(self):
    """Measures power when the device is on call with mute on and off."""
    companion_phone_number = self.get_phone_number(self.ad_cp)
    self.log.info('The companion phone number is {}'.format(companion_phone_number))
    self.run_instrumentation_on_companion(
        'com.google.android.platform.dou.CompanionPhoneVoiceCallTests',
        'testReceiveVoiceCall')
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.PhoneVoiceCallWithMuteTests',
        'testVoiceCall',
        extra_params=[('recipient_number_companion', companion_phone_number)])

    final_metrics = self._generate_final_metrics(metrics)
    self.record_metrics(final_metrics)
    self.validate_metrics(final_metrics)

  def _generate_final_metrics(self, metrics):
    """General a final metrics by combine each weighted value in the original metrics.
        Results = Talk *40% + Listen *40% + Silence *20%

        Args:
            metrics: The metrics is a dictionary with a list of
              power_metrics.Metric as value

        Returns:
            A recalculated dictionary
        """
    final_list = []
    final_metrics = {}
    combined_seg_name = ''

    for key, result_list in metrics.items():
      if not final_list:
        for result_metrics in result_list:
          final_list.append(copy.deepcopy(result_metrics))
          final_list[-1].value = 0
      if '2' in key:
        for i, result_metrics in enumerate(result_list):
          final_list[i].value += result_metrics.value * 0.2
      else:
        for i, result_metrics in enumerate(result_list):
          final_list[i].value += result_metrics.value * 0.4
      if '0' in key:
        combined_seg_name = key

    final_metrics[combined_seg_name] = final_list
    return final_metrics
