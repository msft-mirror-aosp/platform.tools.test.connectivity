#!/usr/bin/env python3
#
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

import acts_contrib.test_utils.power.cellular.cellular_power_base_test as PWCEL


class PowerTelIdle_Preset_Test(PWCEL.PowerCellularLabBaseTest):
    def setup_class(self):
        super().setup_class()
        self.cellular_simulator.switch_HCCU_settings(is_fr2=False)

    def power_tel_idle_test(self):
        """ Measures power when the device is on RRC idle state."""
        idle_wait_time = self.simulation.rrc_sc_timer + 30
        # Wait for RRC status change to trigger
        self.cellular_simulator.wait_until_idle_state(idle_wait_time)

        # Measure power
        self.collect_power_data()

        # Check if power measurement is below the required value
        self.pass_fail_check(self.avg_current)

    def teardown_test(self):
        super().teardown_test()
        self.sponge_upload()
        self.cellular_simulator.detach()
        self.cellular_dut.toggle_airplane_mode(True)

    def test_preset_LTE_idle(self):
        self.power_tel_idle_test()

    def test_preset_sa_idle_fr1(self):
        self.power_tel_idle_test()
