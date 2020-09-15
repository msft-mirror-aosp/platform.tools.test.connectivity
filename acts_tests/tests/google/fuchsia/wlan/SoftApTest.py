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

from mobly import signals
import multiprocessing as mp
import time

from acts import utils
from acts import asserts
from acts.base_test import BaseTestClass
from acts.controllers import iperf_server
from acts.controllers import iperf_client
from acts.controllers.ap_lib import hostapd_constants
from acts.controllers.ap_lib import hostapd_security
from acts.test_utils.abstract_devices.utils_lib import wlan_utils
from acts.test_utils.abstract_devices.wlan_device import create_wlan_device
from acts.test_utils.abstract_devices.utils_lib.wlan_utils import setup_ap_and_associate

ANDROID_DEFAULT_WLAN_INTERFACE = 'wlan0'
CONNECTIVITY_MODE_LOCAL = 'local_only'
CONNECTIVITY_MODE_UNRESTRICTED = 'unrestricted'
DEFAULT_AP_PROFILE = 'whirlwind'
DEFAULT_IPERF_PORT = 5201
DEFAULT_STRESS_TEST_ITERATIONS = 10
DEFAULT_TIMEOUT = 30
DEFAULT_IPERF_TIMEOUT = 60
INTERFACE_ROLE_AP = 'Ap'
INTERFACE_ROLE_CLIENT = 'Client'
INTERFACE_ROLES = {INTERFACE_ROLE_AP, INTERFACE_ROLE_CLIENT}
OPERATING_BAND_2G = 'only_2_4_ghz'
OPERATING_BAND_5G = 'only_5_ghz'
OPERATING_BAND_ANY = 'any'
SECURITY_OPEN = 'none'
SECURITY_WEP = 'wep'
SECURITY_WPA = 'wpa'
SECURITY_WPA2 = 'wpa2'
SECURITY_WPA3 = 'wpa3'
TEST_TYPE_ASSOCIATE_ONLY = 'associate_only'
TEST_TYPE_ASSOCIATE_AND_PING = 'associate_and_ping'
TEST_TYPE_ASSOCIATE_AND_PASS_TRAFFIC = 'associate_and_pass_traffic'
TEST_TYPES = {
    TEST_TYPE_ASSOCIATE_ONLY, TEST_TYPE_ASSOCIATE_AND_PING,
    TEST_TYPE_ASSOCIATE_AND_PASS_TRAFFIC
}


def get_test_name_from_settings(settings):
    return settings['test_name']


def get_soft_ap_params_from_config_or_default(config):
    """Retrieves SoftAp parameters from ACTS config or returns default settings.

    Args:
        config: dict, from ACTS config, that may contain custom soft ap
            parameters

    Returns:
        dict, containing all soft AP parameters
    """
    ssid = config.get(
        'ssid', utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G))
    connectivity_mode = config.get('connectivity_mode',
                                   CONNECTIVITY_MODE_LOCAL)
    operating_band = config.get('operating_band', OPERATING_BAND_2G)
    security_type = config.get('security_type', SECURITY_OPEN)
    password = config.get('password', '')

    return {
        'ssid': ssid,
        'connectivity_mode': connectivity_mode,
        'operating_band': operating_band,
        'security_type': security_type,
        'password': password
    }


class SoftApClient(object):
    def __init__(self, device):
        self.w_device = create_wlan_device(device)
        self.ip_client = iperf_client.IPerfClientOverAdb(device.serial)


class WlanInterface(object):
    def __init__(self):
        self.name = None
        self.mac_addr = None
        self.ipv4 = None


