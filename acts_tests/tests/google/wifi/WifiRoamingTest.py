#
#   Copyright 2017 - The Android Open Source Project
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

from acts import asserts
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.wifi import wifi_test_utils as wutils
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest


class WifiRoamingTest(WifiBaseTest):

    def setup_class(self):
        """Configure the required networks for testing roaming."""
        super().setup_class()

        self.dut = self.android_devices[0]
        wutils.wifi_test_device_init(self.dut)
        req_params = ["roaming_attn",]
        self.unpack_userparams(req_param_names=req_params,)

        if "AccessPoint" in self.user_params:
            self.legacy_configure_ap_and_start(ap_count=2)
        elif "OpenWrtAP" in self.user_params:
            self.configure_openwrt_ap_and_start(open_network=True,
                                                wpa_network=True,
                                                owe_network=True,
                                                sae_network=True,
                                                ap_count=2,
                                                mirror_ap=True)

    def teardown_class(self):
        self.dut.ed.clear_all_events()
        if "AccessPoint" in self.user_params:
            del self.user_params["reference_networks"]
            del self.user_params["open_network"]

    def setup_test(self):
        super().setup_test()
        self.dut.ed.clear_all_events()
        self.dut.droid.wakeLockAcquireBright()
        self.dut.droid.wakeUpNow()

    def teardown_test(self):
        super().teardown_test()
        self.dut.droid.wakeLockRelease()
        self.dut.droid.goToSleepNow()
        wutils.reset_wifi(self.dut)
        wutils.set_attns(self.attenuators, "default")

    ### Helper Methods ###

    def roaming_from_AP1_and_AP2(self, AP1_network, AP2_network):
        """Test roaming between two APs.

        Args:
            AP1_network: AP-1's network information.
            AP2_network: AP-2's network information.

        Steps:
        1. Make AP1 visible, AP2 not visible.
        2. Connect to AP1's ssid.
        3. Make AP1 not visible, AP2 visible.
        4. Expect DUT to roam to AP2.
        5. Validate connection information and ping.
        """
        wutils.set_attns(self.attenuators, "AP1_on_AP2_off", self.roaming_attn)
        wifi_config = AP1_network.copy()
        wifi_config.pop("bssid")
        wutils.connect_to_wifi_network(self.dut, wifi_config)
        self.log.info("Roaming from %s to %s", AP1_network, AP2_network)
        wutils.trigger_roaming_and_validate(
            self.dut, self.attenuators, "AP1_off_AP2_on", AP2_network,
            self.roaming_attn)

    ### Test Cases ###

    @test_tracker_info(uuid="db8a46f9-713f-4b98-8d9f-d36319905b0a")
    def test_roaming_between_AP1_to_AP2_open_2g(self):
        ap1_network = self.open_network[0]["2g"]
        ap2_network = self.open_network[1]["2g"]
        if "OpenWrtAP" in self.user_params:
            ap1_network["bssid"] = self.bssid_map[0]["2g"][ap1_network["SSID"]]
            ap2_network["bssid"] = self.bssid_map[1]["2g"][ap2_network["SSID"]]
        self.roaming_from_AP1_and_AP2(ap1_network, ap2_network)

    @test_tracker_info(uuid="0db67d9b-6ea9-4f40-acf2-155c4ecf9dc5")
    def test_roaming_between_AP1_to_AP2_open_5g(self):
        ap1_network = self.open_network[0]["5g"]
        ap2_network = self.open_network[1]["5g"]
        if "OpenWrtAP" in self.user_params:
            ap1_network["bssid"] = self.bssid_map[0]["5g"][ap1_network["SSID"]]
            ap2_network["bssid"] = self.bssid_map[1]["5g"][ap2_network["SSID"]]
        self.roaming_from_AP1_and_AP2(ap1_network, ap2_network)

    @test_tracker_info(uuid="eabc7319-d962-4bef-b679-725e9ff00420")
    def test_roaming_between_AP1_to_AP2_psk_2g(self):
        ap1_network = self.reference_networks[0]["2g"]
        ap2_network = self.reference_networks[1]["2g"]
        if "OpenWrtAP" in self.user_params:
            ap1_network["bssid"] = self.bssid_map[0]["2g"][ap1_network["SSID"]]
            ap2_network["bssid"] = self.bssid_map[1]["2g"][ap2_network["SSID"]]
        self.roaming_from_AP1_and_AP2(ap1_network, ap2_network)

    @test_tracker_info(uuid="1cf9c681-4ff0-45c1-9719-f01629f6a7f7")
    def test_roaming_between_AP1_to_AP2_psk_5g(self):
        ap1_network = self.reference_networks[0]["5g"]
        ap2_network = self.reference_networks[1]["5g"]
        if "OpenWrtAP" in self.user_params:
            ap1_network["bssid"] = self.bssid_map[0]["5g"][ap1_network["SSID"]]
            ap2_network["bssid"] = self.bssid_map[1]["5g"][ap2_network["SSID"]]
        self.roaming_from_AP1_and_AP2(ap1_network, ap2_network)

    @test_tracker_info(uuid="a28f7d2e-fae4-4e66-b633-7ee59f8b46e0")
    def test_roaming_between_AP1_to_AP2_owe_2g(self):
        ap1_network = self.owe_networks[0]["2g"]
        ap2_network = self.owe_networks[1]["2g"]
        if "OpenWrtAP" in self.user_params:
            ap1_network["bssid"] = self.bssid_map[0]["2g"][ap1_network["SSID"]]
            ap2_network["bssid"] = self.bssid_map[1]["2g"][ap2_network["SSID"]]
        self.roaming_from_AP1_and_AP2(ap1_network, ap2_network)

    @test_tracker_info(uuid="3c39110a-9336-4abd-b885-acbba85dc10d")
    def test_roaming_between_AP1_to_AP2_owe_5g(self):
        ap1_network = self.owe_networks[0]["5g"]
        ap2_network = self.owe_networks[1]["5g"]
        if "OpenWrtAP" in self.user_params:
            ap1_network["bssid"] = self.bssid_map[0]["5g"][ap1_network["SSID"]]
            ap2_network["bssid"] = self.bssid_map[1]["5g"][ap2_network["SSID"]]
        self.roaming_from_AP1_and_AP2(ap1_network, ap2_network)

    @test_tracker_info(uuid="68b2baf6-162a-44f2-a00d-4973e5ac9471")
    def test_roaming_between_AP1_to_AP2_sae_2g(self):
        ap1_network = self.sae_networks[0]["2g"]
        ap2_network = self.sae_networks[1]["2g"]
        if "OpenWrtAP" in self.user_params:
            ap1_network["bssid"] = self.bssid_map[0]["2g"][ap1_network["SSID"]]
            ap2_network["bssid"] = self.bssid_map[1]["2g"][ap2_network["SSID"]]
        self.roaming_from_AP1_and_AP2(ap1_network, ap2_network)

    @test_tracker_info(uuid="20e24ed3-0cd1-46dd-bd26-2183ffb443e6")
    def test_roaming_between_AP1_to_AP2_sae_5g(self):
        ap1_network = self.sae_networks[0]["5g"]
        ap2_network = self.sae_networks[1]["5g"]
        if "OpenWrtAP" in self.user_params:
            ap1_network["bssid"] = self.bssid_map[0]["5g"][ap1_network["SSID"]]
            ap2_network["bssid"] = self.bssid_map[1]["5g"][ap2_network["SSID"]]
        self.roaming_from_AP1_and_AP2(ap1_network, ap2_network)

    @test_tracker_info(uuid="3114d625-5cdd-4205-bb46-5a9d057dc80d")
    def test_roaming_fail_psk_2g(self):
        network = {'SSID':'test_roaming_fail', 'password':'roam123456@'}
        # AP2 network with incorrect password.
        network_fail = {'SSID':'test_roaming_fail', 'password':'roam123456@#$%^'}
        # Setup AP1 with the correct password.
        wutils.ap_setup(self, 0, self.access_points[0], network)
        network_bssid = self.access_points[0].get_bssid_from_ssid(
                network["SSID"], '2g')
        # Setup AP2 with the incorrect password.
        wutils.ap_setup(self, 1, self.access_points[1], network_fail)
        network_fail_bssid = self.access_points[1].get_bssid_from_ssid(
                network_fail["SSID"], '2g')
        network['bssid'] = network_bssid
        network_fail['bssid'] = network_fail_bssid
        try:
            # Initiate roaming with AP2 configured with incorrect password.
            self.roaming_from_AP1_and_AP2(network, network_fail)
        except:
            self.log.info("Roaming failed to AP2 with incorrect password.")
            # Re-configure AP2 after roaming failed, with correct password.
            self.log.info("Re-configuring AP2 with correct password.")
            wutils.ap_setup(self, 1, self.access_points[1], network)
        self.roaming_from_AP1_and_AP2(network, network_fail)
