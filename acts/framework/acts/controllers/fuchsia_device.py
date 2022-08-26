#!/usr/bin/env python3
#
#   Copyright 2018 - The Android Open Source Project
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

import backoff
import json
import logging
import os
import random
import re
import requests
import socket
import subprocess
import time

from acts import context
from acts import logger as acts_logger
from acts import signals
from acts import utils
from acts.controllers import pdu
from acts.libs.proc import job
from acts.utils import get_fuchsia_mdns_ipv6_address

from acts.controllers.fuchsia_lib.audio_lib import FuchsiaAudioLib
from acts.controllers.fuchsia_lib.basemgr_lib import FuchsiaBasemgrLib
from acts.controllers.fuchsia_lib.bt.avdtp_lib import FuchsiaAvdtpLib
from acts.controllers.fuchsia_lib.bt.ble_lib import FuchsiaBleLib
from acts.controllers.fuchsia_lib.bt.bts_lib import FuchsiaBtsLib
from acts.controllers.fuchsia_lib.bt.gattc_lib import FuchsiaGattcLib
from acts.controllers.fuchsia_lib.bt.gatts_lib import FuchsiaGattsLib
from acts.controllers.fuchsia_lib.bt.hfp_lib import FuchsiaHfpLib
from acts.controllers.fuchsia_lib.bt.rfcomm_lib import FuchsiaRfcommLib
from acts.controllers.fuchsia_lib.bt.sdp_lib import FuchsiaProfileServerLib
from acts.controllers.fuchsia_lib.ffx import FFX
from acts.controllers.fuchsia_lib.lib_controllers.netstack_controller import NetstackController
from acts.controllers.fuchsia_lib.lib_controllers.wlan_controller import WlanController
from acts.controllers.fuchsia_lib.lib_controllers.wlan_policy_controller import WlanPolicyController
from acts.controllers.fuchsia_lib.location.regulatory_region_lib import FuchsiaRegulatoryRegionLib
from acts.controllers.fuchsia_lib.logging_lib import FuchsiaLoggingLib
from acts.controllers.fuchsia_lib.netstack.netstack_lib import FuchsiaNetstackLib
from acts.controllers.fuchsia_lib.session_manager_lib import FuchsiaSessionManagerLib
from acts.controllers.fuchsia_lib.syslog_lib import FuchsiaSyslogError
from acts.controllers.fuchsia_lib.syslog_lib import create_syslog_process
from acts.controllers.fuchsia_lib.utils_lib import SshResults
from acts.controllers.fuchsia_lib.utils_lib import create_ssh_connection
from acts.controllers.fuchsia_lib.utils_lib import flash
from acts.controllers.fuchsia_lib.wlan_ap_policy_lib import FuchsiaWlanApPolicyLib
from acts.controllers.fuchsia_lib.wlan_deprecated_configuration_lib import FuchsiaWlanDeprecatedConfigurationLib
from acts.controllers.fuchsia_lib.wlan_lib import FuchsiaWlanLib
from acts.controllers.fuchsia_lib.wlan_policy_lib import FuchsiaWlanPolicyLib
from acts.controllers.fuchsia_lib.package_server import PackageServer

MOBLY_CONTROLLER_CONFIG_NAME = "FuchsiaDevice"
ACTS_CONTROLLER_REFERENCE_NAME = "fuchsia_devices"

CONTROL_PATH_REPLACE_VALUE = " ControlPath /tmp/fuchsia--%r@%h:%p"

FUCHSIA_DEVICE_EMPTY_CONFIG_MSG = "Configuration is empty, abort!"
FUCHSIA_DEVICE_NOT_LIST_CONFIG_MSG = "Configuration should be a list, abort!"
FUCHSIA_DEVICE_INVALID_CONFIG = ("Fuchsia device config must be either a str "
                                 "or dict. abort! Invalid element %i in %r")
FUCHSIA_DEVICE_NO_IP_MSG = "No IP address specified, abort!"
FUCHSIA_COULD_NOT_GET_DESIRED_STATE = "Could not %s %s."
FUCHSIA_INVALID_CONTROL_STATE = "Invalid control state (%s). abort!"

FUCHSIA_SSH_USERNAME = "fuchsia"
FUCHSIA_TIME_IN_NANOSECONDS = 1000000000

SL4F_APK_NAME = "com.googlecode.android_scripting"
DAEMON_INIT_TIMEOUT_SEC = 1

DAEMON_ACTIVATED_STATES = ["running", "start"]
DAEMON_DEACTIVATED_STATES = ["stop", "stopped"]

FUCHSIA_RECONNECT_AFTER_REBOOT_TIME = 5

CHANNEL_OPEN_TIMEOUT = 5

FUCHSIA_REBOOT_TYPE_SOFT = 'soft'
FUCHSIA_REBOOT_TYPE_SOFT_AND_FLASH = 'flash'
FUCHSIA_REBOOT_TYPE_HARD = 'hard'

FUCHSIA_DEFAULT_CONNECT_TIMEOUT = 60
FUCHSIA_DEFAULT_COMMAND_TIMEOUT = 60

FUCHSIA_DEFAULT_CLEAN_UP_COMMAND_TIMEOUT = 15

FUCHSIA_COUNTRY_CODE_TIMEOUT = 15
FUCHSIA_DEFAULT_COUNTRY_CODE_US = 'US'

MDNS_LOOKUP_RETRY_MAX = 3

START_SL4F_V2_CMD = 'start_sl4f'

VALID_ASSOCIATION_MECHANISMS = {None, 'policy', 'drivers'}


class FuchsiaDeviceError(signals.ControllerError):
    pass


class FuchsiaConfigError(signals.ControllerError):
    """Incorrect FuchsiaDevice configuration."""
    pass


class FuchsiaSSHError(signals.TestError):
    """A SSH command returned with a non-zero status code."""

    def __init__(self, command, result):
        super().__init__(
            f'SSH command "{command}" unexpectedly returned {result.exit_status}: {result.stderr}'
        )
        self.result = result


class FuchsiaSSHTransportError(signals.TestError):
    """Failure to send an SSH command."""
    pass


def create(configs):
    if not configs:
        raise FuchsiaDeviceError(FUCHSIA_DEVICE_EMPTY_CONFIG_MSG)
    elif not isinstance(configs, list):
        raise FuchsiaDeviceError(FUCHSIA_DEVICE_NOT_LIST_CONFIG_MSG)
    for index, config in enumerate(configs):
        if isinstance(config, str):
            configs[index] = {"ip": config}
        elif not isinstance(config, dict):
            raise FuchsiaDeviceError(FUCHSIA_DEVICE_INVALID_CONFIG %
                                     (index, configs))
    return get_instances(configs)


