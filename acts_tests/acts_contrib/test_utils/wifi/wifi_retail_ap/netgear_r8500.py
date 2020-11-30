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

from acts_contrib.test_utils.wifi.wifi_retail_ap import NetgearR7000AP


class NetgearR8500AP(NetgearR7000AP):
    """Class that implements Netgear R8500 AP.

    Since most of the class' implementation is shared with the R7000, this
    class inherits from NetgearR7000AP and simply redefines config parameters
    """
    def __init__(self, ap_settings):
        super().__init__(ap_settings)
        self.init_gui_data()
        # Overwrite minor differences from R8000 AP
        self.config_page = (
            "{protocol}://{username}:{password}@"
            "{ip_address}:{port}/WLG_wireless_tri_band.htm").format(
                protocol=self.ap_settings["protocol"],
                username=self.ap_settings["admin_username"],
                password=self.ap_settings["admin_password"],
                ip_address=self.ap_settings["ip_address"],
                port=self.ap_settings["port"])
        self.config_page_nologin = (
            "{protocol}://{ip_address}:{port}/"
            "WLG_wireless_tri_band.htm").format(
                protocol=self.ap_settings["protocol"],
                ip_address=self.ap_settings["ip_address"],
                port=self.ap_settings["port"])
        self.config_page_advanced = (
            "{protocol}://{username}:{password}@"
            "{ip_address}:{port}/WLG_adv_tri_band2.htm").format(
                protocol=self.ap_settings["protocol"],
                username=self.ap_settings["admin_username"],
                password=self.ap_settings["admin_password"],
                ip_address=self.ap_settings["ip_address"],
                port=self.ap_settings["port"])
        self.networks = ["2G", "5G_1", "5G_2"]
        self.channel_band_map = {
            "2G": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "5G_1": [36, 40, 44, 48],
            "5G_2": [149, 153, 157, 161, 165]
        }
        self.config_page_fields = {
            "region": "WRegion",
            ("2G", "status"): "enable_ap",
            ("5G_1", "status"): "enable_ap_an",
            ("5G_2", "status"): "enable_ap_an_2",
            ("2G", "ssid"): "ssid",
            ("5G_1", "ssid"): "ssid_an",
            ("5G_2", "ssid"): "ssid_an_2",
            ("2G", "channel"): "w_channel",
            ("5G_1", "channel"): "w_channel_an",
            ("5G_2", "channel"): "w_channel_an_2",
            ("2G", "bandwidth"): "opmode",
            ("5G_1", "bandwidth"): "opmode_an",
            ("5G_2", "bandwidth"): "opmode_an_2",
            ("2G", "security_type"): "security_type",
            ("5G_1", "security_type"): "security_type_an",
            ("5G_2", "security_type"): "security_type_an_2",
            ("2G", "password"): "passphrase",
            ("5G_1", "password"): "passphrase_an",
            ("5G_2", "password"): "passphrase_an_2"
        }
        self.bw_mode_text = {
            "11g": "Up to 54 Mbps",
            "VHT20": "Up to 433 Mbps",
            "VHT40": "Up to 1000 Mbps",
            "VHT80": "Up to 2165 Mbps"
        }
        self.default_mode = 'HE'
        # Read and update AP settings
        self.read_ap_settings()
        if not set(ap_settings.items()).issubset(self.ap_settings.items()):
            self.update_ap_settings(ap_settings)
