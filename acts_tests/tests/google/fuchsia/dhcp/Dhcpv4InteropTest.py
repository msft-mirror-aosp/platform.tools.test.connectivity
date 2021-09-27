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
from acts import utils
from acts.controllers.access_point import setup_ap, AccessPoint
from acts.controllers.ap_lib import dhcp_config
from acts.controllers.ap_lib import hostapd_constants
from acts.controllers.ap_lib.hostapd_security import Security
from acts.controllers.ap_lib.hostapd_utils import generate_random_password
from acts_contrib.test_utils.abstract_devices.wlan_device import create_wlan_device
from acts_contrib.test_utils.abstract_devices.wlan_device_lib.AbstractDeviceWlanDeviceBaseTest import AbstractDeviceWlanDeviceBaseTest
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest


class Dhcpv4InteropTest(AbstractDeviceWlanDeviceBaseTest):
    """Tests for validating DHCPv4 Interop

    Test Bed Requirement:
    * One Android device or Fuchsia device
    * One Access Point
    """
    access_point: AccessPoint

    def __init__(self, controllers):
        WifiBaseTest.__init__(self, controllers)

    def setup_class(self):
        super().setup_class()
        if 'dut' in self.user_params:
            if self.user_params['dut'] == 'fuchsia_devices':
                self.dut = create_wlan_device(self.fuchsia_devices[0])
            elif self.user_params['dut'] == 'android_devices':
                self.dut = create_wlan_device(self.android_devices[0])
            else:
                raise ValueError('Invalid DUT specified in config. (%s)' %
                                 self.user_params['dut'])
        else:
            # Default is an android device, just like the other tests
            self.dut = create_wlan_device(self.android_devices[0])

        self.access_point = self.access_points[0]
        self.access_point.stop_all_aps()

    def setup_test(self):
        if hasattr(self, "android_devices"):
            for ad in self.android_devices:
                ad.droid.wakeLockAcquireBright()
                ad.droid.wakeUpNow()
        self.dut.wifi_toggle_state(True)

    def teardown_test(self):
        if hasattr(self, "android_devices"):
            for ad in self.android_devices:
                ad.droid.wakeLockRelease()
                ad.droid.goToSleepNow()
        self.dut.turn_location_off_and_scan_toggle_off()
        self.dut.disconnect()
        self.dut.reset_wifi()
        self.access_point.stop_all_aps()

    def connect(self, ap_params):
        asserts.assert_true(
            self.dut.associate(ap_params['ssid'],
                               target_pwd=ap_params['password'],
                               target_security=ap_params['target_security']),
            'Failed to connect.')

    def setup_ap(self):
        """Generates a hostapd config and sets up the AP with that config.
        Does not run a DHCP server.

        Returns: A dictionary of information about the AP.
        """
        ssid = utils.rand_ascii_str(20)
        security_mode = hostapd_constants.WPA2_STRING
        security_profile = Security(
            security_mode=security_mode,
            password=generate_random_password(length=20),
            wpa_cipher='CCMP',
            wpa2_cipher='CCMP')
        password = security_profile.password
        target_security = hostapd_constants.SECURITY_STRING_TO_DEFAULT_TARGET_SECURITY.get(
            security_mode)

        setup_ap(access_point=self.access_point,
                 profile_name='whirlwind',
                 mode=hostapd_constants.MODE_11N_MIXED,
                 channel=hostapd_constants.AP_DEFAULT_CHANNEL_5G,
                 n_capabilities=[],
                 ac_capabilities=[],
                 force_wmm=True,
                 ssid=ssid,
                 security=security_profile,
                 password=password)

        configured_subnets = self.access_point.get_configured_subnets()
        if len(configured_subnets) > 1:
            raise Exception("Expected only one subnet on AP")
        router_ip = configured_subnets[0].router
        network = configured_subnets[0].network

        self.access_point.stop_dhcp()

        return {
            'ssid': ssid,
            'password': password,
            'target_security': target_security,
            'ip': router_ip,
            'network': network,
        }

    def device_can_ping(self, dest_ip):
        self.log.info('Attempting to ping %s...' % dest_ip)
        ping_result = self.dut.can_ping(dest_ip, count=10, size=50)
        if ping_result:
            self.log.info('Success pinging: %s' % dest_ip)
        else:
            self.log.info('Failure pinging: %s' % dest_ip)
        return ping_result

    def get_device_ipv4_addr(self, interface=None, timeout=20):
        """Checks if device has an ipv4 private address. Sleeps 1 second between
        retries.

        Args:
            interface: string, name of interface from which to get ipv4 address.

        Raises:
            ConnectionError, if DUT does not have an ipv4 address after all
            timeout.

        Returns:
            The device's IP address

        """
        self.log.debug('Fetching updated WLAN interface list')
        if interface is None:
            interface = self.dut.device.wlan_client_test_interface_name
        self.log.info(
            'Checking if DUT has received an ipv4 addr on iface %s. Will retry for %s '
            'seconds.' % (interface, timeout))
        timeout = time.time() + timeout
        while time.time() < timeout:
            ip_addrs = self.dut.get_interface_ip_addresses(interface)

            if len(ip_addrs['ipv4_private']) > 0:
                ip = ip_addrs['ipv4_private'][0]
                self.log.info('DUT has an ipv4 address: %s' % ip)
                return ip
            else:
                self.log.debug(
                    'DUT does not yet have an ipv4 address...retrying in 1 '
                    'second.')
                time.sleep(1)
        else:
            raise ConnectionError('DUT failed to get an ipv4 address.')

    def test_basic_dhcp_assignment(self):
        ap_params = self.setup_ap()
        subnet_conf = dhcp_config.Subnet(subnet=ap_params['network'],
                                         router=ap_params['ip'])
        dhcp_conf = dhcp_config.DhcpConfig(subnets=[subnet_conf])
        self.access_point.start_dhcp(dhcp_conf=dhcp_conf)
        self.connect(ap_params=ap_params)
        self.get_device_ipv4_addr()

    def test_no_dhcp_server_started(self):
        """Validates that self.setup_ap() does not start a DHCP server."""
        ap_params = self.setup_ap()
        self.connect(ap_params=ap_params)
        with asserts.assert_raises(ConnectionError):
            self.get_device_ipv4_addr()
