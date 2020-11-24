#!/usr/bin/env python3
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

import inspect
import logging

import acts_contrib.test_utils.wifi.wifi_test_utils as awutils
import acts_contrib.test_utils.abstract_devices.utils_lib.wlan_utils as fwutils
from acts.utils import get_interface_ip_addresses
from acts.utils import adb_shell_ping

from acts import asserts
from acts.controllers.fuchsia_device import FuchsiaDevice
from acts.controllers.android_device import AndroidDevice


def create_wlan_device(hardware_device):
    """Creates a generic WLAN device based on type of device that is sent to
    the functions.

    Args:
        hardware_device: A WLAN hardware device that is supported by ACTS.
    """
    if isinstance(hardware_device, FuchsiaDevice):
        return FuchsiaWlanDevice(hardware_device)
    elif isinstance(hardware_device, AndroidDevice):
        return AndroidWlanDevice(hardware_device)
    else:
        raise ValueError('Unable to create WlanDevice for type %s' %
                         type(hardware_device))


FUCHSIA_VALID_SECURITY_TYPES = {"none", "wep", "wpa", "wpa2", "wpa3"}


class WlanDevice(object):
    """Class representing a generic WLAN device.

    Each object of this class represents a generic WLAN device.
    Android device and Fuchsia devices are the currently supported devices/

    Attributes:
        device: A generic WLAN device.
    """
    def __init__(self, device):
        self.device = device
        self.log = logging
        self.identifier = None

    def wifi_toggle_state(self, state):
        """Base generic WLAN interface.  Only called if not overridden by
        another supported device.
        """
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def reset_wifi(self):
        """Base generic WLAN interface.  Only called if not overridden by
        another supported device.
        """
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def take_bug_report(self, test_name, begin_time):
        """Base generic WLAN interface.  Only called if not overridden by
        another supported device.
        """
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def get_log(self, test_name, begin_time):
        """Base generic WLAN interface.  Only called if not overridden by
        another supported device.
        """
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def turn_location_off_and_scan_toggle_off(self):
        """Base generic WLAN interface.  Only called if not overridden by
        another supported device.
        """
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def associate(self,
                  target_ssid,
                  target_pwd=None,
                  check_connectivity=True,
                  hidden=False,
                  association_mechanism=None,
                  target_security=None):
        """Base generic WLAN interface.  Only called if not overriden by
        another supported device.
        """
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def disconnect(self, association_mechanism=None):
        """Base generic WLAN interface.  Only called if not overridden by
        another supported device.
        """
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def get_wlan_interface_id_list(self):
        """Base generic WLAN interface.  Only called if not overridden by
        another supported device.
        """
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def destroy_wlan_interface(self, iface_id):
        """Base generic WLAN interface.  Only called if not overridden by
        another supported device.
        """
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def send_command(self, command):
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def get_interface_ip_addresses(self, interface):
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def is_connected(self, ssid=None):
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def can_ping(self,
                 dest_ip,
                 count=3,
                 interval=1000,
                 timeout=1000,
                 size=25,
                 additional_ping_params=None):
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def ping(self,
             dest_ip,
             count=3,
             interval=1000,
             timeout=1000,
             size=25,
             additional_ping_params=None):
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def hard_power_cycle(self, pdus=None):
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def save_network(self, ssid):
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))

    def clear_saved_networks(self):
        raise NotImplementedError("{} must be defined.".format(
            inspect.currentframe().f_code.co_name))


