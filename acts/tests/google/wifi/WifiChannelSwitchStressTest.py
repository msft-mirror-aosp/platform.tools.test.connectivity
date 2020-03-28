#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
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
import random
import re
import acts.test_utils.wifi.wifi_test_utils as wutils
import acts.test_utils.tel.tel_test_utils as tel_utils
import acts.utils as utils
from acts import asserts
from acts.test_decorators import test_tracker_info
from acts.test_utils.wifi.WifiBaseTest import WifiBaseTest
from acts import signals


WifiEnums = wutils.WifiEnums


class WifiChannelSwitchStressTest(WifiBaseTest):

    def setup_class(self):
        super().setup_class()
        self.dut = self.android_devices[0]
        self.dut_client = self.android_devices[1]
        utils.require_sl4a((self.dut, self.dut_client))

        req_params = ["dbs_supported_models"]
        opt_param = ["stress_count"]
        self.unpack_userparams(
            req_param_names=req_params, opt_param_names=opt_param)

        self.AP_IFACE = 'wlan0'
        if self.dut.model in self.dbs_supported_models:
            self.AP_IFACE = 'wlan1'

        for ad in self.android_devices:
            wutils.wifi_test_device_init(ad)
            utils.sync_device_time(ad)
            ad.droid.wifiSetCountryCode(wutils.WifiEnums.CountryCode.US)

    def setup_test(self):
        for ad in self.android_devices:
            ad.droid.wakeLockAcquireBright()
            ad.droid.wakeUpNow()

    def teardown_test(self):
        for ad in self.android_devices:
            ad.droid.wakeLockRelease()
            ad.droid.goToSleepNow()
            wutils.reset_wifi(ad)
        try:
            wutils.stop_wifi_tethering(self.dut)
        except signals.TestFailure:
            pass

    def on_fail(self, test_name, begin_time):
        for ad in self.android_devices:
            ad.take_bug_report(test_name, begin_time)
            ad.cat_adb_log(test_name, begin_time)

    def check_cell_data_and_enable(self):
        """Make sure that cell data is enabled if there is a sim present.

        If a sim is active, cell data needs to be enabled to allow provisioning
        checks through (when applicable).  This is done to relax hardware
        requirements on DUTs - without this check, running this set of tests
        after other wifi tests may cause failures.
        """

        if not self.dut.droid.telephonyIsDataEnabled():
            self.dut.log.info("need to enable data")
            self.dut.droid.telephonyToggleDataConnection(True)
            asserts.assert_true(self.dut.droid.telephonyIsDataEnabled(),
                                "Failed to enable cell data for dut.")

    def get_wlan0_link(self, dut):
        get_wlan0 = 'wpa_cli -iwlan0 -g@android:wpa_wlan0 IFNAME=wlan0 status'
        out = dut.adb.shell(get_wlan0)
        out = dict(re.findall(r'(\S+)=(".*?"|\S+)', out))
        asserts.assert_true("ssid" in out,
                            "Client doesn't connect to any network")
        return out

    def generate_random_list(self, lst):
        """Generate a list where
        the previous and subsequent items
        do not repeat"""

        channel_list = []
        num = random.choice(lst)
        channel_list.append(num)
        for i in range(1, self.stress_count):
            num = random.choice(lst)
            while num == channel_list[-1]:
                num = random.choice(lst)
            channel_list.append(num)
        return channel_list

    @test_tracker_info(uuid="3411cb7c-2609-433a-97b6-202a096dc71b")
    def test_softap_channel_switch_stress_5g(self):
        """
        1. Disable DUT's Wi-Fi
        2. Enable CLIENT's Wi-Fi
        3. Check DUT's sim is ready or not
        4. Enable DUT's mobile data
        5. Bring up DUT's softap in 5g
        6. CLIENT connect to DUT
        7. DUT switch to different 5g channel
        8. Verify CLIENT follow the change
        9, Repeat step 7 and 8
        """

        config = wutils.create_softap_config()
        wutils.wifi_toggle_state(self.dut_client, True)
        init_wifi_state = self.dut.droid.wifiCheckState()
        init_sim_state = tel_utils.is_sim_ready(self.log, self.dut)
        self.dut.log.info("initial wifi state = {}".format(init_wifi_state))
        self.dut.log.info("initial sim state = {}".format(init_sim_state))
        if init_sim_state:
            self.check_cell_data_and_enable()
        wutils.start_wifi_tethering(self.dut,
                                    config[wutils.WifiEnums.SSID_KEY],
                                    config[wutils.WifiEnums.PWD_KEY],
                                    WifiEnums.WIFI_CONFIG_APBAND_5G)
        wutils.connect_to_wifi_network(self.dut_client, config)
        channel_list = self.generate_random_list(
            WifiEnums.NONE_DFS_5G_FREQUENCIES)
        self.log.info("channel_list = {}".format(channel_list))
        for count in range(len(channel_list)):
            self.log.info("iteration : {}".format(count))
            self.dut.log.info('hotspot 5g channel switch START')
            channel_5g = channel_list[count]
            hotspot_5g_channel_switch_cmd = (
                'hostapd_cli -i {} chan_switch 10 {}'.format(self.AP_IFACE,
                                                             channel_5g))
            self.dut.adb.shell(hotspot_5g_channel_switch_cmd)
            self.dut.log.info('softap frequency : {}'.format(channel_5g))
            time.sleep(30)
            client_frequency = int(self.get_wlan0_link(self.dut_client)["freq"])
            self.dut_client.log.info(
                "client frequency : {}".format(client_frequency))
            asserts.assert_true(
                channel_5g == client_frequency,
                "hotspot frequency != client frequency")