class SoftApTest(BaseTestClass):
    """Tests for Fuchsia SoftAP

    Testbed requirement:
    * One Fuchsia Device
    * One Client (Android) Device
    """
    def setup_class(self):
        self.soft_ap_test_params = self.user_params.get(
            'soft_ap_test_params', {})
        self.dut = create_wlan_device(self.fuchsia_devices[0])
        self.dut.device.netstack_lib.init()

        # TODO(fxb/51313): Add in device agnosticity for clients
        self.clients = []
        for device in self.android_devices:
            self.clients.append(SoftApClient(device))
        self.primary_client = self.clients[0]

        self.iperf_server_config = {
            'user': self.dut.device.ssh_username,
            'host': self.dut.device.ip,
            'ssh_config': self.dut.device.ssh_config
        }
        self.iperf_server = iperf_server.IPerfServerOverSsh(
            self.iperf_server_config, DEFAULT_IPERF_PORT, use_killall=True)
        self.iperf_server.start()

        try:
            self.access_point = self.access_points[0]
        except AttributeError:
            self.access_point = None

        self.ap_iperf_client = iperf_client.IPerfClientOverSsh(
            self.user_params['AccessPoint'][0]['ssh_config'])

    def teardown_class(self):
        # Because this is using killall, it will stop all iperf processes
        self.iperf_server.stop()

    def setup_test(self):
        for ad in self.android_devices:
            ad.droid.wakeLockAcquireBright()
            ad.droid.wakeUpNow()
        for client in self.clients:
            client.w_device.disconnect()
            client.w_device.reset_wifi()
            client.w_device.wifi_toggle_state(True)
        self.stop_all_soft_aps()
        if self.access_point:
            self.access_point.stop_all_aps()
        self.dut.disconnect()

    def teardown_test(self):
        for client in self.clients:
            client.w_device.disconnect()
        for ad in self.android_devices:
            ad.droid.wakeLockRelease()
            ad.droid.goToSleepNow()
        self.stop_all_soft_aps()
        if self.access_point:
            self.access_point.stop_all_aps()
        self.dut.disconnect()

    def on_fail(self, test_name, begin_time):
        self.dut.take_bug_report(test_name, begin_time)
        self.dut.get_log(test_name, begin_time)

    def start_soft_ap(self, settings):
        """Starts a softAP on Fuchsia device.

        Args:
            settings: a dict containing softAP configuration params
                ssid: string, SSID of softAP network
                security_type: string, security type of softAP network
                    - 'none', 'wep', 'wpa', 'wpa2', 'wpa3'
                password: string, password if applicable
                connectivity_mode: string, connecitivity_mode for softAP
                    - 'local_only', 'unrestricted'
                operating_band: string, band for softAP network
                    - 'any', 'only_5_ghz', 'only_2_4_ghz'
        """
        ssid = settings['ssid']
        security_type = settings['security_type']
        password = settings.get('password', '')
        connectivity_mode = settings['connectivity_mode']
        operating_band = settings['operating_band']

        self.log.info('Starting SoftAP on DUT with settings: %s' % settings)

        response = self.dut.device.wlan_ap_policy_lib.wlanStartAccessPoint(
            ssid, security_type, password, connectivity_mode, operating_band)
        if response.get('error'):
            raise EnvironmentError('SL4F: Failed to setup SoftAP. Err: %s' %
                                   response['error'])

        self.log.info('SoftAp network (%s) is up.' % ssid)

    def stop_soft_ap(self, settings):
        """ Stops a specific SoftAP On Fuchsia device.

        Args:
            settings: a dict containing softAP config params (see start_soft_ap)
                for details

        Raises:
            EnvironmentError, if StopSoftAP call fails.
        """
        ssid = settings['ssid']
        security_type = settings['security_type']
        password = settings.get('password', '')

        response = self.dut.device.wlan_ap_policy_lib.wlanStopAccessPoint(
            ssid, security_type, password)
        if response.get('error'):
            raise EnvironmentError('SL4F: Failed to stop SoftAP. Err: %s' %
                                   response['error'])

    def stop_all_soft_aps(self):
        """ Stops all SoftAPs on Fuchsia Device.

        Raises:
            EnvironmentError, if StopAllAps call fails.
        """
        response = self.dut.device.wlan_ap_policy_lib.wlanStopAllAccessPoint()
        if response.get('error'):
            raise EnvironmentError(
                'SL4F: Failed to stop all SoftAPs. Err: %s' %
                response['error'])

    def associate_with_soft_ap(self, w_device, settings):
        """Associates client device with softAP on Fuchsia device.

        Args:
            w_device: wlan_device to associate with the softAP
            settings: a dict containing softAP config params (see start_soft_ap)
                for details

        Raises:
            TestFailure, if association fails
        """
        self.log.info(
            'Attempting to associate client %s with SoftAP on FuchsiaDevice '
            '(%s).' % (w_device.device.serial, self.dut.device.ip))

        check_connectivity = settings[
            'connectivity_mode'] == CONNECTIVITY_MODE_UNRESTRICTED
        associated = wlan_utils.associate(
            w_device,
            settings['ssid'],
            password=settings.get('password'),
            check_connectivity=check_connectivity)

        if not associated:
            self.log.error('Failed to connect to SoftAp.')
            return False

        self.log.info('Client successfully associated with SoftAP.')
        return True

    def disconnect_from_soft_ap(self, w_device):
        """Disconnects client device from SoftAP.

        Args:
            w_device: wlan_device to disconnect from SoftAP
        """
        self.log.info('Disconnecting device %s from SoftAP.' %
                      w_device.device.serial)
        w_device.disconnect()

    def get_dut_interface_by_role(self,
                                  role,
                                  wait_for_addr_timeout=DEFAULT_TIMEOUT):
        """Retrieves interface information from the FuchsiaDevice DUT based
        on the role.

        Args:
            role: string, the role of the interface to seek (e.g. Client or Ap)

        Raises:
            ConnectionError, if SL4F calls fail
            AttributeError, if device does not have an interface matching role

        Returns:
            WlanInterface object representing the interface matching role
        """
        if not role in INTERFACE_ROLES:
            raise ValueError('Unsupported interface role %s' % role)

        interface = WlanInterface()

        # Determine WLAN interface with role
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

            if iface_info['result']['role'] == role:
                interface.mac_addr = iface_info['result']['mac_addr']
                break
        else:
            raise LookupError('Failed to find a %s interface.' % role)

        # Retrieve interface info from netstack
        netstack_ifaces = self.dut.device.netstack_lib.netstackListInterfaces()
        if netstack_ifaces.get('error'):
            raise ConnectionError('Failed to get netstack ifaces: %s' %
                                  netstack_ifaces['error'])

        # TODO(fxb/51315): Once subnet information is available in
        # netstackListInterfaces store it to verify the clients ip address.
        for netstack_iface in netstack_ifaces['result']:
            if netstack_iface['mac'] == interface.mac_addr:
                interface.name = netstack_iface['name']
                if len(netstack_iface['ipv4_addresses']) > 0:
                    interface.ipv4 = '.'.join(
                        str(byte)
                        for byte in netstack_iface['ipv4_addresses'][0])
                else:
                    interface.ipv4 = self.wait_for_ipv4_address(
                        self.dut,
                        interface.name,
                        timeout=wait_for_addr_timeout)
        self.log.info('DUT %s interface: %s. Has ipv4 address %s' %
                      (role, interface.name, interface.ipv4))
        return interface

    def wait_for_ipv4_address(self,
                              w_device,
                              interface_name,
                              timeout=DEFAULT_TIMEOUT):
        # TODO(fxb/51315): Once subnet information is available in netstack, add a
        # subnet verification here.
        """ Waits for interface on a wlan_device to get an ipv4 address.

        Args:
            w_device: wlan_device to check interface
            interface_name: name of the interface to check
            timeout: seconds to wait before raising an error

        Raises:
            ValueError, if interface does not have an ipv4 address after timeout
        """

        end_time = time.time() + timeout
        while time.time() < end_time:
            ips = w_device.get_interface_ip_addresses(interface_name)
            if len(ips['ipv4_private']) > 0:
                self.log.info('Device %s interface %s has ipv4 address %s' %
                              (w_device.device.serial, interface_name,
                               ips['ipv4_private'][0]))
                return ips['ipv4_private'][0]
            else:
                time.sleep(1)
        raise ConnectionError(
            'After %s seconds, device %s still does not have an ipv4 address '
            'on interface %s.' %
            (timeout, w_device.device.serial, interface_name))

    def get_ap_ipv4_address(self, channel, timeout=DEFAULT_TIMEOUT):
        """Get APs ipv4 address (actual AP, not soft ap on DUT)

        Args:
            channel: int, channel of the network used to determine
                which interface to use
        """
        lowest_5ghz_channel = 36
        if channel < lowest_5ghz_channel:
            ap_interface = self.access_point.wlan_2g
        else:
            ap_interface = self.access_point.wlan_5g
        end_time = time.time() + timeout
        while time.time() < end_time:
            ap_ipv4_addresses = utils.get_interface_ip_addresses(
                self.access_point.ssh, ap_interface)['ipv4_private']
            if len(ap_ipv4_addresses) > 0:
                return ap_ipv4_addresses[0]
            else:
                self.log.debug(
                    'Access point does not have an ipv4 address on interface '
                    '%s. Retrying in 1 second.' % ap_interface)
        else:
            raise ConnectionError(
                'Access point never had an ipv4 address on interface %s.' %
                ap_interface)

    def device_can_ping_addr(self, w_device, dest_ip, timeout=DEFAULT_TIMEOUT):
        """ Verify wlan_device can ping a destination ip.

        Args:
            w_device: wlan_device to initiate ping
            dest_ip: ip to ping from wlan_device

        Raises:
            TestFailure, if ping fails
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            with utils.SuppressLogOutput():
                ping_result = w_device.can_ping(dest_ip)

            if ping_result:
                self.log.info('Ping successful from device %s to dest ip %s.' %
                              (w_device.identifier, dest_ip))
                return True
            else:
                self.log.debug(
                    'Device %s could not ping dest ip %s. Retrying in 1 second.'
                    % (w_device.identifier, dest_ip))
                time.sleep(1)
        else:
            self.log.info('Failed to ping from device %s to dest ip %s.' %
                          (w_device.identifier, dest_ip))
            return False

    def run_iperf_traffic(self, ip_client, server_address, server_port=5201):
        """Runs traffic between client and ap an verifies throughput.

        Args:
            ip_client: iperf client to use
            server_address: ipv4 address of the iperf server to use
            server_port: port of the iperf server

        Raises:
            TestFailure, if no traffic passes in either direction
        """
        ip_client_identifier = self.get_iperf_client_identifier(ip_client)

        self.log.info(
            'Running traffic from iperf client %s to iperf server %s.' %
            (ip_client_identifier, server_address))
        client_to_ap_path = ip_client.start(
            server_address, '-i 1 -t 10 -J -p %s' % server_port,
            'client_to_soft_ap')

        client_to_ap_result = iperf_server.IPerfResult(client_to_ap_path)
        if (not client_to_ap_result.avg_receive_rate):
            raise ConnectionError(
                'Failed to pass traffic from iperf client %s to iperf server %s.'
                % (ip_client_identifier, server_address))

        self.log.info(
            'Passed traffic from iperf client %s to iperf server %s with avg '
            'rate of %s MB/s.' % (ip_client_identifier, server_address,
                                  client_to_ap_result.avg_receive_rate))

        self.log.info(
            'Running traffic from iperf server %s to iperf client %s.' %
            (server_address, ip_client_identifier))
        ap_to_client_path = ip_client.start(
            server_address, '-i 1 -t 10 -R -J -p %s' % server_port,
            'soft_ap_to_client')

        ap_to_client_result = iperf_server.IPerfResult(ap_to_client_path)
        if (not ap_to_client_result.avg_receive_rate):
            raise ConnectionError(
                'Failed to pass traffic from iperf server %s to iperf client %s.'
                % (server_address, ip_client_identifier))

        self.log.info(
            'Passed traffic from iperf server %s to iperf client %s with avg '
            'rate of %s MB/s.' % (server_address, ip_client_identifier,
                                  ap_to_client_result.avg_receive_rate))

    def run_iperf_traffic_parallel_process(self,
                                           ip_client,
                                           server_address,
                                           error_queue,
                                           server_port=5201):
        """ Executes run_iperf_traffic using a queue to capture errors. Used
        when running iperf in a parallel process.

        Args:
            ip_client: iperf client to use
            server_address: ipv4 address of the iperf server to use
            error_queue: multiprocessing queue to capture errors
            server_port: port of the iperf server
        """
        try:
            self.run_iperf_traffic(ip_client,
                                   server_address,
                                   server_port=server_port)
        except ConnectionError as err:
            error_queue.put('In iperf process from %s to %s: %s' %
                            (self.get_iperf_client_identifier(ip_client),
                             server_address, err))

    def get_iperf_client_identifier(self, ip_client):
        """ Retrieves an indentifer string from iperf client, for logging.

        Args:
            ip_client: iperf client to grab identifier from
        """
        if type(ip_client) == iperf_client.IPerfClientOverAdb:
            return ip_client._android_device_or_serial
        return ip_client._ssh_settings.hostname

    def dut_is_connected_as_client(self,
                                   channel,
                                   check_traffic=False,
                                   wait_for_addr_timeout=DEFAULT_TIMEOUT):
        """Checks if DUT is successfully connected to AP.

        Args:
            channel: int, channel of the AP network (to retrieve interfaces)
            check_traffic: bool, if true, verifies traffic between DUT and AP,
                else just checks ping.
            wait_for_addr_timeout: int, time, in seconds, to wait when getting
                DUT and AP addresses

        Returns:
            True, if connected correctly
            False, otherwise
        """
        try:
            dut_client_interface = self.get_dut_interface_by_role(
                INTERFACE_ROLE_CLIENT,
                wait_for_addr_timeout=wait_for_addr_timeout)
            ap_ipv4 = self.get_ap_ipv4_address(channel,
                                               timeout=wait_for_addr_timeout)
        except ConnectionError as err:
            self.log.error(
                'Failed to retrieve interfaces and addresses. Err: %s' % err)
            return False

        if not self.device_can_ping_addr(self.dut, ap_ipv4):
            self.log.error('Failed to ping from DUT to AP.')
            return False

        if not self.device_can_ping_addr(self.access_point,
                                         dut_client_interface.ipv4):
            self.log.error('Failed to ping from AP to DUT.')
            return False

        if check_traffic:
            try:
                self.run_iperf_traffic(self.ap_iperf_client,
                                       dut_client_interface.ipv4)
            except ConnectionError as err:
                self.log.error('Failed to run traffic between DUT and AP.')
                return False
        return True

    def client_is_connected_to_soft_ap(
            self,
            client,
            client_interface=ANDROID_DEFAULT_WLAN_INTERFACE,
            check_traffic=False,
            wait_for_addr_timeout=DEFAULT_TIMEOUT):
        """Checks if client is successfully connected to DUT SoftAP.

        Args:
            client: SoftApClient to check
            client_interface: string, wlan interface name of client
            check_traffic: bool, if true, verifies traffic between client and
                DUT, else just checks ping.
            wait_for_addr_timeout: int, time, in seconds, to wait when getting
                DUT and client addresses

        Returns:
            True, if connected correctly
            False, otherwise
        """

        try:
            dut_ap_interface = self.get_dut_interface_by_role(
                INTERFACE_ROLE_AP, wait_for_addr_timeout=wait_for_addr_timeout)
            client_ipv4 = self.wait_for_ipv4_address(
                client.w_device,
                client_interface,
                timeout=wait_for_addr_timeout)
        except ConnectionError as err:
            self.log.error(
                'Failed to retrieve interfaces and addresses. Err: %s' % err)
            return False

        if not self.device_can_ping_addr(self.dut, client_ipv4):
            self.log.error('Failed to ping client (%s) from DUT.' %
                           client_ipv4)
            return False
        if not self.device_can_ping_addr(client.w_device,
                                         dut_ap_interface.ipv4):
            self.log.error('Failed to ping DUT from client (%s)' % client_ipv4)
            return False

        if check_traffic:
            try:
                self.run_iperf_traffic(client.ip_client, dut_ap_interface.ipv4)
            except ConnectionError as err:
                self.log.error(
                    'Ffailed to pass traffic between client (%s) and DUT.' %
                    client_ipv4)
                return False
        return True

# Test Types

    def verify_soft_ap_associate_only(self, client, settings):
        if not self.associate_with_soft_ap(client.w_device, settings):
            asserts.fail('Failed to associate client with SoftAP.')

    def verify_soft_ap_associate_and_ping(self, client, settings):
        self.verify_soft_ap_associate_only(client, settings)
        if not self.client_is_connected_to_soft_ap(client):
            asserts.fail('Client and SoftAP could not ping eachother.')

    def verify_soft_ap_associate_and_pass_traffic(self, client, settings):
        self.verify_soft_ap_associate_only(client, settings)
        if not self.client_is_connected_to_soft_ap(client, check_traffic=True):
            asserts.fail(
                'Client and SoftAP not responding to pings and passing traffic '
                'as expected.')

# Runners for Generated Test Cases

    def run_soft_ap_association_stress_test(self, settings):
        """Sets up a SoftAP, and repeatedly associates and disassociates a
        client.

        Args:
            settings: test configuration settings, see
                test_soft_ap_association_stress for details
        """
        client = settings['client']
        soft_ap_params = settings['soft_ap_params']
        test_type = settings['test_type']
        if not test_type in TEST_TYPES:
            raise ValueError('Unrecognized test type %s' % test_type)
        iterations = settings['iterations']
        self.log.info(
            'Running association stress test type %s in iteration %s times' %
            (test_type, iterations))

        self.start_soft_ap(soft_ap_params)

        passed_count = 0
        for run in range(iterations):
            try:
                self.log.info('Starting SoftAp association run %s' %
                              str(run + 1))

                if test_type == TEST_TYPE_ASSOCIATE_ONLY:
                    self.verify_soft_ap_associate_only(client, soft_ap_params)

                elif test_type == TEST_TYPE_ASSOCIATE_AND_PING:
                    self.verify_soft_ap_associate_and_ping(
                        client, soft_ap_params)

                elif test_type == TEST_TYPE_ASSOCIATE_AND_PASS_TRAFFIC:
                    self.verify_soft_ap_associate_and_pass_traffic(
                        client, soft_ap_params)

                else:
                    raise AttributeError('Invalid test type: %s' % test_type)

            except signals.TestFailure as err:
                self.log.error(
                    'SoftAp association stress run %s failed. Err: %s' %
                    (str(run + 1), err.details))
            else:
                self.log.info('SoftAp association stress run %s successful.' %
                              str(run + 1))
                passed_count += 1

        if passed_count < iterations:
            asserts.fail(
                'SoftAp association stress test passed on %s/%s runs.' %
                (passed_count, iterations))

        asserts.explicit_pass(
            'SoftAp association stress test passed on %s/%s runs.' %
            (passed_count, iterations))


# Test Cases

    def test_soft_ap_2g_open_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_OPEN,
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_open_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_OPEN,
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_5G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_open_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_OPEN,
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_2g_wep_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_WEP,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_wep_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WEP,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_5G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_wep_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WEP,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client, )

    def test_soft_ap_2g_wpa_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_WPA,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_wpa_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_5G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_wpa_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_2g_wpa2_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_WPA2,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_wpa2_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA2,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_5G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_wpa2_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA2,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_2g_wpa3_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_WPA3,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_wpa3_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA3,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_wpa3_local(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA3,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_2g_open_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_OPEN,
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_open_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_OPEN,
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_5G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_open_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_OPEN,
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_2g_wep_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_WEP,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_wep_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WEP,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_5G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_wep_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WEP,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_2g_wpa_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_WPA,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_wpa_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_5G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_wpa_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_2g_wpa2_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_WPA2,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_wpa2_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA2,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_5G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_wpa2_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA2,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_2g_wpa3_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_WPA3,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_5g_wpa3_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA3,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_soft_ap_any_wpa3_unrestricted(self):
        soft_ap_params = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_5G),
            'security_type': SECURITY_WPA3,
            'password':
            utils.rand_ascii_str(hostapd_constants.MIN_WPA_PSK_LENGTH),
            'connectivity_mode': CONNECTIVITY_MODE_UNRESTRICTED,
            'operating_band': OPERATING_BAND_ANY
        }
        self.start_soft_ap(soft_ap_params)
        self.verify_soft_ap_associate_and_pass_traffic(self.primary_client,
                                                       soft_ap_params)

    def test_multi_client(self):
        """Tests multi-client association with a single soft AP network.

        This tests associates a variable length list of clients, verfying it can
        can ping the SoftAP and pass traffic, and then verfies all previously
        associated clients can still ping and pass traffic.

        The same occurs in reverse for disassocations.

        SoftAP parameters can be changed from default via ACTS config:
        Example Config
        "soft_ap_test_params" : {
            "multi_client_test_params": {
                "ssid": "testssid",
                "security_type": "wpa2",
                "password": "password",
                "connectivity_mode": "local_only",
                "operating_band": "only_2_4_ghz"
            }
        }
        """
        # TODO(fxb/59335): Validate clients on network can reach eachother.
        asserts.skip_if(
            len(self.clients) < 2, 'Test requires at least 2 SoftAPClients')

        test_params = self.soft_ap_test_params.get('multi_client_test_params',
                                                   {})
        soft_ap_params = get_soft_ap_params_from_config_or_default(test_params)

        self.start_soft_ap(soft_ap_params)

        dut_ap_interface = self.get_dut_interface_by_role(INTERFACE_ROLE_AP)
        associated = []

        for client in self.clients:
            # Associate new client
            self.verify_soft_ap_associate_and_ping(client, soft_ap_params)
            client_ipv4 = self.wait_for_ipv4_address(
                client.w_device, ANDROID_DEFAULT_WLAN_INTERFACE)

            # Verify previously associated clients still behave as expected
            for client_map in associated:
                associated_client = client_map['client']
                associated_client_ipv4 = client_map['ipv4']
                self.log.info(
                    'Verifying previously associated client %s still functions correctly.'
                    % associated_client.w_device.device.serial)
                if not self.client_is_connected_to_soft_ap(associated_client,
                                                           check_traffic=True):
                    asserts.fail(
                        'Previously associated client %s failed checks after '
                        'client %s associated.' %
                        (associated_client.w_device.device.serial,
                         client.w_device.device.serial))

            associated.append({'client': client, 'ipv4': client_ipv4})

        self.log.info(
            'All devices successfully associated. Beginning disassociations.')

        while len(associated) > 0:
            # Disassociate client
            client = associated.pop()['client']
            self.disconnect_from_soft_ap(client.w_device)

            # Verify still connected clients still behave as expected
            for client_map in associated:
                associated_client = client_map['client']
                associated_client_ipv4 = client_map['ipv4']

                self.log.info(
                    'Verifying still associated client %s still functions '
                    'correctly.' % associated_client.w_device.device.serial)
                if not self.client_is_connected_to_soft_ap(associated_client,
                                                           check_traffic=True):
                    asserts.fail(
                        'Previously associated client %s failed checks after'
                        ' client %s disassociated.' %
                        (associated_client.w_device.device.serial,
                         client.w_device.device.serial))

        self.log.info('All disassociations occurred smoothly.')

    def test_simultaneous_soft_ap_and_client(self):
        """ Tests FuchsiaDevice DUT can act as a client and a SoftAP
        simultaneously.

        Raises:
            ConnectionError: if DUT fails to connect as client
            RuntimeError: if parallel processes fail to join
            TestFailure: if DUT fails to pass traffic as either a client or an
                AP
        """
        # TODO(fxb/59306): Fix flakey parallel streams.
        asserts.skip_if(not self.access_point, 'No access point provided.')

        self.log.info('Setting up AP using hostapd.')

        # Configure AP
        ap_params = self.user_params.get('soft_ap_test_params',
                                         {}).get('ap_params', {})
        channel = ap_params.get('channel', 11)
        ssid = ap_params.get('ssid', 'apnet')
        security_mode = ap_params.get('security_mode', None)
        password = ap_params.get('password', None)
        if security_mode:
            security = hostapd_security.Security(security_mode, password)
        else:
            security = None

        # Setup AP and associate DUT
        if not setup_ap_and_associate(access_point=self.access_point,
                                      client=self.dut,
                                      profile_name='whirlwind',
                                      channel=channel,
                                      security=security,
                                      password=password,
                                      ssid=ssid):
            raise ConnectionError(
                'FuchsiaDevice DUT failed to connect as client to AP.')
        self.log.info('DUT successfully associated to AP network.')

        # Verify FuchsiaDevice's client interface has an ip address from AP
        dut_client_interface = self.get_dut_interface_by_role(
            INTERFACE_ROLE_CLIENT)

        # Verify FuchsiaDevice can ping AP
        lowest_5ghz_channel = 36
        if channel < lowest_5ghz_channel:
            ap_interface = self.access_point.wlan_2g
        else:
            ap_interface = self.access_point.wlan_5g
        ap_ipv4 = utils.get_interface_ip_addresses(
            self.access_point.ssh, ap_interface)['ipv4_private'][0]

        self.device_can_ping_addr(self.dut, ap_ipv4)

        # Setup SoftAP
        soft_ap_settings = {
            'ssid': utils.rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G),
            'security_type': SECURITY_OPEN,
            'connectivity_mode': CONNECTIVITY_MODE_LOCAL,
            'operating_band': OPERATING_BAND_2G
        }
        self.start_soft_ap(soft_ap_settings)

        # Get FuchsiaDevice's AP interface info
        dut_ap_interface = self.get_dut_interface_by_role(INTERFACE_ROLE_AP)

        # Associate primary client with SoftAP
        self.associate_with_soft_ap(self.primary_client.w_device,
                                    soft_ap_settings)

        # Verify primary client has an ip address from SoftAP
        client_ipv4 = self.wait_for_ipv4_address(
            self.primary_client.w_device, ANDROID_DEFAULT_WLAN_INTERFACE)

        # Verify primary client can ping SoftAP, and reverse
        self.device_can_ping_addr(self.primary_client.w_device,
                                  dut_ap_interface.ipv4)
        self.device_can_ping_addr(self.dut, client_ipv4)

        # Set up secondary iperf server of FuchsiaDevice
        self.log.info('Setting up second iperf server on FuchsiaDevice DUT.')
        secondary_iperf_server = iperf_server.IPerfServerOverSsh(
            self.iperf_server_config, DEFAULT_IPERF_PORT + 1, use_killall=True)
        secondary_iperf_server.start()

        # Set up iperf client on AP
        self.log.info('Setting up iperf client on AP.')
        ap_iperf_client = iperf_client.IPerfClientOverSsh(
            self.user_params['AccessPoint'][0]['ssh_config'])

        # Setup iperf processes:
        #     Primary client <-> SoftAP interface on FuchsiaDevice
        #     AP <-> Client interface on FuchsiaDevice
        process_errors = mp.Queue()
        iperf_soft_ap = mp.Process(
            target=self.run_iperf_traffic_parallel_process,
            args=[
                self.primary_client.ip_client, dut_ap_interface.ipv4,
                process_errors
            ])

        iperf_fuchsia_client = mp.Process(
            target=self.run_iperf_traffic_parallel_process,
            args=[ap_iperf_client, dut_client_interface.ipv4, process_errors],
            kwargs={'server_port': 5202})

        # Run iperf processes simultaneously
        self.log.info('Running simultaneous iperf traffic: between AP and DUT '
                      'client interface, and DUT AP interface and client.')

        iperf_soft_ap.start()
        iperf_fuchsia_client.start()

        # Block until processes can join or timeout
        for proc in [iperf_soft_ap, iperf_fuchsia_client]:
            proc.join(timeout=DEFAULT_IPERF_TIMEOUT)
            if proc.is_alive():
                proc.terminate()
                proc.join()
                raise RuntimeError('Failed to join process %s' % proc)

        # Stop iperf server (also stopped in teardown class as failsafe)
        secondary_iperf_server.stop()

        # Check errors from parallel processes
        if process_errors.empty():
            asserts.explicit_pass(
                'FuchsiaDevice was successfully able to pass traffic as a '
                'client and an AP simultaneously.')
        else:
            while not process_errors.empty():
                self.log.error('Error in iperf process: %s' %
                               process_errors.get())
            asserts.fail(
                'FuchsiaDevice failed to pass traffic as a client and an AP '
                'simultaneously.')

    def test_soft_ap_association_stress(self):
        """ Sets up a single AP and repeatedly associate/disassociate
        a client, verifying connection every time

        Each test creates 1 SoftAP and repeatedly associates/disassociates
        client.

        Example Config
        "soft_ap_test_params" : {
            "soft_ap_association_stress_tests": [
                {
                    "ssid": "test_network",
                    "security_type": "wpa2",
                    "password": "password",
                    "connectivity_mode": "local_only",
                    "operating_band": "only_2_4_ghz",
                    "iterations": 10
                }
            ]
        }
        """
        tests = self.soft_ap_test_params.get(
            'test_soft_ap_association_stress',
            [dict(test_name='test_soft_ap_association_stress_default')])

        test_settings_list = []
        for config_settings in tests:
            soft_ap_params = get_soft_ap_params_from_config_or_default(
                config_settings)
            test_type = config_settings.get('test_type',
                                            'associate_and_pass_traffic')
            iterations = config_settings.get('iterations',
                                             DEFAULT_STRESS_TEST_ITERATIONS)
            test_settings = {
                'test_name': config_settings['test_name'],
                'client': self.primary_client,
                'soft_ap_params': soft_ap_params,
                'test_type': test_type,
                'iterations': iterations
            }
            test_settings_list.append(test_settings)

        self.run_generated_testcases(self.run_soft_ap_association_stress_test,
                                     test_settings_list,
                                     name_func=get_test_name_from_settings)