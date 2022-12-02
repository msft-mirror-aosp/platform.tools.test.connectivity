#   Copyright 2022 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
import time

import acts_contrib.test_utils.power.cellular.cellular_power_base_test as PWCEL


class PowerTelAirplaneModeTest(PWCEL.PowerCellularLabBaseTest):

    def power_tel_airplane_mode_test(self):
        """Measure power while airplane mode is on. """
        # Start airplane mode
        self.cellular_dut.toggle_airplane_mode(True)

        # Allow airplane mode to propagate
        time.sleep(3)

        # Measure power
        self.collect_power_data()
        # Check if power measurement is within the required values
        self.pass_fail_check(self.avg_current)

    def teardown_test(self):
        super().teardown_test()
        self.sponge_upload()


class PowerTelAirplaneMode_Test(PowerTelAirplaneModeTest):
    def setup_class(self):
        super().setup_class()

    def test_airplane_mode(self):
        self.power_tel_airplane_mode_test()