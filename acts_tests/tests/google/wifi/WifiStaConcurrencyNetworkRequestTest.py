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

import acts.asserts as asserts
from acts.controllers.android_device import SL4A_APK_NAME
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest
import acts_contrib.test_utils.net.connectivity_const as cconsts
import acts_contrib.test_utils.wifi.wifi_test_utils as wutils
import acts_contrib.test_utils.wifi.aware.aware_test_utils as autils

WifiEnums = wutils.WifiEnums

WIFI_NETWORK_AP_CHANNEL_2G_1 = 1
WIFI_NETWORK_AP_CHANNEL_5G_1 = 36
WIFI_NETWORK_AP_CHANNEL_5G_DFS_1 = 132

WIFI_NETWORK_AP_CHANNEL_2G_2 = 2
WIFI_NETWORK_AP_CHANNEL_5G_2 = 38
WIFI_NETWORK_AP_CHANNEL_5G_DFS_2 = 134

class WifiStaConcurrencyNetworkRequestTest(WifiBaseTest):
    """STA + STA Tests for concurrency between intenet connectivity &
    peer to peer connectivity using NetworkRequest with WifiNetworkSpecifier
    API surface.

    Test Bed Requirement:
    * one Android device
    * Several Wi-Fi networks visible to the device, including an open Wi-Fi
      network.
    """
    def __init__(self, configs):
        super().__init__(configs)
        self.enable_packet_log = True
        self.p2p_key = None

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

        asserts.abort_class_if(
            "OpenWrtAP" not in self.user_params,
            "Setup doesn't support OpenWrt AP, skipping tests")


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
        self.disconnect_both()
        self.dut.droid.wakeLockRelease()
        self.dut.droid.goToSleepNow()
        self.dut.droid.wifiDisconnect()
        wutils.reset_wifi(self.dut)
        # Ensure we disconnected from the current network before the next test.
        if self.dut.droid.wifiGetConnectionInfo()["supplicant_state"] != "disconnected":
            wutils.wait_for_disconnect(self.dut)
        wutils.wifi_toggle_state(self.dut, False)
        self.dut.ed.clear_all_events()
        # Reset access point state.
        for ap in self.access_points:
            ap.close()

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

    def register_network_callback_for_internet(self):
        self.dut.log.debug("Registering network callback for wifi internet connectivity")
        network_request = {
            cconsts.NETWORK_CAP_TRANSPORT_TYPE_KEY :
                cconsts.NETWORK_CAP_TRANSPORT_WIFI,
            cconsts.NETWORK_CAP_CAPABILITY_KEY :
                [cconsts.NETWORK_CAP_CAPABILITY_INTERNET]
        }
        key = self.dut.droid.connectivityRegisterNetworkCallback(network_request)
        return key

    def connect_to_internet_and_wait_for_on_available(self, network):
        self.dut.log.info("Triggering internet connection after registering "
                           "network callback")
        self.internet_request_key = (
            self.register_network_callback_for_internet())
        wutils.connect_to_wifi_network(self.dut, network)
        # Ensure that the internet connection completed and we got the
        # ON_AVAILABLE callback.
        autils.wait_for_event_with_keys(
            self.dut,
            cconsts.EVENT_NETWORK_CALLBACK,
            20,
            (cconsts.NETWORK_CB_KEY_ID, self.internet_request_key),
            (cconsts.NETWORK_CB_KEY_EVENT, cconsts.NETWORK_CB_AVAILABLE))

    def connect_to_p2p_and_wait_for_on_available(self, network):
        self.p2p_key = wutils.wifi_connect_using_network_request(self.dut,
                                                                 network,
                                                                 network)

    def ensure_both_connections_are_active(self):
        self.dut.log.info("Ensuring both connections are active")
        network_caps = (
            self.dut.droid.connectivityNetworkGetAllCapabilities())
        self.dut.log.info("Active network caps: %s", network_caps)
        num_wifi_networks = 0
        for network_cap in network_caps:
            transport_types = (
                network_cap[cconsts.NETWORK_CAP_TRANSPORT_TYPE_KEY])
            if cconsts.NETWORK_CAP_TRANSPORT_WIFI in transport_types:
              num_wifi_networks += 1
        asserts.assert_equal(2, num_wifi_networks, "Expected 2 wifi networks")


    def ensure_both_connections_are_active_and_dont_disconnect(self):
        self.ensure_both_connections_are_active()

        # Don't use the key_id in event to ensure there are no disconnects
        # from either connection.
        self.dut.log.info("Ensuring no connection loss")
        autils.fail_on_event_with_keys(
            self.dut,
            cconsts.EVENT_NETWORK_CALLBACK,
            20,
            (cconsts.NETWORK_CB_KEY_EVENT, cconsts.NETWORK_CB_LOST))

    def disconnect_both(self):
        self.dut.log.info("Disconnecting both connections")
        if self.p2p_key:
            asserts.assert_true(
                self.dut.droid.connectivityUnregisterNetworkCallback(
                    self.p2p_key),
                "Failed to release the p2p request")
            self.p2p_key = None
        self.dut.droid.wifiDisconnect();


    @test_tracker_info(uuid="")
    def test_connect_to_2g_p2p_while_connected_to_5g_internet(self):
        """
        Initiates a connection to a peer to peer network via network request while
        already connected to an internet connectivity network.

        Steps:
        1. Setup 5G & 2G band WPA-PSK networks.
        2. Connect to WPA-PSK 5G network for internet connectivity.
        3. Send a network specifier with the specific SSID/credentials of
           WPA-PSK 2G network.
        4. Wait for platform to scan and find matching networks.
        5. Simulate user selecting the network.
        6. Ensure that the device connects to the network.
        7. Ensure that the device remains connected to both the networks.
        8. Disconnect both connections.
        """
        self.configure_openwrt_ap_and_start(
            wpa_network=True,
            channel_2g=WIFI_NETWORK_AP_CHANNEL_2G_1,
            channel_5g=WIFI_NETWORK_AP_CHANNEL_5G_1,
            ap_count=1)

        self.connect_to_internet_and_wait_for_on_available(
            self.wpa_networks[0]["5g"])
        self.connect_to_p2p_and_wait_for_on_available(
            self.wpa_networks[0]["2g"])

        self.ensure_both_connections_are_active_and_dont_disconnect()


    @test_tracker_info(uuid="")
    def test_connect_to_2g_internet_while_connected_to_5g_p2p(self):
        """
        Initiates a connection to a peer to peer network via network request while
        already connected to an internet connectivity network.

        Steps:
        1. Setup 5G & 2G band WPA-PSK networks.
        2. Send a network specifier with the specific SSID/credentials of
           WPA-PSK 5G network.
        3. Wait for platform to scan and find matching networks.
        4. Simulate user selecting the network.
        5. Ensure that the device connects to the network.
        6. Connect to WPA-PSK 2G network for internet connectivity.
        7. Ensure that the device remains connected to both the networks.
        8. Disconnect both connections.
        """
        self.configure_openwrt_ap_and_start(
            wpa_network=True,
            channel_2g=WIFI_NETWORK_AP_CHANNEL_2G_1,
            channel_5g=WIFI_NETWORK_AP_CHANNEL_5G_1,
            ap_count=1)

        self.connect_to_p2p_and_wait_for_on_available(
            self.wpa_networks[0]["5g"])
        self.connect_to_internet_and_wait_for_on_available(
            self.wpa_networks[0]["2g"])

        self.ensure_both_connections_are_active_and_dont_disconnect()


    @test_tracker_info(uuid="")
    def test_connect_to_2g_internet_while_connected_to_2g_p2p(self):
        """
        Initiates a connection to a peer to peer network via network request while
        already connected to an internet connectivity network.

        Steps:
        1. Setup 2 5G & 2G band WPA-PSK networks.
        2. Send a network specifier with the specific SSID/credentials of
           WPA-PSK 2G network.
        3. Wait for platform to scan and find matching networks.
        4. Simulate user selecting the network.
        5. Ensure that the device connects to the network.
        6. Connect to WPA-PSK 2G network for internet connectivity.
        7. Ensure that the device remains connected to both the networks.
        8. Disconnect both connections.
        """
        self.configure_openwrt_ap_and_start(
            wpa_network=True,
            channel_2g=WIFI_NETWORK_AP_CHANNEL_2G_1,
            channel_2g_ap2=WIFI_NETWORK_AP_CHANNEL_2G_2,
            ap_count=2)

        self.connect_to_p2p_and_wait_for_on_available(
            self.wpa_networks[0]["2g"])
        self.connect_to_internet_and_wait_for_on_available(
            self.wpa_networks[1]["2g"])

        self.ensure_both_connections_are_active_and_dont_disconnect()


    @test_tracker_info(uuid="")
    def test_connect_to_5g_internet_while_connected_to_5g_p2p(self):
        """
        Initiates a connection to a peer to peer network via network request while
        already connected to an internet connectivity network.

        Steps:
        1. Setup 2 5G & 2G band WPA-PSK networks.
        2. Send a network specifier with the specific SSID/credentials of
           WPA-PSK 5G network.
        3. Wait for platform to scan and find matching networks.
        4. Simulate user selecting the network.
        5. Ensure that the device connects to the network.
        6. Connect to WPA-PSK 5G network for internet connectivity.
        7. Ensure that the device remains connected to both the networks.
        8. Disconnect both connections.
        """
        self.configure_openwrt_ap_and_start(
            wpa_network=True,
            channel_5g=WIFI_NETWORK_AP_CHANNEL_5G_1,
            channel_5g_ap2=WIFI_NETWORK_AP_CHANNEL_5G_2,
            ap_count=2)

        self.connect_to_p2p_and_wait_for_on_available(
            self.wpa_networks[0]["5g"])
        self.connect_to_internet_and_wait_for_on_available(
            self.wpa_networks[1]["5g"])

        self.ensure_both_connections_are_active_and_dont_disconnect()

    @test_tracker_info(uuid="")
    def test_connect_to_5g_dfs_internet_while_connected_to_5g_dfs_p2p(self):
        """
        Initiates a connection to a peer to peer network via network request while
        already connected to an internet connectivity network.

        Steps:
        1. Setup 2 5G-DFS & 2G band WPA-PSK networks.
        2. Send a network specifier with the specific SSID/credentials of
           WPA-PSK 5G-DFS network.
        3. Wait for platform to scan and find matching networks.
        4. Simulate user selecting the network.
        5. Ensure that the device connects to the network.
        6. Connect to WPA-PSK 5G network for internet connectivity.
        7. Ensure that the device remains connected to both the networks.
        8. Disconnect both connections.
        """
        self.configure_openwrt_ap_and_start(
            wpa_network=True,
            channel_5g=WIFI_NETWORK_AP_CHANNEL_5G_DFS_1,
            channel_5g_ap2=WIFI_NETWORK_AP_CHANNEL_5G_DFS_2,
            ap_count=2)

        self.connect_to_p2p_and_wait_for_on_available(
            self.wpa_networks[0]["5g"])
        self.connect_to_internet_and_wait_for_on_available(
            self.wpa_networks[1]["5g"])

        self.ensure_both_connections_are_active_and_dont_disconnect()