def destroy(fds):
    for fd in fds:
        fd.clean_up()
        del fd


def get_info(fds):
    """Get information on a list of FuchsiaDevice objects.

    Args:
        fds: A list of FuchsiaDevice objects.

    Returns:
        A list of dict, each representing info for FuchsiaDevice objects.
    """
    device_info = []
    for fd in fds:
        info = {"ip": fd.ip}
        device_info.append(info)
    return device_info


def get_instances(fds_conf_data):
    """Create FuchsiaDevice instances from a list of Fuchsia ips.

    Args:
        fds_conf_data: A list of dicts that contain Fuchsia device info.

    Returns:
        A list of FuchsiaDevice objects.
    """

    return [FuchsiaDevice(fd_conf_data) for fd_conf_data in fds_conf_data]


def find_routes_to(dest_ip):
    """Find the routes used to reach a destination.

    Look through the routing table for the routes that would be used without
    sending any packets. This is especially helpful for when the device is
    currently unreachable.

    Only natively supported on Linux. MacOS has iproute2mac, but it doesn't
    support JSON formatted output.

    TODO(http://b/238924195): Add support for MacOS.

    Args:
        dest_ip: IP address of the destination

    Throws:
        CalledProcessError: if the ip command returns a non-zero exit code
        JSONDecodeError: if the ip command doesn't return JSON

    """
    resp = subprocess.run(f"ip -json route get {dest_ip}".split(),
                          capture_output=True,
                          check=True)
    return json.loads(resp.stdout)


def find_host_ip(device_ip):
    """Find the host's source IP used to reach a device.

    Not all host interfaces can talk to a given device. This limitation can
    either be physical through hardware or virtual through routing tables.
    Look through the routing table without sending any packets then return the
    preferred source IP address.

    Args:
        device_ip: IP address of the device
    """
    routes = find_routes_to(device_ip)
    if len(routes) != 1:
        raise FuchsiaDeviceError(
            f"Expected only one route to {device_ip}, got {routes}")

    route = routes[0]
    if not 'prefsrc' in route:
        raise FuchsiaDeviceError(f'Route does not contain "srcpref": {route}')
    return route["prefsrc"]


