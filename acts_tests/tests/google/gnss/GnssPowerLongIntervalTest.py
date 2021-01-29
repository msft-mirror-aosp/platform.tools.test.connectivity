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
from acts_contrib.test_utils.power.PowerGTWGnssBaseTest import PowerGTWGnssBaseTest
from acts_contrib.test_utils.gnss import gnss_test_utils as gutils
from acts_contrib.test_utils.wifi import wifi_test_utils as wutils


class GnssPowerLongIntervalTest(PowerGTWGnssBaseTest):
    """Gnss Power Long Interval Test"""

    def setup_class(self):
        super().setup_class()
        self.unpack_userparams(req_param_names=['interval'])

    # Test cases
    def test_long_interval_DPO_on(self):
        self.enable_DPO(True)
        self.start_gnss_tracking_with_power_data(
            mode='standalone', freq=self.interval)

    def test_long_interval_DPO_on_measurement_on(self):
        self.enable_DPO(True)
        self.start_gnss_tracking_with_power_data(
            mode='standalone', freq=self.interval, meas=True)

    def test_long_interval_DPO_off(self):
        self.enable_DPO(False)
        self.start_gnss_tracking_with_power_data(
            mode='standalone', freq=self.interval)

    def test_long_interval_DPO_off_measurement_on(self):
        self.enable_DPO(False)
        self.start_gnss_tracking_with_power_data(
            mode='standalone', freq=self.interval, meas=True)
