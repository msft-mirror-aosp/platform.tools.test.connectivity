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

from acts import utils
from acts.test_utils.power.PowerGTWGnssBaseTest import PowerGTWGnssBaseTest
from acts.test_utils.gnss import gnss_test_utils as gutils
from acts.test_utils.wifi import wifi_test_utils as wutils


class GnssPowerLowPowerTest(PowerGTWGnssBaseTest):
    """Gnss Power Low Power Mode Test"""

    def setup_class(self):
        super().setup_class()
        self.unpack_userparams(req_param_names=['interval'])

    # Test cases
    def test_low_power_mode_DPO_on(self):
        self.set_attenuation(self.atten_level['strong_signal'])
        self.enable_DPO(True)
        self.start_gnss_tracking_with_power_data(
            mode='standalone', lowpower=True)

    def test_low_power_mode_DPO_on_long_interval(self):
        self.set_attenuation(self.atten_level['strong_signal'])
        self.enable_DPO(True)
        self.start_gnss_tracking_with_power_data(
            mode='standalone', freq=self.interval, lowpower=True)

    def test_low_power_mode_DPO_off(self):
        self.set_attenuation(self.atten_level['strong_signal'])
        self.enable_DPO(False)
        self.start_gnss_tracking_with_power_data(
            mode='standalone', lowpower=True)

    def test_low_power_mode_DPO_off_long_interval(self):
        self.set_attenuation(self.atten_level['strong_signal'])
        self.enable_DPO(False)
        self.start_gnss_tracking_with_power_data(
            mode='standalone', freq=self.interval, lowpower=True)
