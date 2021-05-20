#!/usr/bin/env python3
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


import time
from acts import asserts
from acts import signals
from acts.test_decorators import test_tracker_info
import acts_contrib.test_utils.wifi.wifi_test_utils as wutils
from acts_contrib.test_utils.wifi import wifi_constants
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest

WifiEnums = wutils.WifiEnums
WAIT_BRIDGED_AP_LAUNCH = 5


class WifiBridgedApTest(WifiBaseTest):
    """WiFi BridgedAp test class.

    Test Bed Requirement:
        * 3 Android devices.
    """

    def setup_class(self):
        super().setup_class()

        if len(self.android_devices) == 3:
            self.dut = self.android_devices[0]
            self.client1 = self.android_devices[1]
            self.client2 = self.android_devices[2]
        else:
            raise signals.TestAbortClass("WifiBridgedApTest requires 3 DUTs")

        if not self.dut.droid.wifiIsBridgedApConcurrencySupported():
            raise signals.TestAbortClass("Legacy phone is not supported")

        for ad in self.android_devices:
            wutils.wifi_test_device_init(ad)

        req_params = ["dbs_supported_models"]
        opt_param = ["cnss_diag_file", "pixel_models"]

        self.unpack_userparams(
            req_param_names=req_params, opt_param_names=opt_param)

    def setup_test(self):
        super().setup_test()
        for ad in self.android_devices:
            wutils.reset_wifi(ad)
        wutils.wifi_toggle_state(self.dut, False)
        wutils.wifi_toggle_state(self.client1, True)
        wutils.wifi_toggle_state(self.client2, True)

    def teardown_test(self):
        super().teardown_test()
        if self.dut.droid.wifiIsApEnabled():
            wutils.stop_wifi_tethering(self.dut)
        for ad in self.android_devices:
            wutils.reset_wifi(ad)
            wutils.set_wifi_country_code(
                ad, wutils.WifiEnums.CountryCode.US)

    def teardown_class(self):
        super().teardown_class()
        for ad in self.android_devices:
            wutils.reset_wifi(ad)
        if "AccessPoint" in self.user_params:
            del self.user_params["reference_networks"]
            del self.user_params["open_network"]

    def two_clients_connect_to_wifi_network(self, dut1, dut2, config):
        """Connect two clients to different BridgedAp instances.
           This function will be called only when BridgedAp ON.

        Args:
            config: Wi-Fi config, e.g., {"SSID": "xxx", "password": "xxx"}
        Steps:
            Register SoftAp Callback.
            Get SoftAp Infos.
            Get BSSIDs from Infos.
            Connect two clients to different BridgedAp instances.
        """
        # Make sure 2 instances enabled, and get BSSIDs from BridgedAp Infos.
        callbackId = self.dut.droid.registerSoftApCallback()
        infos = wutils.get_current_softap_infos(self.dut, callbackId, True)
        self.dut.droid.unregisterSoftApCallback(callbackId)

        if len(infos) == 0:
            raise signals.TestFailure("No BridgedAp instance")
        elif len(infos) == 1:
            raise signals.TestFailure(
                "Only one BridgedAp instance, should be two")
        else:
            bssid_5g = infos[0][wifi_constants.SOFTAP_INFO_BSSID_CALLBACK_KEY]
            bssid_2g = infos[1][wifi_constants.SOFTAP_INFO_BSSID_CALLBACK_KEY]

        # Two configs for BridgedAp 2G and 5G instances.
        config_5g = config.copy()
        config_2g = config.copy()
        config_5g[WifiEnums.BSSID_KEY] = bssid_5g
        config_2g[WifiEnums.BSSID_KEY] = bssid_2g

        # Connect two clients to BridgedAp.
        wutils.connect_to_wifi_network(dut1, config_5g,
                                       check_connectivity=False)
        wutils.connect_to_wifi_network(dut2, config_2g,
                                       check_connectivity=False)

        # Verify if Clients connect to the expected BridgedAp instances.
        client1_bssid = wutils.get_wlan0_link(
            self.client1)[wifi_constants.SOFTAP_INFO_BSSID_CALLBACK_KEY]
        client2_bssid = wutils.get_wlan0_link(
            self.client2)[wifi_constants.SOFTAP_INFO_BSSID_CALLBACK_KEY]
        asserts.assert_true(client1_bssid == bssid_5g,
                            "Client1 does not connect to the 5G instance")
        asserts.assert_true(client2_bssid == bssid_2g,
                            "Client2 does not connect to the 2G instance")

    @test_tracker_info(uuid="6f776b4a-b080-4b52-a330-52aa641b18f2")
    def test_two_clients_ping_on_bridged_ap_band_2_and_5_with_wpa3_in_country_us(self):
        """Test clients on different instances can ping each other.

        Steps:
            Backup config.
            Make sure clients support WPA3 SAE.
            Make sure DUT is able to enable BridgedAp.
            Enable BridgedAp with bridged configuration.
            RegisterSoftApCallback.
            Check the bridged AP enabled succeed.
            Force client#1 connect to 5G.
            Force client#2 connect to 2.4G.
            Trigger client#1 and client#2 each other.
            Restore config.
        """
        # Backup config
        original_softap_config = self.dut.droid.wifiGetApConfiguration()

        # Make sure clients support WPA3 SAE.
        client1_supported = self.client1.droid.wifiIsWpa3SaeSupported()
        client2_supported = self.client2.droid.wifiIsWpa3SaeSupported()
        asserts.skip_if(not (client1_supported and client2_supported),
                        "Clients do not support WPA3 SAE")
        # Make sure DUT is able to enable BridgedAp.
        is_supported = wutils.check_available_channels_in_bands_2_5(
            self.dut, wutils.WifiEnums.CountryCode.US)
        asserts.skip_if(not is_supported, "BridgedAp is not supported in {}"
                        .format(wutils.WifiEnums.CountryCode.US))

        # Enable BridgedAp
        config = wutils.create_softap_config()
        config[WifiEnums.SECURITY] = WifiEnums.SoftApSecurityType.WPA3_SAE
        wutils.save_wifi_soft_ap_config(
            self.dut, config,
            bands=[WifiEnums.WIFI_CONFIG_SOFTAP_BAND_2G,
                   WifiEnums.WIFI_CONFIG_SOFTAP_BAND_2G_5G])
        wutils.start_wifi_tethering_saved_config(self.dut)
        # Wait 5 seconds for BridgedAp launch.
        time.sleep(WAIT_BRIDGED_AP_LAUNCH)

        self.two_clients_connect_to_wifi_network(self.client1, self.client2,
                                                 config)
        # Trigger client#1 and client#2 ping each other.
        wutils.validate_ping_between_two_clients(self.client1, self.client2)

        # Restore config
        wutils.save_wifi_soft_ap_config(self.dut, original_softap_config)