class FuchsiaDevice:
    """Class representing a Fuchsia device.

    Each object of this class represents one Fuchsia device in ACTS.

    Attributes:
        ip: The full address or Fuchsia abstract name to contact the Fuchsia
            device at
        log: A logger object.
        ssh_port: The SSH TCP port number of the Fuchsia device.
        sl4f_port: The SL4F HTTP port number of the Fuchsia device.
        ssh_config: The ssh_config for connecting to the Fuchsia device.
    """

    def __init__(self, fd_conf_data):
        """
        Args:
            fd_conf_data: A dict of a fuchsia device configuration data
                Required keys:
                    ip: IP address of fuchsia device
                optional key:
                    sl4_port: Port for the sl4f web server on the fuchsia device
                              (Default: 80)
                    ssh_config: Location of the ssh_config file to connect to
                        the fuchsia device
                        (Default: None)
                    ssh_port: Port for the ssh server on the fuchsia device
                              (Default: 22)
        """
        self.conf_data = fd_conf_data
        if "ip" not in fd_conf_data:
            raise FuchsiaDeviceError(FUCHSIA_DEVICE_NO_IP_MSG)
        self.ip = fd_conf_data["ip"]
        self.orig_ip = fd_conf_data["ip"]
        self.sl4f_port = fd_conf_data.get("sl4f_port", 80)
        self.ssh_port = fd_conf_data.get("ssh_port", 22)
        self.ssh_config = fd_conf_data.get("ssh_config", None)
        self.ssh_priv_key = fd_conf_data.get("ssh_priv_key", None)
        self.authorized_file = fd_conf_data.get("authorized_file_loc", None)
        self.serial_number = fd_conf_data.get("serial_number", None)
        self.device_type = fd_conf_data.get("device_type", None)
        self.product_type = fd_conf_data.get("product_type", None)
        self.board_type = fd_conf_data.get("board_type", None)
        self.build_number = fd_conf_data.get("build_number", None)
        self.build_type = fd_conf_data.get("build_type", None)
        self.server_path = fd_conf_data.get("server_path", None)
        self.specific_image = fd_conf_data.get("specific_image", None)
        self.ffx_binary_path = fd_conf_data.get("ffx_binary_path", None)
        self.pm_binary_path = fd_conf_data.get("pm_binary_path", None)
        self.packages_path = fd_conf_data.get("packages_path", None)
        self.mdns_name = fd_conf_data.get("mdns_name", None)

        # Instead of the input ssh_config, a new config is generated with proper
        # ControlPath to the test output directory.
        output_path = context.get_current_context().get_base_output_path()
        generated_ssh_config = os.path.join(output_path,
                                            "ssh_config_{}".format(self.ip))
        self._set_control_path_config(self.ssh_config, generated_ssh_config)
        self.ssh_config = generated_ssh_config

        self.ssh_username = fd_conf_data.get("ssh_username",
                                             FUCHSIA_SSH_USERNAME)
        self.hard_reboot_on_fail = fd_conf_data.get("hard_reboot_on_fail",
                                                    False)
        self.take_bug_report_on_fail = fd_conf_data.get(
            "take_bug_report_on_fail", False)
        self.device_pdu_config = fd_conf_data.get("PduDevice", None)
        self.config_country_code = fd_conf_data.get(
            'country_code', FUCHSIA_DEFAULT_COUNTRY_CODE_US).upper()
        self._persistent_ssh_conn = None

        # WLAN interface info is populated inside configure_wlan
        self.wlan_client_interfaces = {}
        self.wlan_ap_interfaces = {}
        self.wlan_client_test_interface_name = fd_conf_data.get(
            'wlan_client_test_interface', None)
        self.wlan_ap_test_interface_name = fd_conf_data.get(
            'wlan_ap_test_interface', None)

        # Whether to use 'policy' or 'drivers' for WLAN connect/disconnect calls
        # If set to None, wlan is not configured.
        self.association_mechanism = None
        # Defaults to policy layer, unless otherwise specified in the config
        self.default_association_mechanism = fd_conf_data.get(
            'association_mechanism', 'policy')

        # Whether to clear and preserve existing saved networks and client
        # connections state, to be restored at device teardown.
        self.default_preserve_saved_networks = fd_conf_data.get(
            'preserve_saved_networks', True)

        if utils.is_valid_ipv4_address(self.ip):
            self.address = "http://{}:{}".format(self.ip, self.sl4f_port)
        elif utils.is_valid_ipv6_address(self.ip):
            self.address = "http://[{}]:{}".format(self.ip, self.sl4f_port)
        else:
            mdns_ip = None
            for retry_counter in range(MDNS_LOOKUP_RETRY_MAX):
                mdns_ip = get_fuchsia_mdns_ipv6_address(self.ip)
                if mdns_ip:
                    break
                else:
                    time.sleep(1)
            if mdns_ip and utils.is_valid_ipv6_address(mdns_ip):
                # self.ip was actually an mdns name. Use it for self.mdns_name
                # unless one was explicitly provided.
                self.mdns_name = self.mdns_name or self.ip
                self.ip = mdns_ip
                self.address = "http://[{}]:{}".format(self.ip, self.sl4f_port)
            else:
                raise ValueError('Invalid IP: %s' % self.ip)

        self.log = acts_logger.create_tagged_trace_logger(
            "FuchsiaDevice | %s" % self.orig_ip)

        self.init_address = self.address + "/init"
        self.cleanup_address = self.address + "/cleanup"
        self.print_address = self.address + "/print_clients"
        self.ping_rtt_match = re.compile(r'RTT Min/Max/Avg '
                                         r'= \[ (.*?) / (.*?) / (.*?) \] ms')

        # TODO(): Come up with better client numbering system
        self.client_id = "FuchsiaClient" + str(random.randint(0, 1000000))
        self.test_counter = 0
        self.serial = re.sub('[.:%]', '_', self.ip)
        log_path_base = getattr(logging, 'log_path', '/tmp/logs')
        self.log_path = os.path.join(log_path_base,
                                     'FuchsiaDevice%s' % self.serial)
        self.fuchsia_log_file_path = os.path.join(
            self.log_path, "fuchsialog_%s_debug.txt" % self.serial)
        self.log_process = None
        self.package_server = None

        self.init_libraries()

        self.setup_commands = fd_conf_data.get('setup_commands', [])
        self.teardown_commands = fd_conf_data.get('teardown_commands', [])

        # Assuming using SL4F CFv2, we'll fallback to using CFv1 if v2 is
        # not present.
        self.sl4f_v1 = False

        try:
            self.start_services()
            self.run_commands_from_config(self.setup_commands)
        except Exception as e:
            # Prevent a threading error, since controller isn't fully up yet.
            self.clean_up()
            self.stop_sl4f_on_fuchsia_device()
            raise e

    def _set_control_path_config(self, old_config, new_config):
        """Given an input ssh_config, write to a new config with proper
        ControlPath values in place, if it doesn't exist already.

        Args:
            old_config: string, path to the input config
            new_config: string, path to store the new config
        """
        if os.path.isfile(new_config):
            return

        ssh_config_copy = ""

        with open(old_config, 'r') as file:
            ssh_config_copy = re.sub('(\sControlPath\s.*)',
                                     CONTROL_PATH_REPLACE_VALUE,
                                     file.read(),
                                     flags=re.M)
        with open(new_config, 'w') as file:
            file.write(ssh_config_copy)

    def init_libraries(self):
        # Grab commands from FuchsiaAudioLib
        self.audio_lib = FuchsiaAudioLib(self.address, self.test_counter,
                                         self.client_id)

        # Grab commands from FuchsiaAvdtpLib
        self.avdtp_lib = FuchsiaAvdtpLib(self.address, self.test_counter,
                                         self.client_id)

        # Grab commands from FuchsiaHfpLib
        self.hfp_lib = FuchsiaHfpLib(self.address, self.test_counter,
                                     self.client_id)

        # Grab commands from FuchsiaRfcommLib
        self.rfcomm_lib = FuchsiaRfcommLib(self.address, self.test_counter,
                                           self.client_id)

        # Grab commands from FuchsiaBasemgrLib
        self.basemgr_lib = FuchsiaBasemgrLib(self.address, self.test_counter,
                                             self.client_id)
        # Grab commands from FuchsiaBleLib
        self.ble_lib = FuchsiaBleLib(self.address, self.test_counter,
                                     self.client_id)
        # Grab commands from FuchsiaBtsLib
        self.bts_lib = FuchsiaBtsLib(self.address, self.test_counter,
                                     self.client_id)
        # Grab commands from FuchsiaGattcLib
        self.gattc_lib = FuchsiaGattcLib(self.address, self.test_counter,
                                         self.client_id)
        # Grab commands from FuchsiaGattsLib
        self.gatts_lib = FuchsiaGattsLib(self.address, self.test_counter,
                                         self.client_id)

        # Grab commands from FuchsiaLoggingLib
        self.logging_lib = FuchsiaLoggingLib(self.address, self.test_counter,
                                             self.client_id)

        # Grab commands from FuchsiaNetstackLib
        self.netstack_lib = FuchsiaNetstackLib(self.address, self.test_counter,
                                               self.client_id)

        # Grab commands from FuchsiaProfileServerLib
        self.sdp_lib = FuchsiaProfileServerLib(self.address, self.test_counter,
                                               self.client_id)

        # Grab commands from FuchsiaRegulatoryRegionLib
        self.regulatory_region_lib = FuchsiaRegulatoryRegionLib(
            self.address, self.test_counter, self.client_id)

        # Grab commands from FuchsiaSessionManagerLib
        self.session_manager_lib = FuchsiaSessionManagerLib(self)

        # Grabs command from FuchsiaWlanDeprecatedConfigurationLib
        self.wlan_deprecated_configuration_lib = (
            FuchsiaWlanDeprecatedConfigurationLib(self.address,
                                                  self.test_counter,
                                                  self.client_id))

        # Grab commands from FuchsiaWlanLib
        self.wlan_lib = FuchsiaWlanLib(self.address, self.test_counter,
                                       self.client_id)

        # Grab commands from FuchsiaWlanApPolicyLib
        self.wlan_ap_policy_lib = FuchsiaWlanApPolicyLib(
            self.address, self.test_counter, self.client_id)

        # Grab commands from FuchsiaWlanPolicyLib
        self.wlan_policy_lib = FuchsiaWlanPolicyLib(self.address,
                                                    self.test_counter,
                                                    self.client_id)

        # Contains Netstack functions
        self.netstack_controller = NetstackController(self)

        # Contains WLAN core functions
        self.wlan_controller = WlanController(self)

        # Contains WLAN policy functions like save_network, remove_network, etc
        self.wlan_policy_controller = WlanPolicyController(self)

    def start_package_server(self):
        if not self.pm_binary_path or not self.packages_path:
            self.log.warn(
                "Either pm_binary_path or packages_path is not specified. "
                "Assuming a package server is already running and configured on "
                "the DUT. If this is not the case, either run your own package "
                "server, or configure these fields appropriately. "
                "This is usually required for the Fuchsia iPerf3 client or "
                "other testing utilities not on device cache.")
            return

        self.package_server = PackageServer(self.pm_binary_path,
                                            self.packages_path)
        self.package_server.start()

        # Remove any existing repositories that may be stale.
        try:
            self.send_command_ssh(f"pkgctl repo rm fuchsia-pkg://fuchsia.com")
        except FuchsiaSSHError as e:
            if not 'NOT_FOUND' in e.result.stderr:
                raise e

        # Configure the device with the new repository.
        host_ip = find_host_ip(self.ip)
        repo_url = f"http://{host_ip}:{self.package_server.port}"
        self.send_command_ssh(
            f"pkgctl repo add url -f 2 -n fuchsia.com {repo_url}/config.json")
        self.log.info(f'Added repo "fuchsia.com" from {repo_url}')

    @backoff.on_exception(
        backoff.constant,
        (ConnectionRefusedError, requests.exceptions.ConnectionError),
        interval=1.5,
        max_tries=4)
    def init_sl4f_connection(self):
        """Initializes HTTP connection with SL4F server."""
        self.log.debug("Initializing SL4F server connection")
        init_data = json.dumps({
            "jsonrpc": "2.0",
            "id": self.build_id(self.test_counter),
            "method": "sl4f.sl4f_init",
            "params": {
                "client_id": self.client_id
            }
        })

        requests.get(url=self.init_address, data=init_data)
        self.test_counter += 1

    @property
    def ffx(self):
        """Get the ffx module configured for this device.

        The ffx module uses lazy-initialization; it will initialize an ffx
        connection to the device when it is required.

        If ffx needs to be reinitialized, delete the "ffx" property and attempt
        access again. Note re-initialization will interrupt any running ffx
        calls.
        """
        if not hasattr(self, '_ffx'):
            if not self.ffx_binary_path:
                raise FuchsiaConfigError(
                    'Must provide "ffx_binary_path: <path to FFX binary>" in the device config'
                )
            if not self.mdns_name:
                raise FuchsiaConfigError(
                    'Must provide "mdns_name: <device mDNS name>" in the device config'
                )
            self._ffx = FFX(self.ffx_binary_path, self.mdns_name, self.ip,
                            self.ssh_priv_key)
        return self._ffx

    @ffx.deleter
    def ffx(self):
        if not hasattr(self, '_ffx'):
            return
        self._ffx.clean_up()
        del self._ffx

    def run_commands_from_config(self, cmd_dicts):
        """Runs commands on the Fuchsia device from the config file. Useful for
        device and/or Fuchsia specific configuration.

        Args:
            cmd_dicts: list of dictionaries containing the following
                'cmd': string, command to run on device
                'timeout': int, seconds to wait for command to run (optional)
                'skip_status_code_check': bool, disregard errors if true

        Raises:
            FuchsiaDeviceError: if any of the commands return a non-zero status
                code and skip_status_code_check is false or undefined.
        """
        for cmd_dict in cmd_dicts:
            try:
                cmd = cmd_dict['cmd']
            except KeyError:
                raise FuchsiaDeviceError(
                    'To run a command via config, you must provide key "cmd" '
                    'containing the command string.')

            timeout = cmd_dict.get('timeout', FUCHSIA_DEFAULT_COMMAND_TIMEOUT)
            # Catch both boolean and string values from JSON
            skip_status_code_check = 'true' == str(
                cmd_dict.get('skip_status_code_check', False)).lower()

            try:
                if skip_status_code_check:
                    self.log.info(
                        f'Running command "{cmd}" and ignoring result.')
                else:
                    self.log.info(f'Running command "{cmd}".')

                result = self.send_command_ssh(
                    cmd,
                    timeout=timeout,
                    skip_status_code_check=skip_status_code_check)
                self.log.debug(result)
            except FuchsiaSSHError as e:
                raise FuchsiaDeviceError(
                    'Failed device specific commands for initial configuration'
                ) from e

    def build_id(self, test_id):
        """Concatenates client_id and test_id to form a command_id

        Args:
            test_id: string, unique identifier of test command
        """
        return self.client_id + "." + str(test_id)

    def configure_wlan(self,
                       association_mechanism=None,
                       preserve_saved_networks=None):
        """
        Readies device for WLAN functionality. If applicable, connects to the
        policy layer and clears/saves preexisting saved networks.

        Args:
            association_mechanism: string, 'policy' or 'drivers'. If None, uses
                the default value from init (can be set by ACTS config)
            preserve_saved_networks: bool, whether to clear existing saved
                networks, and preserve them for restoration later. If None, uses
                the default value from init (can be set by ACTS config)

        Raises:
            FuchsiaDeviceError, if configuration fails
        """

        # Set the country code US by default, or country code provided
        # in ACTS config
        self.configure_regulatory_domain(self.config_country_code)

        # If args aren't provided, use the defaults, which can be set in the
        # config.
        if association_mechanism is None:
            association_mechanism = self.default_association_mechanism
        if preserve_saved_networks is None:
            preserve_saved_networks = self.default_preserve_saved_networks

        if association_mechanism not in VALID_ASSOCIATION_MECHANISMS:
            raise FuchsiaDeviceError(
                'Invalid FuchsiaDevice association_mechanism: %s' %
                association_mechanism)

        # Allows for wlan to be set up differently in different tests
        if self.association_mechanism:
            self.deconfigure_wlan()

        self.association_mechanism = association_mechanism

        self.log.info('Configuring WLAN w/ association mechanism: %s' %
                      association_mechanism)
        if association_mechanism == 'drivers':
            self.log.warn(
                'You may encounter unusual device behavior when using the '
                'drivers directly for WLAN. This should be reserved for '
                'debugging specific issues. Normal test runs should use the '
                'policy layer.')
            if preserve_saved_networks:
                self.log.warn(
                    'Unable to preserve saved networks when using drivers '
                    'association mechanism (requires policy layer control).')
        else:
            # This requires SL4F calls, so it can only happen with actual
            # devices, not with unit tests.
            self.wlan_policy_controller._configure_wlan(
                preserve_saved_networks)

        # Retrieve WLAN client and AP interfaces
        self.wlan_controller.update_wlan_interfaces()

    def deconfigure_wlan(self):
        """
        Stops WLAN functionality (if it has been started). Used to allow
        different tests to use WLAN differently (e.g. some tests require using
        wlan policy, while the abstract wlan_device can be setup to use policy
        or drivers)

        Raises:
            FuchsiaDeviveError, if deconfigure fails.
        """
        if not self.association_mechanism:
            self.log.debug(
                'WLAN not configured before deconfigure was called.')
            return
        # If using policy, stop client connections. Otherwise, just clear
        # variables.
        if self.association_mechanism != 'drivers':
            self.wlan_policy_controller._deconfigure_wlan()
        self.association_mechanism = None

    def reboot(self,
               use_ssh=False,
               unreachable_timeout=FUCHSIA_DEFAULT_CONNECT_TIMEOUT,
               ping_timeout=FUCHSIA_DEFAULT_CONNECT_TIMEOUT,
               ssh_timeout=FUCHSIA_DEFAULT_CONNECT_TIMEOUT,
               reboot_type=FUCHSIA_REBOOT_TYPE_SOFT,
               testbed_pdus=None):
        """Reboot a FuchsiaDevice.

        Soft reboots the device, verifies it becomes unreachable, then verifies
        it comes back online. Re-initializes services so the tests can continue.

        Args:
            use_ssh: bool, if True, use fuchsia shell command via ssh to reboot
                instead of SL4F.
            unreachable_timeout: int, time to wait for device to become
                unreachable.
            ping_timeout: int, time to wait for device to respond to pings.
            ssh_timeout: int, time to wait for device to be reachable via ssh.
            reboot_type: boolFUCHSIA_REBOOT_TYPE_SOFT or
                FUCHSIA_REBOOT_TYPE_HARD
            testbed_pdus: list, all testbed PDUs

        Raises:
            ConnectionError, if device fails to become unreachable, fails to
                come back up, or if SL4F does not setup correctly.
        """
        skip_unreachable_check = False
        # Call Reboot
        if reboot_type == FUCHSIA_REBOOT_TYPE_SOFT:
            if use_ssh:
                self.log.info('Sending reboot command via SSH.')
                with utils.SuppressLogOutput():
                    self.clean_up_services()
                    self.stop_sl4f_on_fuchsia_device()
                    self.send_command_ssh(
                        'dm reboot',
                        timeout=FUCHSIA_RECONNECT_AFTER_REBOOT_TIME,
                        skip_status_code_check=True)
            else:
                self.log.info('Calling SL4F reboot command.')
                self.clean_up_services()
                with utils.SuppressLogOutput():
                    self.hardware_power_statecontrol_lib.suspendReboot(
                        timeout=3)
                    self.stop_sl4f_on_fuchsia_device()
        # TODO(http://b/230890623): Refactor control_daemon to split cleanup.
        elif reboot_type == FUCHSIA_REBOOT_TYPE_SOFT_AND_FLASH:
            flash(self, use_ssh, FUCHSIA_RECONNECT_AFTER_REBOOT_TIME)
            skip_unreachable_check = True
        elif reboot_type == FUCHSIA_REBOOT_TYPE_HARD:
            self.log.info('Power cycling FuchsiaDevice (%s)' % self.ip)
            if not testbed_pdus:
                raise AttributeError('Testbed PDUs must be supplied '
                                     'to hard reboot a fuchsia_device.')
            device_pdu, device_pdu_port = pdu.get_pdu_port_for_device(
                self.device_pdu_config, testbed_pdus)
            with utils.SuppressLogOutput():
                self.clean_up_services()
            self.log.info('Killing power to FuchsiaDevice (%s)...' % self.ip)
            device_pdu.off(str(device_pdu_port))
        else:
            raise ValueError('Invalid reboot type: %s' % reboot_type)
        if not skip_unreachable_check:
            # Wait for unreachable
            self.log.info('Verifying device is unreachable.')
            timeout = time.time() + unreachable_timeout
            while (time.time() < timeout):
                if utils.can_ping(job, self.ip):
                    self.log.debug('Device is still pingable. Retrying.')
                else:
                    if reboot_type == FUCHSIA_REBOOT_TYPE_HARD:
                        self.log.info(
                            'Restoring power to FuchsiaDevice (%s)...' %
                            self.ip)
                        device_pdu.on(str(device_pdu_port))
                    break
            else:
                self.log.info(
                    'Device failed to go offline. Restarting services...')
                self.start_services()
                raise ConnectionError('Device never went down.')
            self.log.info('Device is unreachable as expected.')
        if reboot_type == FUCHSIA_REBOOT_TYPE_HARD:
            self.log.info('Restoring power to FuchsiaDevice (%s)...' % self.ip)
            device_pdu.on(str(device_pdu_port))

        self.log.info('Waiting for device to respond to pings.')
        end_time = time.time() + ping_timeout
        while time.time() < end_time:
            if utils.can_ping(job, self.ip):
                break
            else:
                self.log.debug('Device is not pingable. Retrying in 1 second.')
                time.sleep(1)
        else:
            raise ConnectionError('Device never came back online.')
        self.log.info('Device responded to pings.')

        self.log.info('Waiting for device to allow ssh connection.')
        end_time = time.time() + ssh_timeout
        while time.time() < end_time:
            try:
                self.send_command_ssh('\n')
            except Exception:
                self.log.debug(
                    'Could not SSH to device. Retrying in 1 second.')
                time.sleep(1)
            else:
                break
        else:
            raise ConnectionError('Failed to connect to device via SSH.')
        self.log.info('Device now available via ssh.')

        # Creating new log process, start it, start new persistent ssh session,
        # start SL4F, and connect via SL4F
        self.log.info(f'Restarting services on FuchsiaDevice {self.ip}')
        self.start_services()

        # Verify SL4F is up.
        self.log.info('Verifying SL4F commands can run.')
        try:
            self.hwinfo_lib.getDeviceInfo()
        except Exception as err:
            raise ConnectionError(
                'Failed to connect and run command via SL4F. Err: %s' % err)

        # Reconfigure country code, as it does not persist after reboots
        self.configure_regulatory_domain(self.config_country_code)
        try:
            self.run_commands_from_config(self.setup_commands)
        except FuchsiaDeviceError:
            # Prevent a threading error, since controller isn't fully up yet.
            self.clean_up()
            self.stop_sl4f_on_fuchsia_device()
            raise FuchsiaDeviceError(
                'Failed to run setup commands after reboot.')

        # If wlan was configured before reboot, it must be configured again
        # after rebooting, as it was before reboot. No preserving should occur.
        if self.association_mechanism:
            pre_reboot_association_mechanism = self.association_mechanism
            # Prevent configure_wlan from thinking it needs to deconfigure first
            self.association_mechanism = None
            self.configure_wlan(
                association_mechanism=pre_reboot_association_mechanism,
                preserve_saved_networks=False)

        self.log.info(
            'Device has rebooted, SL4F is reconnected and functional.')

    def send_command_ssh(self,
                         test_cmd,
                         connect_timeout=FUCHSIA_DEFAULT_CONNECT_TIMEOUT,
                         timeout=FUCHSIA_DEFAULT_COMMAND_TIMEOUT,
                         skip_status_code_check=False):
        """Sends an SSH command to a Fuchsia device

        Args:
            test_cmd: string, command to send to Fuchsia device over SSH.
            connect_timeout: Timeout to wait for connecting via SSH.
            timeout: Timeout to wait for a command to complete.
            skip_status_code_check: Whether to check for the status code.

        Returns:
            A SshResults object containing the results of the ssh command.

        Raises:
            FuchsiaConfigError: if ssh_config is not specified
            FuchsiaSSHError: if the SSH command returns a non-zero status code
                and skip_status_code_check is False.
            FuchsiaSSHTransportError: if SSH fails to run the command
        """
        if not self.ssh_config:
            raise FuchsiaConfigError(
                'Cannot send ssh commands since "FuchsiaDevice.ssh_config" was not specified'
            )

        ssh_conn = None
        result = False

        try:
            ssh_conn = create_ssh_connection(self.ip,
                                             self.ssh_username,
                                             self.ssh_config,
                                             ssh_port=self.ssh_port,
                                             connect_timeout=connect_timeout)
            cmd_result_stdin, cmd_result_stdout, cmd_result_stderr = (
                ssh_conn.exec_command(test_cmd, timeout=timeout))
            result = SshResults(cmd_result_stdin, cmd_result_stdout,
                                cmd_result_stderr, cmd_result_stdout.channel)
        except Exception as e:
            raise FuchsiaSSHTransportError(
                f'Failed sending SSH command "{test_cmd}"') from e
        finally:
            if ssh_conn is not None:
                ssh_conn.close()

        if result.exit_status != 0 and not skip_status_code_check:
            raise FuchsiaSSHError(test_cmd, result)
        return result

    def version(self, timeout=FUCHSIA_DEFAULT_COMMAND_TIMEOUT):
        """Returns the version of Fuchsia running on the device.

        Args:
            timeout: (int) Seconds to wait for command to run.

        Returns:
            A string containing the Fuchsia version number or nothing if there
            is no version information attached during the build.
            For example, "5.20210713.2.1" or "".

        Raises:
            FFXTimeout: when the command times out.
            FFXError: when the command returns non-zero and skip_status_code_check is False.
        """
        target_info_json = self.ffx.run("target show --json").stdout
        target_info = json.loads(target_info_json)
        build_info = [
            entry for entry in target_info if entry["label"] == "build"
        ]
        if len(build_info) != 1:
            self.log.warning(
                f'Expected one entry with label "build", found {build_info}')
            return ""
        version_info = [
            child for child in build_info[0]["child"]
            if child["label"] == "version"
        ]
        if len(version_info) != 1:
            self.log.warning(
                f'Expected one entry child with label "version", found {build_info}'
            )
            return ""
        return version_info[0]["value"]

    def ping(self,
             dest_ip,
             count=3,
             interval=1000,
             timeout=1000,
             size=25,
             additional_ping_params=None):
        """Pings from a Fuchsia device to an IPv4 address or hostname

        Args:
            dest_ip: (str) The ip or hostname to ping.
            count: (int) How many icmp packets to send.
            interval: (int) How long to wait between pings (ms)
            timeout: (int) How long to wait before having the icmp packet
                timeout (ms).
            size: (int) Size of the icmp packet.
            additional_ping_params: (str) command option flags to
                append to the command string

        Returns:
            A dictionary for the results of the ping.  The dictionary contains
            the following items:
                status: Whether the ping was successful.
                rtt_min: The minimum round trip time of the ping.
                rtt_max: The minimum round trip time of the ping.
                rtt_avg: The avg round trip time of the ping.
                stdout: The standard out of the ping command.
                stderr: The standard error of the ping command.
        """
        rtt_min = None
        rtt_max = None
        rtt_avg = None
        self.log.debug("Pinging %s..." % dest_ip)
        if not additional_ping_params:
            additional_ping_params = ''

        try:
            ping_result = self.send_command_ssh(
                f'ping -c {count} -i {interval} -t {timeout} -s {size} '
                f'{additional_ping_params} {dest_ip}')
        except FuchsiaSSHError as e:
            ping_result = e.result

        if ping_result.stderr:
            status = False
        else:
            status = True
            rtt_line = ping_result.stdout.split('\n')[:-1]
            rtt_line = rtt_line[-1]
            rtt_stats = re.search(self.ping_rtt_match, rtt_line)
            rtt_min = rtt_stats.group(1)
            rtt_max = rtt_stats.group(2)
            rtt_avg = rtt_stats.group(3)
        return {
            'status': status,
            'rtt_min': rtt_min,
            'rtt_max': rtt_max,
            'rtt_avg': rtt_avg,
            'stdout': ping_result.stdout,
            'stderr': ping_result.stderr
        }

    def can_ping(self,
                 dest_ip,
                 count=1,
                 interval=1000,
                 timeout=1000,
                 size=25,
                 additional_ping_params=None):
        """Returns whether fuchsia device can ping a given dest address"""
        ping_result = self.ping(dest_ip,
                                count=count,
                                interval=interval,
                                timeout=timeout,
                                size=size,
                                additional_ping_params=additional_ping_params)
        return ping_result['status']

    def print_clients(self):
        """Gets connected clients from SL4F server"""
        self.log.debug("Request to print clients")
        print_id = self.build_id(self.test_counter)
        print_args = {}
        print_method = "sl4f.sl4f_print_clients"
        data = json.dumps({
            "jsonrpc": "2.0",
            "id": print_id,
            "method": print_method,
            "params": print_args
        })

        r = requests.get(url=self.print_address, data=data).json()
        self.test_counter += 1

        return r

    def clean_up(self):
        """Cleans up the FuchsiaDevice object, releases any resources it
        claimed, and restores saved networks if applicable. For reboots, use
        clean_up_services only.

        Note: Any exceptions thrown in this method must be caught and handled,
        ensuring that clean_up_services is run. Otherwise, the syslog listening
        thread will never join and will leave tests hanging.
        """
        # If and only if wlan is configured, and using the policy layer
        if self.association_mechanism == 'policy':
            try:
                self.wlan_policy_controller._clean_up()
            except Exception as err:
                self.log.warning('Unable to clean up WLAN Policy layer: %s' %
                                 err)
        try:
            self.run_commands_from_config(self.teardown_commands)
        except Exception as err:
            self.log.warning('Failed to run teardown_commands: %s' % err)

        # This MUST be run, otherwise syslog threads will never join.
        self.clean_up_services()

        if self.package_server:
            self.package_server.clean_up()

    def clean_up_services(self):
        """ Cleans up FuchsiaDevice services (e.g. SL4F). Subset of clean_up,
        to be used for reboots, when testing is to continue (as opposed to
        teardown after testing is finished.)
        """
        cleanup_id = self.build_id(self.test_counter)
        cleanup_args = {}
        cleanup_method = "sl4f.sl4f_cleanup"
        data = json.dumps({
            "jsonrpc": "2.0",
            "id": cleanup_id,
            "method": cleanup_method,
            "params": cleanup_args
        })

        try:
            response = requests.get(
                url=self.cleanup_address,
                data=data,
                timeout=FUCHSIA_DEFAULT_CLEAN_UP_COMMAND_TIMEOUT).json()
            self.log.debug(response)
        except Exception as err:
            self.log.exception("Cleanup request failed with %s:" % err)
        finally:
            self.test_counter += 1
            self.stop_host_services()

    def check_process_state(self, process_name):
        """Checks the state of a process on the Fuchsia device

        Returns:
            True if the process_name is running
            False if process_name is not running
        """
        ps_cmd = self.send_command_ssh("ps")
        return process_name in ps_cmd.stdout

    def check_process_with_expectation(self, process_name, expectation=None):
        """Checks the state of a process on the Fuchsia device and returns
        true or false depending the stated expectation

        Args:
            process_name: The name of the process to check for.
            expectation: The state expectation of state of process
        Returns:
            True if the state of the process matches the expectation
            False if the state of the process does not match the expectation
        """
        process_state = self.check_process_state(process_name)
        if expectation in DAEMON_ACTIVATED_STATES:
            return process_state
        elif expectation in DAEMON_DEACTIVATED_STATES:
            return not process_state
        else:
            raise ValueError("Invalid expectation value (%s). abort!" %
                             expectation)

    def control_daemon(self, process_name, action):
        """Starts or stops a process on a Fuchsia device

        Args:
            process_name: the name of the process to start or stop
            action: specify whether to start or stop a process
        """
        if not (process_name[-4:] == '.cmx' or process_name[-4:] == '.cml'):
            process_name = '%s.cmx' % process_name
        unable_to_connect_msg = None
        process_state = False
        try:
            if not self._persistent_ssh_conn:
                self._persistent_ssh_conn = (create_ssh_connection(
                    self.ip,
                    self.ssh_username,
                    self.ssh_config,
                    ssh_port=self.ssh_port))
            self._persistent_ssh_conn.exec_command(
                "killall %s" % process_name, timeout=CHANNEL_OPEN_TIMEOUT)
            # This command will effectively stop the process but should
            # be used as a cleanup before starting a process.  It is a bit
            # confusing to have the msg saying "attempting to stop
            # the process" after the command already tried but since both start
            # and stop need to run this command, this is the best place
            # for the command.
            if action in DAEMON_ACTIVATED_STATES:
                self.log.debug("Attempting to start Fuchsia "
                               "devices services.")
                self._persistent_ssh_conn.exec_command(
                    "run fuchsia-pkg://fuchsia.com/%s#meta/%s &" %
                    (process_name[:-4], process_name))
                process_initial_msg = (
                    "%s has not started yet. Waiting %i second and "
                    "checking again." %
                    (process_name, DAEMON_INIT_TIMEOUT_SEC))
                process_timeout_msg = ("Timed out waiting for %s to start." %
                                       process_name)
                unable_to_connect_msg = ("Unable to start %s no Fuchsia "
                                         "device via SSH. %s may not "
                                         "be started." %
                                         (process_name, process_name))
            elif action in DAEMON_DEACTIVATED_STATES:
                process_initial_msg = ("%s is running. Waiting %i second and "
                                       "checking again." %
                                       (process_name, DAEMON_INIT_TIMEOUT_SEC))
                process_timeout_msg = ("Timed out waiting trying to kill %s." %
                                       process_name)
                unable_to_connect_msg = ("Unable to stop %s on Fuchsia "
                                         "device via SSH. %s may "
                                         "still be running." %
                                         (process_name, process_name))
            else:
                raise FuchsiaDeviceError(FUCHSIA_INVALID_CONTROL_STATE %
                                         action)
            timeout_counter = 0
            while not process_state:
                self.log.info(process_initial_msg)
                time.sleep(DAEMON_INIT_TIMEOUT_SEC)
                timeout_counter += 1
                process_state = (self.check_process_with_expectation(
                    process_name, expectation=action))
                if timeout_counter == (DAEMON_INIT_TIMEOUT_SEC * 3):
                    self.log.info(process_timeout_msg)
                    break
            if not process_state:
                raise FuchsiaDeviceError(FUCHSIA_COULD_NOT_GET_DESIRED_STATE %
                                         (action, process_name))
        except Exception as e:
            self.log.info(unable_to_connect_msg)
            raise e
        finally:
            # TODO(http://b/230890623): Refactor control_daemon to split cleanup.
            if action == 'stop' and (process_name == 'sl4f'
                                     or process_name == 'sl4f.cmx'):
                self._persistent_ssh_conn.close()
                self._persistent_ssh_conn = None

    def check_connect_response(self, connect_response):
        if connect_response.get("error") is None:
            # Checks the response from SL4F and if there is no error, check
            # the result.
            connection_result = connect_response.get("result")
            if not connection_result:
                # Ideally the error would be present but just outputting a log
                # message until available.
                self.log.debug("Connect call failed, aborting!")
                return False
            else:
                # Returns True if connection was successful.
                return True
        else:
            # the response indicates an error - log and raise failure
            self.log.debug("Aborting! - Connect call failed with error: %s" %
                           connect_response.get("error"))
            return False

    def check_disconnect_response(self, disconnect_response):
        if disconnect_response.get("error") is None:
            # Returns True if disconnect was successful.
            return True
        else:
            # the response indicates an error - log and raise failure
            self.log.debug("Disconnect call failed with error: %s" %
                           disconnect_response.get("error"))
            return False

    # TODO(fxb/64657): Determine more stable solution to country code config on
    # device bring up.
    def configure_regulatory_domain(self, desired_country_code):
        """Allows the user to set the device country code via ACTS config

        Usage:
            In FuchsiaDevice config, add "country_code": "<CC>"
        """
        if self.ssh_config:
            # Country code can be None, from ACTS config.
            if desired_country_code:
                desired_country_code = desired_country_code.upper()
                response = self.regulatory_region_lib.setRegion(
                    desired_country_code)
                if response.get('error'):
                    raise FuchsiaDeviceError(
                        'Failed to set regulatory domain. Err: %s' %
                        response['error'])
                end_time = time.time() + FUCHSIA_COUNTRY_CODE_TIMEOUT
                while time.time() < end_time:
                    ascii_cc = self.wlan_lib.wlanGetCountry(0).get('result')
                    # Convert ascii_cc to string, then compare
                    if ascii_cc and (''.join(chr(c) for c in ascii_cc).upper()
                                     == desired_country_code):
                        self.log.debug('Country code successfully set to %s.' %
                                       desired_country_code)
                        return
                    self.log.debug('Country code not yet updated. Retrying.')
                    time.sleep(1)
                raise FuchsiaDeviceError('Country code never updated to %s' %
                                         desired_country_code)

    @backoff.on_exception(backoff.constant,
                          (FuchsiaSyslogError, socket.timeout),
                          interval=1.5,
                          max_tries=4)
    def start_services(self):
        """Starts long running services on the Fuchsia device.

        Starts a syslog streaming process, SL4F server, and initializes a
        connection to the SL4F server.

        """
        self.log.debug("Attempting to start Fuchsia device services on %s." %
                       self.ip)
        if self.ssh_config:
            self.log_process = create_syslog_process(self.serial,
                                                     self.log_path,
                                                     self.ip,
                                                     self.ssh_username,
                                                     self.ssh_config,
                                                     ssh_port=self.ssh_port)

            try:
                self.log_process.start()
            except FuchsiaSyslogError as e:
                # Before backing off and retrying, stop the syslog if it
                # failed to setup correctly, to prevent threading error when
                # retrying
                self.log_process.stop()
                raise

            self.start_sl4f_on_fuchsia_device()
            self.init_sl4f_connection()

    def stop_host_services(self):
        """Stops ffx daemon and ssh connection to streaming logs on the host"""
        self.log.debug("Attempting to stop host device services on %s." %
                       self.ip)
        del self.ffx
        if self.ssh_config:
            if self.log_process:
                self.log_process.stop()

    def start_sl4f_on_fuchsia_device(self):
        self.log.debug(
            "Attempting to start SL4F server on Fuchsia device %s." % self.ip)
        if self.ssh_config:
            try:
                self.send_command_ssh(START_SL4F_V2_CMD).stdout
                self.sl4f_v1 = False
            except FuchsiaSSHError:
                # TODO(fxbug.dev/99331) Remove support to run SL4F in CFv1 mode
                # once ACTS no longer use images that comes with only CFv1 SL4F.
                self.log.warn(
                    "Running SL4F in CFv1 mode, "
                    "this is deprecated for images built after 5/9/2022, "
                    "see https://fxbug.dev/77056 for more info.")
                self.control_daemon("sl4f.cmx", "start")
                self.sl4f_v1 = True

    def stop_sl4f_on_fuchsia_device(self):
        """Stops SL4F server on the fuchsia device

        This also closes the persistent ssh connection to the SLF4 daemon which
        is important to prevent ssh exceptions on subsequent commands.
        """
        self.log.debug("Attempting to stop SL4F server on Fuchsia device %s." %
                       self.ip)
        if self.ssh_config and self.sl4f_v1:
            try:
                self.control_daemon("sl4f.cmx", "stop")
            except Exception as err:
                self.log.exception("Failed to stop sl4f.cmx with: %s. "
                                   "This is expected if running CFv2." % err)
        else:
            if hasattr(self, '_ffx'):
                # TODO(b/234054431): This calls ffx after it has been stopped.
                # Refactor controller clean up such that ffx is called after SL4F
                # has been stopped.
                self.ffx.run('component stop /core/sl4f')
                del self.ffx

    def load_config(self, config):
        pass

    def take_bug_report(self, test_name=None, begin_time=None):
        """Takes a bug report on the device and stores it in a file.

        Args:
            test_name: DEPRECATED. Do not specify this argument; it is only used
                for logging. Name of the test case that triggered this bug
                report.
            begin_time: DEPRECATED. Do not specify this argument; it allows
                overwriting of bug reports when this function is called several
                times in one test. Epoch time when the test started. If not
                specified, the current time will be used.
        """
        if not self.ssh_config:
            self.log.warn(
                'Skipping take_bug_report because ssh_config is not specified')
            return

        if test_name:
            self.log.info(
                f"Taking snapshot of {self.mdns_name} for {test_name}")
        else:
            self.log.info(f"Taking snapshot of {self.mdns_name}")

        epoch = begin_time if begin_time else utils.get_current_epoch_time()
        time_stamp = acts_logger.normalize_log_line_timestamp(
            acts_logger.epoch_to_log_line_timestamp(epoch))
        out_dir = context.get_current_context().get_full_output_path()
        out_path = os.path.join(out_dir, f'{self.mdns_name}_{time_stamp}.zip')

        try:
            subprocess.run(
                [f"ssh -F {self.ssh_config} {self.ip} snapshot > {out_path}"],
                shell=True)
            self.log.info(f'Snapshot saved to {out_path}')
        except Exception as err:
            self.log.error(f'Failed to take snapshot: {err}')

    def take_bt_snoop_log(self, custom_name=None):
        """Takes a the bt-snoop log from the device and stores it in a file
        in a pcap format.
        """
        bt_snoop_path = context.get_current_context().get_full_output_path()
        time_stamp = acts_logger.normalize_log_line_timestamp(
            acts_logger.epoch_to_log_line_timestamp(time.time()))
        out_name = "FuchsiaDevice%s_%s" % (
            self.serial, time_stamp.replace(" ", "_").replace(":", "-"))
        out_name = "%s.pcap" % out_name
        if custom_name:
            out_name = "%s_%s.pcap" % (self.serial, custom_name)
        else:
            out_name = "%s.pcap" % out_name
        full_out_path = os.path.join(bt_snoop_path, out_name)
        bt_snoop_data = self.send_command_ssh(
            'bt-snoop-cli -d -f pcap').raw_stdout
        bt_snoop_file = open(full_out_path, 'wb')
        bt_snoop_file.write(bt_snoop_data)
        bt_snoop_file.close()


class FuchsiaDeviceLoggerAdapter(logging.LoggerAdapter):

    def process(self, msg, kwargs):
        msg = "[FuchsiaDevice|%s] %s" % (self.extra["ip"], msg)
        return msg, kwargs
