#!/usr/bin/env python3.4
#
#   Copyright 2019 - The Android Open Source Project
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
import acts.utils

from acts import asserts
from acts.controllers.ap_lib import hostapd_constants
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest

WifiEnums = wutils.WifiEnums

class WifiWpa3OweTest(WifiBaseTest):
    """Tests for APIs in Android's WifiManager class.

    Test Bed Requirement:
    * At least one Android device and atleast two Access Points.
    * Several Wi-Fi networks visible to the device.
    """

    def setup_class(self):
        super().setup_class()

        self.dut = self.android_devices[0]
        self.dut_client = self.android_devices[1]
        wutils.wifi_test_device_init(self.dut)
        wutils.wifi_test_device_init(self.dut_client)
        req_params = ["owe_networks", "wpa3_personal"]
        opt_param = []
        self.unpack_userparams(
            req_param_names=req_params, opt_param_names=opt_param)
        wutils.wifi_toggle_state(self.dut, True)
        wutils.wifi_toggle_state(self.dut_client, True)
        self.owe_2g = self.owe_networks[0]["2g"]
        self.owe_5g = self.owe_networks[0]["5g"]
        self.wpa3_personal_2g = self.wpa3_personal[0]["2g"]
        self.wpa3_personal_5g = self.wpa3_personal[0]["5g"]

    def setup_test(self):
        for ad in self.android_devices:
            ad.droid.wakeLockAcquireBright()
            ad.droid.wakeUpNow()
            wutils.wifi_toggle_state(ad, True)

    def teardown_test(self):
        for ad in self.android_devices:
            ad.droid.wakeLockRelease()
            ad.droid.goToSleepNow()
        wutils.reset_wifi(self.dut)
        wutils.reset_wifi(self.dut_client)

    def on_fail(self, test_name, begin_time):
        self.dut.cat_adb_log(test_name, begin_time)
        self.dut.take_bug_report(test_name, begin_time)

    """Helper Functions"""

    """Tests"""

    @test_tracker_info(uuid="a7755f1f-5740-4d45-8c29-3711172b1bd7")
    def test_connect_to_owe_2g(self):
        wutils.start_wifi_connection_scan_and_ensure_network_found(self.dut,
            self.owe_2g[WifiEnums.SSID_KEY])
        wutils.connect_to_wifi_network(self.dut, self.owe_2g )

    @test_tracker_info(uuid="9977765e-03da-4614-ab96-4c1597101118")
    def test_connect_to_owe_5g(self):
        wutils.start_wifi_connection_scan_and_ensure_network_found(self.dut,
            self.owe_5g[WifiEnums.SSID_KEY])
        wutils.connect_to_wifi_network(self.dut, self.owe_5g)

    @test_tracker_info(uuid="3670702a-3d78-4184-b5e1-7fcf5fa48fd8")
    def test_connect_to_wpa3_personal_2g(self):
        wutils.start_wifi_connection_scan_and_ensure_network_found(self.dut,
            self.wpa3_personal_2g[WifiEnums.SSID_KEY])
        wutils.connect_to_wifi_network(self.dut, self.wpa3_personal_2g)

    @test_tracker_info(uuid="c4528eaf-7960-4ecd-8f11-d5439bdf1c58")
    def test_connect_to_wpa3_personal_5g(self):
        wutils.start_wifi_connection_scan_and_ensure_network_found(self.dut,
            self.wpa3_personal_5g[WifiEnums.SSID_KEY])
        wutils.connect_to_wifi_network(self.dut, self.wpa3_personal_5g)

    @test_tracker_info(uuid="a8fb46be-3487-4dc8-a393-5af992b27f45")
    def test_connect_to_wpa3_personal_reconnection(self):
        """ This is to catch auth reject which is caused by PMKSA cache.
            Steps:
            ------------------------------
            1. Connect STA to WPA3 AP
            2. Turn off the WiFi or connect to a different AP
            3. Turn on the WiFi or connect back to WPA3 AP.
            4. Initial connect request fails
               Second connect request from framework succeeds.
        """
        wutils.start_wifi_connection_scan_and_ensure_network_found(self.dut,
            self.wpa3_personal_2g[WifiEnums.SSID_KEY])
        wutils.connect_to_wifi_network(self.dut, self.wpa3_personal_2g)
        wutils.toggle_wifi_off_and_on(self.dut)
        wutils.start_wifi_connection_scan_and_ensure_network_found(self.dut,
            self.wpa3_personal_2g[WifiEnums.SSID_KEY])
        wutils.connect_to_wifi_network(self.dut, self.wpa3_personal_2g)