class AndroidWlanDevice(WlanDevice):
    """Class wrapper for an Android WLAN device.

    Each object of this class represents a generic WLAN device.
    Android device and Fuchsia devices are the currently supported devices/

    Attributes:
        android_device: An Android WLAN device.
    """
    def __init__(self, android_device):
        super().__init__(android_device)
        self.identifier = android_device.serial

    def wifi_toggle_state(self, state):
        awutils.wifi_toggle_state(self.device, state)

    def reset_wifi(self):
        awutils.reset_wifi(self.device)

    def take_bug_report(self, test_name, begin_time):
        self.device.take_bug_report(test_name, begin_time)

    def get_log(self, test_name, begin_time):
        self.device.cat_adb_log(test_name, begin_time)

    def turn_location_off_and_scan_toggle_off(self):
        awutils.turn_location_off_and_scan_toggle_off(self.device)

    def associate(self,
                  target_ssid,
                  target_pwd=None,
                  key_mgmt=None,
                  check_connectivity=True,
                  hidden=False,
                  association_mechanism=None,
                  target_security=None):
        """Function to associate an Android WLAN device.

        Args:
            target_ssid: SSID to associate to.
            target_pwd: Password for the SSID, if necessary.
            key_mgmt: The hostapd wpa_key_mgmt value, distinguishes wpa3 from
                wpa2 for android tests.
            check_connectivity: Whether to check for internet connectivity.
            hidden: Whether the network is hidden.
        Returns:
            True if successfully connected to WLAN, False if not.
        """
        network = {'SSID': target_ssid, 'hiddenSSID': hidden}
        if target_pwd:
            network['password'] = target_pwd
        if key_mgmt:
            network['security'] = key_mgmt
        try:
            awutils.connect_to_wifi_network(
                self.device,
                network,
                check_connectivity=check_connectivity,
                hidden=hidden)
            return True
        except Exception as e:
            self.device.log.info('Failed to associated (%s)' % e)
            return False

    def disconnect(self, association_mechanism=None):
        awutils.turn_location_off_and_scan_toggle_off(self.device)

    def get_wlan_interface_id_list(self):
        pass

    def destroy_wlan_interface(self, iface_id):
        pass

    def send_command(self, command):
        return self.device.adb.shell(str(command))

    def get_interface_ip_addresses(self, interface):
        return get_interface_ip_addresses(self.device, interface)

    def is_connected(self, ssid=None):
        wifi_info = self.device.droid.wifiGetConnectionInfo()
        if ssid:
            return 'BSSID' in wifi_info and wifi_info['SSID'] == ssid
        return 'BSSID' in wifi_info

    def can_ping(self,
                 dest_ip,
                 count=3,
                 interval=1000,
                 timeout=1000,
                 size=25,
                 additional_ping_params=None):
        return adb_shell_ping(self.device,
                              dest_ip=dest_ip,
                              count=count,
                              timeout=timeout)

    def ping(self, dest_ip, count=3, interval=1000, timeout=1000, size=25):
        pass

    def hard_power_cycle(self, pdus):
        pass

    def save_network(self, ssid):
        pass

    def clear_saved_networks(self):
        pass


