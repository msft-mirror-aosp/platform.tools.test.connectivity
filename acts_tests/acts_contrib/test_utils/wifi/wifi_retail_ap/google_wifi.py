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

from acts.controllers import access_point
from acts.controllers.ap_lib import bridge_interface
from acts.controllers.ap_lib import hostapd_security
from acts.controllers.ap_lib import hostapd_ap_preset
from acts_contrib.test_utils.wifi.wifi_retail_ap import WifiRetailAP


class GoogleWifiAP(WifiRetailAP):
    """ Class that implements Google Wifi AP.

    This class is a work in progress
    """
    def __init__(self, ap_settings):
        super().__init__(ap_settings)
        # Initialize AP
        if self.ap_settings["status_2G"] and self.ap_settings["status_5G_1"]:
            raise ValueError("Error initializing Google Wifi AP. "
                             "Only one interface can be enabled at a time.")
        self.channel_band_map = {
            "2G": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
            "5G_1": [36, 40, 44, 48, 149, 153, 157, 161, 165]
        }
        self.BW_MODE_MAP = {
            "legacy": 20,
            "VHT20": 20,
            "VHT40": 40,
            "VHT80": 80
        }
        self.default_settings = {
            "region": "United States",
            "brand": "Google",
            "model": "Wifi",
            "hostapd_profile": "whirlwind",
            "status_2G": 0,
            "status_5G_1": 0,
            "ssid_2G": "GoogleWifi_2G",
            "ssid_5G_1": "GoogleWifi_5G",
            "channel_2G": 11,
            "channel_5G_1": 149,
            "bandwidth_2G": "VHT20",
            "bandwidth_5G_1": "VHT20",
            "power_2G": "auto",
            "power_5G_1": "auto",
            "mode_2G": None,
            "num_streams_2G": None,
            "rate_2G": "auto",
            "short_gi_2G": 0,
            "mode_5G_1": None,
            "num_streams_5G_1": None,
            "rate_5G_1": "auto",
            "short_gi_5G_1": 0,
            "security_type_2G": "Open",
            "security_type_5G_1": "Open",
            "subnet_2G": "192.168.1.0/24",
            "subnet_5G_1": "192.168.9.0/24",
            "password_2G": "password",
            "password_5G_1": "password"
        }
        self.default_mode = 'VHT'
        for setting in self.default_settings.keys():
            if setting not in self.ap_settings:
                self.log.debug(
                    "{0} not found during init. Setting {0} = {1}".format(
                        setting, self.default_settings[setting]))
                self.ap_settings[setting] = self.default_settings[setting]
        init_settings = self.ap_settings.copy()
        init_settings["ap_subnet"] = {
            "2g": self.ap_settings["subnet_2G"],
            "5g": self.ap_settings["subnet_5G_1"]
        }
        self.access_point = access_point.AccessPoint(init_settings)
        self.configure_ap()

    def read_ap_settings(self):
        """Function that reads current ap settings."""
        return self.ap_settings.copy()

    def update_ap_settings(self, dict_settings={}, **named_settings):
        """Function to update settings of existing AP.

        Function copies arguments into ap_settings and calls configure_ap
        to apply them.

        Args:
            dict_settings: single dictionary of settings to update
            **named_settings: named settings to update
            Note: dict and named_settings cannot contain the same settings.
        """
        settings_to_update = dict(dict_settings, **named_settings)
        if len(settings_to_update) != len(dict_settings) + len(named_settings):
            raise KeyError("The following keys were passed twice: {}".format(
                (set(dict_settings.keys()).intersection(
                    set(named_settings.keys())))))
        if not set(settings_to_update.keys()).issubset(
                set(self.ap_settings.keys())):
            raise KeyError(
                "The following settings are invalid for this AP: {}".format(
                    set(settings_to_update.keys()).difference(
                        set(self.ap_settings.keys()))))

        updating_2G = any(["2G" in x for x in settings_to_update.keys()])
        updating_5G_1 = any(["5G_1" in x for x in settings_to_update.keys()])
        if updating_2G and updating_5G_1:
            raise ValueError(
                "Error updating Google WiFi AP. "
                "One interface can be activated and updated at a time")
        elif updating_2G:
            # If updating an interface and not explicitly setting its status,
            # it is assumed that the interface is to be ENABLED and updated
            if "status_2G" not in settings_to_update:
                settings_to_update["status_2G"] = 1
                settings_to_update["status_5G_1"] = 0
        elif updating_5G_1:
            if "status_5G_1" not in settings_to_update:
                settings_to_update["status_2G"] = 0
                settings_to_update["status_5G_1"] = 1

        updates_requested = False
        for setting, value in settings_to_update.items():
            if self.ap_settings[setting] != value:
                self.ap_settings[setting] = value
                updates_requested = True

        if updates_requested:
            self.configure_ap()

    def configure_ap(self):
        """Function to configure Google Wifi."""
        self.log.info("Stopping Google Wifi interfaces.")
        self.access_point.stop_all_aps()

        if self.ap_settings["status_2G"] == 1:
            network = "2G"
            self.log.info("Bringing up 2.4 GHz network.")
        elif self.ap_settings["status_5G_1"] == 1:
            network = "5G_1"
            self.log.info("Bringing up 5 GHz network.")
        else:
            return

        bss_settings = []
        ssid = self.ap_settings["ssid_{}".format(network)]
        security_mode = self.ap_settings["security_type_{}".format(
            network)].lower()
        if "wpa" in security_mode:
            password = self.ap_settings["password_{}".format(network)]
            security = hostapd_security.Security(security_mode=security_mode,
                                                 password=password)
        else:
            security = hostapd_security.Security(security_mode=None,
                                                 password=None)
        channel = int(self.ap_settings["channel_{}".format(network)])
        bandwidth = self.BW_MODE_MAP[self.ap_settings["bandwidth_{}".format(
            network)]]
        config = hostapd_ap_preset.create_ap_preset(
            channel=channel,
            ssid=ssid,
            security=security,
            bss_settings=bss_settings,
            vht_bandwidth=bandwidth,
            profile_name=self.ap_settings["hostapd_profile"],
            iface_wlan_2g=self.access_point.wlan_2g,
            iface_wlan_5g=self.access_point.wlan_5g)
        config_bridge = self.access_point.generate_bridge_configs(channel)
        brconfigs = bridge_interface.BridgeInterfaceConfigs(
            config_bridge[0], "lan0", config_bridge[2])
        self.access_point.bridge.startup(brconfigs)
        self.access_point.start_ap(config)
        self.set_power(network, self.ap_settings["power_{}".format(network)])
        self.set_rate(
            network,
            mode=self.ap_settings["mode_{}".format(network)],
            num_streams=self.ap_settings["num_streams_{}".format(network)],
            rate=self.ap_settings["rate_{}".format(network)],
            short_gi=self.ap_settings["short_gi_{}".format(network)])
        self.log.info("AP started on channel {} with SSID {}".format(
            channel, ssid))

    def set_power(self, network, power):
        """Function that sets network transmit power.

        Args:
            network: string containing network identifier (2G, 5G_1, 5G_2)
            power: power level in dBm
        """
        if power == "auto":
            power_string = "auto"
        else:
            if not float(power).is_integer():
                self.log.info(
                    "Power in dBm must be an integer. Setting to {}".format(
                        int(power)))
            power = int(power)
            power_string = "fixed {}".format(int(power) * 100)

        if "2G" in network:
            interface = self.access_point.wlan_2g
            self.ap_settings["power_2G"] = power
        elif "5G_1" in network:
            interface = self.access_point.wlan_5g
            self.ap_settings["power_5G_1"] = power
        self.access_point.ssh.run("iw dev {} set txpower {}".format(
            interface, power_string))

    def set_rate(self,
                 network,
                 mode=None,
                 num_streams=None,
                 rate='auto',
                 short_gi=0):
        """Function that sets rate.

        Args:
            network: string containing network identifier (2G, 5G_1, 5G_2)
            mode: string indicating the WiFi standard to use
            num_streams: number of MIMO streams. used only for VHT
            rate: data rate of MCS index to use
            short_gi: boolean controlling the use of short guard interval
        """
        if "2G" in network:
            interface = self.access_point.wlan_2g
            interface_short = "2.4"
            self.ap_settings["mode_2G"] = mode
            self.ap_settings["num_streams_2G"] = num_streams
            self.ap_settings["rate_2G"] = rate
            self.ap_settings["short_gi_2G"] = short_gi
        elif "5G_1" in network:
            interface = self.access_point.wlan_5g
            interface_short = "5"
            self.ap_settings["mode_5G_1"] = mode
            self.ap_settings["num_streams_5G_1"] = num_streams
            self.ap_settings["rate_5G_1"] = rate
            self.ap_settings["short_gi_5G_1"] = short_gi

        if rate == "auto":
            cmd_string = "iw dev {0} set bitrates".format(interface)
        elif "legacy" in mode.lower():
            cmd_string = "iw dev {0} set bitrates legacy-{1} {2} ht-mcs-{1} vht-mcs-{1}".format(
                interface, interface_short, rate)
        elif "vht" in mode.lower():
            cmd_string = "iw dev {0} set bitrates legacy-{1} ht-mcs-{1} vht-mcs-{1} {2}:{3}".format(
                interface, interface_short, num_streams, rate)
            if short_gi:
                cmd_string = cmd_string + " sgi-{}".format(interface_short)
        elif "ht" in mode.lower():
            cmd_string = "iw dev {0} set bitrates legacy-{1} ht-mcs-{1} {2} vht-mcs-{1}".format(
                interface, interface_short, rate)
            if short_gi:
                cmd_string = cmd_string + " sgi-{}".format(interface_short)
        self.access_point.ssh.run(cmd_string)
