#!/usr/bin/env python3.4
#
#   Copyright 2021 - The Android Open Source Project
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

from WifiNewSetupAutoJoinTest import WifiNewSetupAutoJoinTest

class WifiNewSetupWifiToWifiAutoJoinTest(WifiNewSetupAutoJoinTest):
    """Test Wifi to Wifi auto-switching.

    Note that tests are inherited from WifiNewSetupAutoJoinTest. The only
    modification is in setup_test, where we ensure Wifi is connected before
    switching networks
    """

    def __init__(self, configs):
        super().__init__(configs)

    def setup_test(self):
        # Attenuate all other networks except network 0's 2.4 GHz STA, and
        # validate we connect to it.
        # This ensures that we are connected to something at the beginning of
        # each test, in order to test Wifi-to-Wifi switching.
        self.set_attn_and_validate_connection(
            (0, 90, 90, 90),
            self.reference_networks[0]["2g"]['bssid'])

    """ Tests Begin """

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_2g_AP1_20_AP2_95_AP3_95(self):
        super().test_autojoin_Ap1_2g_AP1_20_AP2_95_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_2g_AP1_15_AP2_95_AP3_95(self):
        super().test_autojoin_Ap1_2g_AP1_15_AP2_95_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_2g_AP1_10_AP2_95_AP3_95(self):
        super().test_autojoin_Ap1_2g_AP1_10_AP2_95_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_2g_AP1_5_AP2_95_AP3_95(self):
        super().test_autojoin_Ap1_2g_AP1_5_AP2_95_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_2gto5g_AP1_55_AP2_10_AP3_95(self):
        super().test_autojoin_Ap1_2gto5g_AP1_55_AP2_10_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_2gto5g_AP1_50_AP2_10_AP3_95(self):
        super().test_autojoin_Ap1_2gto5g_AP1_50_AP2_10_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_2gto5g_AP1_45_AP2_10_AP3_95(self):
        super().test_autojoin_Ap1_2gto5g_AP1_45_AP2_10_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_in_AP1_5gto2g_AP1_5_AP2_80_AP3_95(self):
        super().test_autojoin_in_AP1_5gto2g_AP1_5_AP2_80_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_in_AP1_5gto2g_AP1_10_AP2_75_AP3_95(self):
        super().test_autojoin_in_AP1_5gto2g_AP1_10_AP2_75_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_in_AP1_5gto2g_AP1_15_AP2_70_AP3_95(self):
        super().test_autojoin_in_AP1_5gto2g_AP1_15_AP2_70_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_swtich_AP1toAp2_AP1_65_AP2_75_AP3_2(self):
        super().test_autojoin_swtich_AP1toAp2_AP1_65_AP2_75_AP3_2()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_swtich_AP1toAp2_AP1_70_AP2_70_AP3_2(self):
        super().test_autojoin_swtich_AP1toAp2_AP1_70_AP2_70_AP3_2()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_swtich_AP1toAp2_AP1_75_AP2_65_AP3_2(self):
        super().test_autojoin_swtich_AP1toAp2_AP1_75_AP2_65_AP3_2()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_2gto5g_AP1_70_AP2_85_AP3_75(self):
        super().test_autojoin_Ap2_2gto5g_AP1_70_AP2_85_AP3_75()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_2gto5g_AP1_75_AP2_80_AP3_75(self):
        super().test_autojoin_Ap2_2gto5g_AP1_75_AP2_80_AP3_75()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_2gto5g_AP1_75_AP2_75_AP3_75(self):
        super().test_autojoin_Ap2_2gto5g_AP1_75_AP2_75_AP3_75()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_5gto2g_AP1_75_AP2_70_AP3_10(self):
        super().test_autojoin_Ap2_5gto2g_AP1_75_AP2_70_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_5gto2g_AP1_75_AP2_75_AP3_10(self):
        super().test_autojoin_Ap2_5gto2g_AP1_75_AP2_75_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_5gto2g_AP1_75_AP2_80_AP3_10(self):
        super().test_autojoin_Ap2_5gto2g_AP1_75_AP2_80_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_out_of_range(self):
        super().test_autojoin_out_of_range()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_2g_AP1_75_AP2_85_AP3_10(self):
        super().test_autojoin_Ap2_2g_AP1_75_AP2_85_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_2g_AP1_75_AP2_80_AP3_10(self):
        super().test_autojoin_Ap2_2g_AP1_75_AP2_80_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_2g_AP1_75_AP2_75_AP3_10(self):
        super().test_autojoin_Ap2_2g_AP1_75_AP2_75_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap2_2g_AP1_75_AP2_70_AP3_10(self):
        super().test_autojoin_Ap2_2g_AP1_75_AP2_70_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_in_Ap2_5gto2g_AP1_75_AP2_70_AP3_10(self):
        super().test_autojoin_in_Ap2_5gto2g_AP1_75_AP2_70_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_in_Ap2_5gto2g_AP1_75_AP2_75_AP3_10(self):
        super().test_autojoin_in_Ap2_5gto2g_AP1_75_AP2_75_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_in_Ap2_5gto2g_AP1_75_AP2_80_AP3_10(self):
        super().test_autojoin_in_Ap2_5gto2g_AP1_75_AP2_80_AP3_10()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_swtich_AP2toAp1_AP1_15_AP2_65_AP3_75(self):
        super().test_autojoin_swtich_AP2toAp1_AP1_15_AP2_65_AP3_75()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_swtich_AP2toAp1_AP1_10_AP2_70_AP3_75(self):
        super().test_autojoin_swtich_AP2toAp1_AP1_10_AP2_70_AP3_75()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_swtich_AP2toAp1_AP1_5_AP2_75_AP3_75(self):
        super().test_autojoin_swtich_AP2toAp1_AP1_5_AP2_75_AP3_75()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_5gto2g_AP1_10_AP2_80_AP3_95(self):
        super().test_autojoin_Ap1_5gto2g_AP1_10_AP2_80_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_5gto2g_AP1_15_AP2_80_AP3_95(self):
        super().test_autojoin_Ap1_5gto2g_AP1_15_AP2_80_AP3_95()

    # TODO(b/182936315): @test_tracker_info(uuid=???)
    def test_autojoin_Ap1_5gto2g_AP1_20_AP2_80_AP3_95(self):
        super().test_autojoin_Ap1_5gto2g_AP1_20_AP2_80_AP3_95()

    """ Tests End """
