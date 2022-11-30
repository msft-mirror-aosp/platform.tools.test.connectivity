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


import acts_contrib.test_utils.power.cellular.cellular_pdcch_power_test as cppt


class PowerTelPdcchFr2_Preset_Test(cppt.PowerTelPDCCHTest):
    def setup_class(self):
        super().setup_class()
        self.cellular_simulator.switch_HCCU_settings(is_fr2=True)

    def teardown_test(self):
        super().teardown_test()
        self.sponge_upload()
        self.cellular_simulator.detach()
        self.cellular_dut.toggle_airplane_mode(True)

    def test_preset_nsa_cdrx_fr2(self):
        self.power_pdcch_test()

    def test_preset_nsa_pdcch_fr2(self):
        self.power_pdcch_test()
