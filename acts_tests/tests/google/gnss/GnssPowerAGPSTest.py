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


class GnssPowerAGPSTest(PowerGTWGnssBaseTest):
    """Gnss AGPS Power Test"""

    # Test cases
    # Cell only tests
    def test_cell_power_baseline(self):
        self.set_cell_only()
        self.baseline_test()

    def test_cell_strong_cn(self):
        self.set_cell_only()
        self.start_gnss_tracking_with_power_data()

    def test_cell_weak_cn(self):
        self.set_attenuation(self.atten_level['weak_signal'])
        self.set_cell_only()
        self.start_gnss_tracking_with_power_data()

    def test_cell_no_signal(self):
        self.set_attenuation(self.atten_level['no_signal'])
        self.set_cell_only()
        self.start_gnss_tracking_with_power_data(is_signal=False)

    # Long Interval tests
    def test_cell_strong_cn_long(self):
        self.set_cell_only()
        self.start_gnss_tracking_with_power_data(freq=self.interval)

    def test_cell_weak_cn_long(self):
        self.set_attenuation(self.atten_level['weak_signal'])
        self.set_cell_only()
        self.start_gnss_tracking_with_power_data(freq=self.interval)
