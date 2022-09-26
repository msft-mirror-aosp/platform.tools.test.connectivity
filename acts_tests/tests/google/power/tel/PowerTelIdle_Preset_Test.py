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

import acts_contrib.test_utils.power.cellular.cellular_idle_power_test as cipt


class PowerTelIdle_Preset_Test(cipt.PowerTelIdleTest):
    def teardown_test(self):
        super().teardown_test()
        self.sponge_upload()

    def test_preset_LTE_idle(self):
        self.power_tel_idle_test(filter_results=False)

    def test_preset_sa_idle_fr1(self):
        self.power_tel_idle_test(filter_results=False)
