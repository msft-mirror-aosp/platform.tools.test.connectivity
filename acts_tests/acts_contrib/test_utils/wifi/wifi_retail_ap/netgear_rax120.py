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

import selenium
import time
from acts_contrib.test_utils.wifi.wifi_retail_ap.netgear_r7500 import NetgearR7500AP
from acts_contrib.test_utils.wifi.wifi_retail_ap import BlockingBrowser

BROWSER_WAIT_SHORT = 1
BROWSER_WAIT_MED = 3
BROWSER_WAIT_LONG = 30
BROWSER_WAIT_EXTRA_LONG = 60


class NetgearRAX120AP(NetgearR7500AP):
    """Class that implements Netgear RAX120 AP.

    Since most of the class' implementation is shared with the R7500, this
    class inherits from NetgearR7500AP and simply redefines config parameters
    """
    def __init__(self, ap_settings):
        super().__init__(ap_settings)
        self.init_gui_data()
        # Read and update AP settings
        self.read_ap_settings()
        if not set(ap_settings.items()).issubset(self.ap_settings.items()):
            self.update_ap_settings(ap_settings)

    def init_gui_data(self):
        """Function to initialize data used while interacting with web GUI"""
        self.config_page = ("{protocol}://{username}:{password}@"
                            "{ip_address}:{port}/index.htm").format(
                                protocol=self.ap_settings["protocol"],
                                username=self.ap_settings["admin_username"],
                                password=self.ap_settings["admin_password"],
                                ip_address=self.ap_settings["ip_address"],
                                port=self.ap_settings["port"])
        self.config_page_advanced = (
            "{protocol}://{username}:{password}@"
            "{ip_address}:{port}/adv_index.htm").format(
                protocol=self.ap_settings["protocol"],
                username=self.ap_settings["admin_username"],
                password=self.ap_settings["admin_password"],
                ip_address=self.ap_settings["ip_address"],
                port=self.ap_settings["port"])
        self.networks = ["2G", "5G_1"]
        self.channel_band_map = {
            "2G": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "5G_1": [
                36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120,
                124, 128, 132, 136, 140, 149, 153, 157, 161, 165
            ]
        }
        self.config_page_fields = {
            "region": "WRegion",
            "enable_ax": "enable_ax_chec",
            ("2G", "status"): "enable_ap",
            ("5G_1", "status"): "enable_ap_an",
            ("2G", "ssid"): "ssid",
            ("5G_1", "ssid"): "ssid_an",
            ("2G", "channel"): "w_channel",
            ("5G_1", "channel"): "w_channel_an",
            ("2G", "bandwidth"): "opmode",
            ("5G_1", "bandwidth"): "opmode_an",
            ("2G", "security_type"): "security_type",
            ("5G_1", "security_type"): "security_type_an",
            ("2G", "password"): "passphrase",
            ("5G_1", "password"): "passphrase_an"
        }
        self.region_map = {
            "0": "Africa",
            "1": "Asia",
            "2": "Australia",
            "3": "Canada",
            "4": "Europe",
            "5": "Israel",
            "6": "Japan",
            "7": "Korea",
            "8": "Mexico",
            "9": "South America",
            "10": "United States",
            "11": "China",
            "12": "India",
            "13": "Malaysia",
            "14": "Middle East(Algeria/Syria/Yemen)",
            "15": "Middle East(Iran/Labanon/Qatar)",
            "16": "Middle East(Egypt/Tunisia/Kuwait)",
            "17": "Middle East(Turkey)",
            "18": "Middle East(Saudi Arabia/United Arab Emirates)",
            "19": "Russia",
            "20": "Singapore",
            "21": "Taiwan",
        }
        self.bw_mode_text = {
            '2G': {
                "11g": "Up to 54 Mbps (11g)",
                "HE20": "Up to 573.5 Mbps (11ax, HT20, 1024-QAM)",
                "HE40": "Up to 1147 Mbps (11ax, HT40, 1024-QAM)",
                'VHT20': 'Up to 481 Mbps (11ng, HT20, 1024-QAM)',
                'VHT40': 'Up to 1000 Mbps (11ng, HT40, 1024-QAM)'
            },
            '5G_1': {
                "HE20": "Up to 1147 Mbps (11ax, HT20, 1024-QAM)",
                "HE40": "Up to 2294 Mbps (11ax, HT40, 1024-QAM)",
                "HE80": "Up to 4803 Mbps (11ax, HT80, 1024-QAM)",
                "HE160": "Up to 4803 Mbps (11ax, HT160, 1024-QAM)",
                'VHT20': 'Up to 962 Mbps (11ac, HT20, 1024-QAM)',
                'VHT40': 'Up to 2000 Mbps (11ac, HT40, 1024-QAM)',
                'VHT80': 'Up to 4333 Mbps (11ac, HT80, 1024-QAM)',
                'VHT160': 'Up to 4333 Mbps (11ac, HT160, 1024-QAM)'
            }
        }
        self.bw_mode_values = {
            0: {
                "1": "11g",
                "2": "VHT20",
                "3": "VHT40",
                '7': 'VHT20',
                '8': 'VHT40',
                '9': 'VHT80',
                '10': 'VHT160'
            },
            1: {
                "1": "11g",
                "2": "HE20",
                "3": "HE40",
                '7': 'HE20',
                '8': 'HE40',
                '9': 'HE80',
                '10': 'HE160'
            }
        }
        self.security_mode_values = {
            '2G': {
                'Disable': 'security_disable',
                'WPA2-PSK': 'security_wpa2'
            },
            '5G_1': {
                'Disable': 'security_an_disable',
                'WPA2-PSK': 'security_an_wpa2'
            }
        }
        self.default_mode = 'HE'

    def set_bandwidth(self, network, bandwidth):
        """Function that sets network bandwidth/mode.

        Args:
            network: string containing network identifier (2G, 5G_1, 5G_2)
            bandwidth: string containing mode, e.g. 11g, VHT20, VHT40, VHT80.
        """
        if 'BW' in bandwidth:
            bandwidth = bandwidth.replace('BW', self.default_mode)
        setting_to_update = {"bandwidth_{}".format(network): str(bandwidth)}
        # Check if other interfaces need to be changed too
        requested_mode = ''.join([x for x in bandwidth if x.isalpha()])
        setting_to_update["enable_ax"] = int('HE' in requested_mode)
        for curr_network in self.networks:
            if curr_network == network:
                pass
            else:
                curr_mode = ''.join([
                    x for x in self.ap_settings["bandwidth_{}".format(
                        curr_network)] if x.isalpha()
                ])
                curr_bw = ''.join([
                    x for x in self.ap_settings["bandwidth_{}".format(
                        curr_network)] if x.isdigit()
                ])
                if curr_mode != requested_mode:
                    updated_mode = '{}{}'.format(requested_mode, curr_bw)
                    self.log.warning("All networks must be VHT or HE. "
                                     "Updating {} to {}".format(
                                         curr_network, updated_mode))
                    setting_to_update["bandwidth_{}".format(
                        curr_network)] = updated_mode

        self.update_ap_settings(setting_to_update)

    def read_ap_settings(self):
        """Function to read ap wireless settings."""
        # Get radio status (on/off)
        self.read_radio_on_off()
        # Get radio configuration. Note that if both radios are off, the below
        # code will result in an error
        with BlockingBrowser(self.ap_settings["headless_browser"],
                             900) as browser:
            browser.visit_persistent(self.config_page,
                                     BROWSER_WAIT_MED,
                                     10,
                                     check_for_element="wireless")
            wireless_button = browser.find_by_id("wireless").first
            wireless_button.click()
            time.sleep(BROWSER_WAIT_MED)

            with browser.get_iframe("formframe") as iframe:
                # read if 11ax is enabled first
                config_item = iframe.find_by_name('enable_ax').first
                self.ap_settings['enable_ax'] = int(config_item.checked)
                # read rest of configuration
                for key, value in self.config_page_fields.items():
                    if "bandwidth" in key:
                        config_item = iframe.find_by_name(value).first
                        self.ap_settings["{}_{}".format(
                            key[1], key[0])] = self.bw_mode_values[
                                self.ap_settings['enable_ax']][
                                    config_item.value]
                    elif "region" in key:
                        config_item = iframe.find_by_name(value).first
                        self.ap_settings["region"] = self.region_map[
                            config_item.value]
                    elif "password" in key:
                        try:
                            config_item = iframe.find_by_name(value).first
                            self.ap_settings["{}_{}".format(
                                key[1], key[0])] = config_item.value
                            self.ap_settings["{}_{}".format(
                                "security_type", key[0])] = "WPA2-PSK"
                        except:
                            self.ap_settings["{}_{}".format(
                                key[1], key[0])] = "defaultpassword"
                            self.ap_settings["{}_{}".format(
                                "security_type", key[0])] = "Disable"
                    elif ("channel" in key) or ("ssid" in key):
                        config_item = iframe.find_by_name(value).first
                        self.ap_settings["{}_{}".format(
                            key[1], key[0])] = config_item.value
        return self.ap_settings.copy()

    def configure_ap(self, **config_flags):
        """Function to configure ap wireless settings."""
        # Turn radios on or off
        if config_flags["status_toggled"]:
            self.configure_radio_on_off()
        # Configure radios
        with BlockingBrowser(self.ap_settings["headless_browser"],
                             900) as browser:
            browser.visit_persistent(self.config_page,
                                     BROWSER_WAIT_MED,
                                     10,
                                     check_for_element="wireless")
            wireless_button = browser.find_by_id("wireless").first
            wireless_button.click()
            time.sleep(BROWSER_WAIT_MED)

            with browser.get_iframe("formframe") as iframe:
                # Create action chain
                action = selenium.webdriver.common.action_chains.ActionChains(
                    browser.driver)
                # Configure 11ax on or off
                curr_ax_enabled = int(
                    iframe.find_by_name('enable_ax').first.checked)
                if self.ap_settings['enable_ax'] != curr_ax_enabled:
                    ax_checkbox = browser.driver.find_element_by_id(
                        "enable_ax_chec")
                    action.move_to_element(ax_checkbox).click().perform()
                # Update AP region. Must be done before channel setting
                config_item = iframe.find_by_name(
                    self.config_page_fields["region"]).first
                config_item.select_by_text(self.ap_settings["region"])
                # Update wireless settings for each network
                for key, value in self.config_page_fields.items():
                    if "ssid" in key:
                        config_item = iframe.find_by_name(value).first
                        config_item.fill(self.ap_settings["{}_{}".format(
                            key[1], key[0])])
                    elif "channel" in key:
                        channel_string = "0" * (int(self.ap_settings[
                            "{}_{}".format(key[1], key[0])]) < 10) + str(
                                self.ap_settings["{}_{}".format(
                                    key[1], key[0])]) + "(DFS)" * (48 < int(
                                        self.ap_settings["{}_{}".format(
                                            key[1], key[0])]) < 149)
                        config_item = iframe.find_by_name(value).first
                        try:
                            config_item.select_by_text(channel_string)
                        except AttributeError:
                            self.log.warning(
                                "Cannot select channel. Keeping AP default.")
                    elif "bandwidth" in key:
                        config_item = iframe.find_by_name(value).first
                        try:
                            config_item.select_by_text(
                                str(self.bw_mode_text[key[0]][self.ap_settings[
                                    "{}_{}".format(key[1], key[0])]]))
                        except AttributeError:
                            self.log.warning(
                                "Cannot select bandwidth. Keeping AP default.")
                # Update passwords for WPA2-PSK protected networks
                # (Must be done after security type is selected)
                for key, value in self.config_page_fields.items():
                    if "security_type" in key:
                        security_option = browser.driver.find_element_by_id(
                            self.security_mode_values[key[0]][self.ap_settings[
                                "{}_{}".format(key[1], key[0])]])
                        action = selenium.webdriver.common.action_chains.ActionChains(
                            browser.driver)
                        action.move_to_element(
                            security_option).click().perform()
                        if self.ap_settings["{}_{}".format(
                                key[1], key[0])] == "WPA2-PSK":
                            config_item = iframe.find_by_name(
                                self.config_page_fields[(key[0],
                                                         "password")]).first
                            config_item.fill(self.ap_settings["{}_{}".format(
                                "password", key[0])])

                apply_button = iframe.find_by_name("Apply")
                apply_button[0].click()
                time.sleep(BROWSER_WAIT_SHORT)
                try:
                    alert = browser.get_alert()
                    alert.accept()
                except:
                    pass
                time.sleep(BROWSER_WAIT_SHORT)
                try:
                    alert = browser.get_alert()
                    alert.accept()
                except:
                    pass
                time.sleep(BROWSER_WAIT_SHORT)
            time.sleep(BROWSER_WAIT_EXTRA_LONG)
            browser.visit_persistent(self.config_page, BROWSER_WAIT_EXTRA_LONG,
                                     10)
