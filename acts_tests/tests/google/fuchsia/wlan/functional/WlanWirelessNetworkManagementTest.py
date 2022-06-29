#!/usr/bin/env python3
#
#   Copyright 2022 - The Android Open Source Project
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

import re

from acts import asserts
from acts import utils
from acts.controllers.access_point import setup_ap
from acts.controllers.ap_lib import hostapd_constants
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest
from acts_contrib.test_utils.abstract_devices.wlan_device import create_wlan_device


class WlanWirelessNetworkManagementTest(WifiBaseTest):
    """Tests Fuchsia's Wireless Network Management (AKA 802.11v) support.

    Testbed Requirements:
    * One Fuchsia device
    * One Whirlwind access point

    Existing Fuchsia drivers do not yet support WNM features, so this suite verifies that
    WNM features are not advertised or used by the Fuchsia DUT. When WNM features are
    supported, tests will be added that confirm the proper functioning of those features.
    """

    def setup_class(self):
        if 'dut' in self.user_params and self.user_params[
                'dut'] != 'fuchsia_devices':
            raise AttributeError(
                'WlanWirelessNetworkManagementTest is only relevant for Fuchsia devices.'
            )

        self.dut = create_wlan_device(self.fuchsia_devices[0])
        if self.dut.device.association_mechanism != 'policy':
            raise AttributeError('Must use WLAN policy layer to test WNM.')
        self.access_point = self.access_points[0]

    def teardown_class(self):
        self.dut.disconnect()
        self.access_point.stop_all_aps()

    def teardown_test(self):
        self.dut.disconnect()
        self.download_ap_logs()
        self.access_point.stop_all_aps()

    def on_fail(self, test_name: str, begin_time: str):
        super().on_fail(test_name, begin_time)
        self.access_point.stop_all_aps()

    def on_exception(self, test_name: str, begin_time: str):
        super().on_exception(test_name, begin_time)
        self.dut.disconnect()
        self.access_point.stop_all_aps()

    def setup_ap(self,
                 wnm_features: frozenset[
                     hostapd_constants.WnmFeature] = frozenset()):
        """Sets up an AP using the provided parameters.

        Args:
            wnm_features: Wireless Network Management features to enable.
        """
        ssid = utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G)
        setup_ap(access_point=self.access_point,
                 profile_name='whirlwind',
                 channel=hostapd_constants.AP_DEFAULT_CHANNEL_2G,
                 ssid=ssid,
                 security=None,
                 wnm_features=wnm_features)
        self.ssid = ssid

    def _get_client_mac(self) -> str:
        """Get the MAC address of the DUT client interface.

        Returns:
            str, MAC address of the DUT client interface.
        Raises:
            ValueError if there is no DUT client interface.
            ConnectionError if the DUT interface query fails.
        """
        wlan_ifaces = self.dut.device.wlan_lib.wlanGetIfaceIdList()
        if wlan_ifaces.get('error'):
            raise ConnectionError('Failed to get wlan interface IDs: %s' %
                                  wlan_ifaces['error'])

        for wlan_iface in wlan_ifaces['result']:
            iface_info = self.dut.device.wlan_lib.wlanQueryInterface(
                wlan_iface)
            if iface_info.get('error'):
                raise ConnectionError('Failed to query wlan iface: %s' %
                                      iface_info['error'])

            if iface_info['result']['role'] == 'Client':
                return utils.mac_address_list_to_str(
                    iface_info['result']['sta_addr'])
        raise ValueError(
            'Failed to get client interface mac address. No client interface found.'
        )

    def test_bss_transition_ap_supported_dut_unsupported(self):
        wnm_features = frozenset(
            [hostapd_constants.WnmFeature.BSS_TRANSITION_MANAGEMENT])
        self.setup_ap(wnm_features)
        asserts.assert_true(self.dut.associate(self.ssid),
                            'Failed to associate.')
        asserts.assert_true(self.dut.is_connected(), 'Failed to connect.')
        client_mac = self._get_client_mac()

        ext_capabilities = self.access_point.get_sta_extended_capabilities(
            self.access_point.wlan_2g, client_mac)
        asserts.assert_false(
            ext_capabilities.bss_transition,
            'DUT is incorrectly advertising BSS Transition Management support')

    def test_wnm_sleep_mode_ap_supported_dut_unsupported(self):
        wnm_features = frozenset([hostapd_constants.WnmFeature.WNM_SLEEP_MODE])
        self.setup_ap(wnm_features)
        asserts.assert_true(self.dut.associate(self.ssid),
                            'Failed to associate.')
        asserts.assert_true(self.dut.is_connected(), 'Failed to connect.')
        client_mac = self._get_client_mac()

        ext_capabilities = self.access_point.get_sta_extended_capabilities(
            self.access_point.wlan_2g, client_mac)
        asserts.assert_false(
            ext_capabilities.wnm_sleep_mode,
            'DUT is incorrectly advertising WNM Sleep Mode support')
