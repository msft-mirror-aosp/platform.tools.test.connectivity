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


class PowerTelPdcch_Preset_Test(cppt.PowerTelPDCCHTest):

    # Key for custom_property in Sponge
    CUSTOM_PROP_KEY_BUILD_ID = 'build_id'
    CUSTOM_PROP_KEY_INCR_BUILD_ID = 'incremental_build_id'
    CUSTOM_PROP_KEY_BUILD_TYPE = 'build_type'
    CUSTOM_PROP_KEY_POWER_MEASURE = 'power_measure'
    CUSTOM_PROP_KEY_MODEM_BASEBAND = 'baseband'

    def teardown_test(self):
        super().teardown_test()

        build_info = self.cellular_dut.ad.build_info
        build_id = build_info.get('build_id', 'Unknown')
        incr_build_id = build_info.get('incremental_build_id', 'Unknown')
        modem_base_band = self.cellular_dut.ad.adb.getprop(
            'gsm.version.baseband')
        build_type = build_info.get('build_type', 'Unknown')
        power_measure = self.power_results.get(self.test_name, None)
        self.record_data({
            'Test Name': self.test_name,
            'sponge_properties': {
                self.CUSTOM_PROP_KEY_POWER_MEASURE: power_measure,
                self.CUSTOM_PROP_KEY_BUILD_ID: build_id,
                self.CUSTOM_PROP_KEY_INCR_BUILD_ID: incr_build_id,
                self.CUSTOM_PROP_KEY_MODEM_BASEBAND: modem_base_band,
                self.CUSTOM_PROP_KEY_BUILD_TYPE: build_type
            },
        })

    def test_preset_sa_pdcch(self):
        self.power_pdcch_test()

    def test_preset_nsa_pdcch(self):
        self.power_pdcch_test()

    def test_preset_LTE_pdcch(self):
        self.power_pdcch_test()

    def test_preset_sa_cdrx(self):
        self.power_pdcch_test()

    def test_preset_nsa_cdrx(self):
        self.power_pdcch_test()

    def test_preset_LTE_cdrx(self):
        self.power_pdcch_test()
