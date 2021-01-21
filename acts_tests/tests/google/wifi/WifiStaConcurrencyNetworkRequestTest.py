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

import itertools
import pprint
import queue
import time

import acts.base_test
import acts.signals as signals
import acts_contrib.test_utils.wifi.wifi_test_utils as wutils

from acts import asserts
from acts.controllers.android_device import SL4A_APK_NAME
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest
from acts_contrib.test_utils.wifi import wifi_constants

WifiEnums = wutils.WifiEnums

# Network request timeout to use.
NETWORK_REQUEST_TIMEOUT_MS = 60 * 1000
# Timeout to wait for instant failure.
NETWORK_REQUEST_INSTANT_FAILURE_TIMEOUT_SEC = 5

class WifiStaConcurrencyNetworkRequestTest(WifiBaseTest):
    """STA + STA Tests for concurrency between intenet connectivity &
    peer to peer connectivity using NetworkRequest with WifiNetworkSpecifier API surface.

    Test Bed Requirement:
    * one Android device
    * Several Wi-Fi networks visible to the device, including an open Wi-Fi
      network.
    """
    def __init__(self, configs):
        super().__init__(configs)
        self.enable_packet_log = True

    def setup_class(self):
        super().setup_class()

        self.dut = self.android_devices[0]
        wutils.wifi_test_device_init(self.dut)
        req_params = ["sta_concurrency_supported_models"]
        opt_param = [
            "open_network", "reference_networks"
        ]
        self.unpack_userparams(
            req_param_names=req_params, opt_param_names=opt_param)

        asserts.abort_class_if(
                self.dut.model not in self.sta_concurrency_supported_models,
                "Device %s doesn't support STA+STA, skipping tests")

        if "AccessPoint" in self.user_params:
            self.legacy_configure_ap_and_start(wpa_network=True,
                                               wep_network=True)
        elif "OpenWrtAP" in self.user_params:
            self.configure_openwrt_ap_and_start(open_network=True,
                                                wpa_network=True,
                                                wep_network=True)

        asserts.assert_true(
            len(self.reference_networks) > 0,
            "Need at least one reference network with psk.")
        self.wpa_psk_2g = self.reference_networks[0]["2g"]
        self.wpa_psk_5g = self.reference_networks[0]["5g"]
        self.open_2g = self.open_network[0]["2g"]
        self.open_5g = self.open_network[0]["5g"]

    def setup_test(self):
        super().setup_test()
        self.dut.droid.wakeLockAcquireBright()
        self.dut.droid.wakeUpNow()
        self.remove_approvals()
        self.clear_user_disabled_networks()
        wutils.wifi_toggle_state(self.dut, True)
        self.dut.ed.clear_all_events()

    def teardown_test(self):
        super().teardown_test()
        self.dut.droid.wakeLockRelease()
        self.dut.droid.goToSleepNow()
        self.dut.droid.wifiReleaseNetworkAll()
        self.dut.droid.wifiDisconnect()
        wutils.reset_wifi(self.dut)
        # Ensure we disconnected from the current network before the next test.
        if self.dut.droid.wifiGetConnectionInfo()["supplicant_state"] != "disconnected":
            wutils.wait_for_disconnect(self.dut)
        wutils.wifi_toggle_state(self.dut, False)
        self.dut.ed.clear_all_events()

    def teardown_class(self):
        if "AccessPoint" in self.user_params:
            del self.user_params["reference_networks"]
            del self.user_params["open_network"]

    """Helper Functions"""
    def remove_approvals(self):
        self.dut.log.debug("Removing all approvals from sl4a app")
        self.dut.adb.shell(
            "cmd wifi network-requests-remove-user-approved-access-points"
            + " " + SL4A_APK_NAME)

    def clear_user_disabled_networks(self):
        self.dut.log.debug("Clearing user disabled networks")
        self.dut.adb.shell(
            "cmd wifi clear-user-disabled-networks")

    @test_tracker_info(uuid="")
    def test_connect_to_wpa_psk_2g_p2p_while_connected_to_wpa_psk_5g_internet(self):
        """
        Initiates a connection to a peer to peer network via network request while
        already connected to an internet connectivity network.

        Steps:
        1. Connect to WPA-PSK 5G network for internet connectivity.
        2. Send a network specifier with the specific SSID/credentials of
           WPA-PSK 2G network.
        3. Wait for platform to scan and find matching networks.
        4. Simulate user selecting the network.
        5. Ensure that the device connects to the network.
        6. Ensure that the device remains connected to both the networks.
        """
        wutils.connect_to_wifi_network(self.dut, self.wpa_psk_5g)
        wutils.wifi_connect_using_network_request(self.dut, self.wpa_psk_2g,
                                                  self.wpa_psk_2g)

    @test_tracker_info(uuid="")
    def test_connect_to_wpa_psk_2g_internet_while_connected_to_wpa_psk_5g_p2p(self):
        """
        Initiates a connection to a peer to peer network via network request while
        already connected to an internet connectivity network.

        Steps:
        1. Send a network specifier with the specific SSID/credentials of
           WPA-PSK 5G network.
        2. Wait for platform to scan and find matching networks.
        3. Simulate user selecting the network.
        4. Ensure that the device connects to the network.
        5. Connect to WPA-PSK 2G network for internet connectivity.
        6. Ensure that the device remains connected to both the networks.
        """
        wutils.wifi_connect_using_network_request(self.dut, self.wpa_psk_5g,
                                                  self.wpa_psk_5g)
        wutils.connect_to_wifi_network(self.dut, self.wpa_psk_2g)
