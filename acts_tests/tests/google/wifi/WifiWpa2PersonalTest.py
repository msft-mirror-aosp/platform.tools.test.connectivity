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


import acts_contrib.test_utils.wifi.wifi_test_utils as wutils
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest
from acts.controllers.openwrt_lib.openwrt_constants import OpenWrtWifiSecurity
from acts import asserts


WifiEnums = wutils.WifiEnums


class WifiWpa2PersonalTest(WifiBaseTest):
  """ Wi-Fi WPA2 test

      Test Bed Requirement:
        * One Android device
        * One OpenWrt Wi-Fi AP.
  """
  def setup_class(self):
    super().setup_class()
    self.dut = self.android_devices[0]

    if 'OpenWrtAP' in self.user_params:
      self.openwrt = self.access_points[0]
      self.configure_openwrt_ap_and_start(wpa_network=True)

    opt_params = ["pixel_models", "cnss_diag_file"]
    self.unpack_userparams(opt_params)
    self.wpa2_psk_2g = self.wpa_networks[0]["2g"]
    self.wpa2_psk_5g = self.wpa_networks[0]["5g"]

  def setup_test(self):
    super().setup_test()
    for ad in self.android_devices:
      ad.droid.wakeLockAcquireBright()
      ad.droid.wakeUpNow()
      wutils.wifi_toggle_state(ad, True)

  def teardown_test(self):
    super().teardown_test()
    for ad in self.android_devices:
      ad.droid.wakeLockRelease()
      ad.droid.goToSleepNow()
    wutils.reset_wifi(self.dut)

  def verify_wpa_network_encryption(self, encryption):
    result = wutils.get_wlan0_link(self.dut)
    if encryption == 'psk2+ccmp':
      asserts.assert_true(
          result['pairwise_cipher'] == 'CCMP' and
          result['group_cipher'] == 'CCMP' and
          result['key_mgmt'] == "WPA2-PSK",
          'DUT does not connect to {} encryption network'.format(encryption))
    elif encryption == 'psk2+tkip':
      asserts.assert_true(
          result['pairwise_cipher'] == 'TKIP' and
          result['group_cipher'] == 'TKIP' and
          result['key_mgmt'] == "WPA2-PSK",
          'DUT does not connect to {} encryption network'.format(encryption))
    elif encryption == 'psk2+tkip+ccmp':
      asserts.assert_true(
          result['pairwise_cipher'] == 'CCMP' and
          result['group_cipher'] == 'TKIP' and
          result['key_mgmt'] == "WPA2-PSK",
          'DUT does not connect to {} encryption network'.format(encryption))

  """ Tests"""

  def test_connect_to_wpa2_psk_ccmp_2g(self):
    """Change AP's security type to "WPA2" and cipher to "CCMP".
       Connect to 2g network.
    """
    self.openwrt.log.info("Enable WPA2-PSK CCMP on OpenWrt AP")
    self.openwrt.set_wpa_encryption(OpenWrtWifiSecurity.WPA2_PSK_CCMP)
    wutils.connect_to_wifi_network(self.dut, self.wpa2_psk_2g)
    self.verify_wpa_network_encryption(OpenWrtWifiSecurity.WPA2_PSK_CCMP)

  def test_connect_to_wpa2_psk_ccmp_5g(self):
    """Change AP's security type to "WPA2" and cipher to "CCMP".
       Connect to 5g network.
    """
    self.openwrt.log.info("Enable WPA2-PSK CCMP on OpenWrt AP")
    self.openwrt.set_wpa_encryption(OpenWrtWifiSecurity.WPA2_PSK_CCMP)
    wutils.connect_to_wifi_network(self.dut, self.wpa2_psk_5g)
    self.verify_wpa_network_encryption(OpenWrtWifiSecurity.WPA2_PSK_CCMP)

  def test_connect_to_wpa2_psk_tkip_2g(self):
    """Change AP's security type to "WPA2" and cipher to "TKIP".
       Connect to 2g network.
    """
    self.openwrt.log.info("Enable WPA2-PSK TKIP on OpenWrt AP")
    self.openwrt.set_wpa_encryption(OpenWrtWifiSecurity.WPA2_PSK_TKIP)
    wutils.connect_to_wifi_network(self.dut, self.wpa2_psk_2g)
    self.verify_wpa_network_encryption(OpenWrtWifiSecurity.WPA2_PSK_TKIP)

  def test_connect_to_wpa2_psk_tkip_5g(self):
    """Change AP's security type to "WPA2" and cipher to "TKIP".
       Connect to 5g network.
    """
    self.openwrt.log.info("Enable WPA2-PSK TKIP on OpenWrt AP")
    self.openwrt.set_wpa_encryption(OpenWrtWifiSecurity.WPA2_PSK_TKIP)
    wutils.connect_to_wifi_network(self.dut, self.wpa2_psk_5g)
    self.verify_wpa_network_encryption(OpenWrtWifiSecurity.WPA2_PSK_TKIP)

  def test_connect_to_wpa2_psk_tkip_and_ccmp_2g(self):
    """Change AP's security type to "WPA2" and cipher to "CCMP and TKIP".
       Connect to 2g network.
    """
    self.openwrt.log.info("Enable WPA2-PSK CCMP and TKIP on OpenWrt AP")
    self.openwrt.set_wpa_encryption(OpenWrtWifiSecurity.WPA2_PSK_TKIP_AND_CCMP)
    wutils.connect_to_wifi_network(self.dut, self.wpa2_psk_2g)
    self.verify_wpa_network_encryption(
        OpenWrtWifiSecurity.WPA2_PSK_TKIP_AND_CCMP)

  def test_connect_to_wpa2_psk_tkip_and_ccmp_5g(self):
    """Change AP's security type to "WPA2" and cipher to "CCMP and TKIP".
       Connect to 5g network.
    """
    self.openwrt.log.info("Enable WPA2-PSK CCMP and TKIP on OpenWrt AP")
    self.openwrt.set_wpa_encryption(OpenWrtWifiSecurity.WPA2_PSK_TKIP_AND_CCMP)
    wutils.connect_to_wifi_network(self.dut, self.wpa2_psk_5g)
    self.verify_wpa_network_encryption(
        OpenWrtWifiSecurity.WPA2_PSK_TKIP_AND_CCMP)
