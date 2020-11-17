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


class GnssPowerAGPSTest(PowerGTWGnssBaseTest):
    """Gnss AGPS Power Test"""

    def turn_on_wifi_connection(self):
        """Turn on wifi connection."""
        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.wifi_network)

    def set_cell_only(self):
        """Turn off wifi connection, enable cell service."""
        wutils.wifi_toggle_state(self.ad, False)
        utils.force_airplane_mode(self.ad, False)

    # Test cases
    # Wifi only tests
    def test_wifi_only_gps_power_baseline(self):
        self.turn_on_wifi_connection()
        self.baseline_test()

    def test_wifi_only_gps_strong_signal(self):
        self.set_attenuation(self.atten_level['strong_signal'])
        self.enable_DPO(True)
        self.turn_on_wifi_connection()
        self.start_gnss_tracking_with_power_data()

    def test_wifi_only_gps_weak_signal(self):
        self.set_attenuation(self.atten_level['weak_signal'])
        self.enable_DPO(True)
        self.turn_on_wifi_connection()
        self.start_gnss_tracking_with_power_data()

    def test_wifi_only_gps_no_signal(self):
        self.set_attenuation(self.atten_level['no_signal'])
        self.turn_on_wifi_connection()
        self.start_gnss_tracking_with_power_data(is_signal=False)

    # Cell only tests
    def test_cell_only_gps_power_baseline(self):
        self.set_cell_only()
        self.baseline_test()

    def test_cell_only_gps_strong_signal(self):
        self.set_attenuation(self.atten_level['strong_signal'])
        self.enable_DPO(True)
        self.set_cell_only()
        self.start_gnss_tracking_with_power_data()

    def test_cell_only_gps_weak_signal(self):
        self.set_attenuation(self.atten_level['weak_signal'])
        self.enable_DPO(True)
        self.set_cell_only()
        self.start_gnss_tracking_with_power_data()

    def test_cell_only_gps_no_signal(self):
        self.set_attenuation(self.atten_level['no_signal'])
        self.set_cell_only()
        self.start_gnss_tracking_with_power_data(is_signal=False)