class FuchsiaWlanDevice(WlanDevice):
    """Class wrapper for an Fuchsia WLAN device.

    Each object of this class represents a generic WLAN device.
    Android device and Fuchsia devices are the currently supported devices/

    Attributes:
        fuchsia_device: A Fuchsia WLAN device.
    """
    def __init__(self, fuchsia_device):
        super().__init__(fuchsia_device)
        self.identifier = fuchsia_device.ip

    def wifi_toggle_state(self, state):
        """Stub for Fuchsia implementation."""
        pass

    def reset_wifi(self):
        """Stub for Fuchsia implementation."""
        pass

    def take_bug_report(self, test_name, begin_time):
        """Stub for Fuchsia implementation."""
        pass

    def get_log(self, test_name, begin_time):
        """Stub for Fuchsia implementation."""
        pass

    def turn_location_off_and_scan_toggle_off(self):
        """Stub for Fuchsia implementation."""
        pass

    def associate(self,
                  target_ssid,
                  target_pwd=None,
                  key_mgmt=None,
                  check_connectivity=True,
                  hidden=False,
                  association_mechanism=None,
                  target_security=None):
        """Function to associate a Fuchsia WLAN device.

        Args:
            target_ssid: SSID to associate to.
            target_pwd: Password for the SSID, if necessary.
            key_mgmt: the hostapd wpa_key_mgmt, if specified.
            check_connectivity: Whether to check for internet connectivity.
            hidden: Whether the network is hidden.
        Returns:
            True if successfully connected to WLAN, False if not.
        """
        if association_mechanism == 'policy':
            return self.device.policy_save_and_connect(target_ssid,
                                                       target_security,
                                                       password=target_pwd)
        elif not association_mechanism or association_mechanism == 'drivers':
            connection_response = self.device.wlan_lib.wlanConnectToNetwork(
                target_ssid, target_pwd=target_pwd)
            return self.device.check_connect_response(connection_response)
        else:
            self.log.error(
                "Association mechanism %s is not recognized. Acceptable values are 'drivers' and 'policy'"
                % association_mechanism)
            return False

    def disconnect(self, association_mechanism=None):
        """Function to disconnect from a Fuchsia WLAN device.
           Asserts if disconnect was not successful.
        """
        if association_mechanism == 'policy':
            asserts.assert_true(self.device.remove_all_and_disconnect(),
                                'Failed to disconnect')
        elif not association_mechanism or association_mechanism == 'drivers':
            disconnect_response = self.device.wlan_lib.wlanDisconnect()
            asserts.assert_true(
                self.device.check_disconnect_response(disconnect_response),
                'Failed to disconnect.')
        else:
            self.log.error(
                "Association mechanism %s is not recognized. Acceptable values are 'drivers' and 'policy'"
                % association_mechanism)
            raise ValueError(
                'Invalid association_mechanism "%s". Valid options are "policy" or "drivers".'
                % association_mechanism)

    def status(self):
        return self.device.wlan_lib.wlanStatus()

    def can_ping(self,
                 dest_ip,
                 count=3,
                 interval=1000,
                 timeout=1000,
                 size=25,
                 additional_ping_params=None):
        return self.device.can_ping(
            dest_ip,
            count=count,
            interval=interval,
            timeout=timeout,
            size=size,
            additional_ping_params=additional_ping_params)

    def ping(self,
             dest_ip,
             count=3,
             interval=1000,
             timeout=1000,
             size=25,
             additional_ping_params=None):
        return self.device.ping(dest_ip,
                                count=count,
                                interval=interval,
                                timeout=timeout,
                                size=size,
                                additional_ping_params=additional_ping_params)

    def get_wlan_interface_id_list(self):
        """Function to list available WLAN interfaces.

        Returns:
            A list of wlan interface IDs.
        """
        return self.device.wlan_lib.wlanGetIfaceIdList().get('result')

    def destroy_wlan_interface(self, iface_id):
        """Function to associate a Fuchsia WLAN device.

        Args:
            target_ssid: SSID to associate to.
            target_pwd: Password for the SSID, if necessary.
            check_connectivity: Whether to check for internet connectivity.
            hidden: Whether the network is hidden.
        Returns:
            True if successfully destroyed wlan interface, False if not.
        """
        result = self.device.wlan_lib.wlanDestroyIface(iface_id)
        if result.get('error') is None:
            return True
        else:
            self.log.error("Failed to destroy interface with: {}".format(
                result.get('error')))
            return False

    def send_command(self, command):
        return self.device.send_command_ssh(str(command)).stdout

    def get_interface_ip_addresses(self, interface):
        return get_interface_ip_addresses(self.device, interface)

    def is_connected(self, ssid=None):
        """ Determines if wlan_device is connected to wlan network.

        Args:
            ssid (optional): string, to check if device is connect to a specific
                network.

        Returns:
            True, if connected to a network or to the correct network when SSID
                is provided.
            False, if not connected or connect to incorrect network when SSID is
                provided.
        """
        response = self.status()
        if response.get('error'):
            raise ConnectionError(
                'Failed to get client network connection status')

        status = response.get('result')
        if status and status.get('connected_to'):
            if ssid:
                connected_ssid = ''.join(
                    chr(i) for i in status['connected_to']['ssid'])
                if ssid != connected_ssid:
                    return False
            return True
        return False

    def hard_power_cycle(self, pdus):
        self.device.reboot(reboot_type='hard', testbed_pdus=pdus)

    def save_network(self, target_ssid, security_type=None, target_pwd=None):
        if security_type and security_type not in FUCHSIA_VALID_SECURITY_TYPES:
            raise TypeError('Invalid security type: %s' % security_type)
        response = self.device.wlan_policy_lib.wlanSaveNetwork(
            target_ssid, security_type, target_pwd=target_pwd)
        if response.get('error'):
            raise EnvironmentError('Failed to save network %s. Err: %s' %
                                   (target_ssid, response.get('error')))

    def clear_saved_networks(self):
        response = self.device.wlan_policy_lib.wlanRemoveAllNetworks()
        if response.get('error'):
            raise EnvironmentError('Failed to clear saved networks: %s' %
                                   response.get('error'))
