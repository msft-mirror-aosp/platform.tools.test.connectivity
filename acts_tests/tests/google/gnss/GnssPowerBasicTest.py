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


class GnssPowerBasicTest(PowerGTWGnssBaseTest):
    """Gnss Power Basic Test"""

    # Test cases
    # Standalone tests
    def test_standalone_gps_power_baseline(self):
        """
            1. Set DUT rockbottom.
            2. Collect power data.
        """
        self.baseline_test()

    def test_standalone_DPO_on(self):
        """
            1. Attenuate signal to strong GNSS level.
            2. Turn DPO on.
            3. Open GPStool and tracking with DUT sleep.
            4. Collect power data.
        """
        self.set_attenuation(self.atten_level['strong_signal'])
        self.enable_DPO(True)
        self.start_gnss_tracking_with_power_data(mode='standalone')

    def test_standalone_DPO_on_weak_signal(self):
        """
            1. Attenuate signal to strong GNSS level.
            2. Turn DPO on.
            3. Open GPStool and tracking with DUT sleep.
            4. Collect power data.
        """
        self.set_attenuation(self.atten_level['weak_signal'])
        self.enable_DPO(True)
        self.start_gnss_tracking_with_power_data(mode='standalone')

    def test_standalone_DPO_off(self):
        """
            1. Attenuate signal to strong GNSS level.
            2. Turn DPO off.
            3. Open GPStool and tracking with DUT sleep.
            4. Collect power data.
        """
        self.set_attenuation(self.atten_level['strong_signal'])
        self.enable_DPO(False)
        self.start_gnss_tracking_with_power_data(mode='standalone')

    def test_standalone_DPO_off_weak_signal(self):
        """
            1. Attenuate signal to strong GNSS level.
            2. Turn DPO off.
            3. Open GPStool and tracking with DUT sleep.
            4. Collect power data.
        """
        self.set_attenuation(self.atten_level['weak_signal'])
        self.enable_DPO(False)
        self.start_gnss_tracking_with_power_data(mode='standalone')

    def test_standalone_no_signal(self):
        """
            1. Attenuate signal to strong GNSS level.
            2. Turn DPO on.
            3. Open GPStool and tracking with DUT sleep.
            4. Collect power data.
        """
        self.set_attenuation(self.atten_level['no_signal'])
        self.enable_DPO(True)
        self.start_gnss_tracking_with_power_data(mode='standalone')

    def test_partial_wake_lock(self):
        """
            1. Attenuate signal to strong GNSS level.
            2. Trigger instrumentation to hold the partial wake lock.
            3. Collect power data.
        """
        self.set_attenuation(self.atten_level['strong_signal'])
        test_class = 'com.google.android.platform.powertests.IdleTestCase'
        test_method = 'testPartialWakelock'
        test_methods = {test_class: test_method}
        options = {'IdleTestCase-testPartialWakelock': self.mon_duration}
        instrument_cmd = gutils.build_instrumentation_call(
            POWER_TEST_PACKAGE, DEFAULT_RUNNER, test_methods, options)
        self.ad.adb.shell_nb(instrument_cmd)
        self.baseline_test()
