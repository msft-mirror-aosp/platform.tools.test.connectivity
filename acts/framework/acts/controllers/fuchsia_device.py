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
import platform
import os
import random
import re
import requests
import subprocess
import socket
import time

from acts import context
from acts import logger as acts_logger
from acts import utils
from acts import signals

from acts.controllers import pdu

from acts.controllers.fuchsia_lib.backlight_lib import FuchsiaBacklightLib
from acts.controllers.fuchsia_lib.bt.avdtp_lib import FuchsiaAvdtpLib
from acts.controllers.fuchsia_lib.light_lib import FuchsiaLightLib

from acts.controllers.fuchsia_lib.bt.ble_lib import FuchsiaBleLib
from acts.controllers.fuchsia_lib.bt.bts_lib import FuchsiaBtsLib
from acts.controllers.fuchsia_lib.bt.gattc_lib import FuchsiaGattcLib
from acts.controllers.fuchsia_lib.bt.gatts_lib import FuchsiaGattsLib
from acts.controllers.fuchsia_lib.bt.sdp_lib import FuchsiaProfileServerLib
from acts.controllers.fuchsia_lib.gpio_lib import FuchsiaGpioLib
from acts.controllers.fuchsia_lib.hardware_power_statecontrol_lib import FuchsiaHardwarePowerStatecontrolLib
from acts.controllers.fuchsia_lib.hwinfo_lib import FuchsiaHwinfoLib
from acts.controllers.fuchsia_lib.i2c_lib import FuchsiaI2cLib
from acts.controllers.fuchsia_lib.input_report_lib import FuchsiaInputReportLib
from acts.controllers.fuchsia_lib.kernel_lib import FuchsiaKernelLib
from acts.controllers.fuchsia_lib.location.regulatory_region_lib import FuchsiaRegulatoryRegionLib
from acts.controllers.fuchsia_lib.logging_lib import FuchsiaLoggingLib
from acts.controllers.fuchsia_lib.netstack.netstack_lib import FuchsiaNetstackLib
from acts.controllers.fuchsia_lib.ram_lib import FuchsiaRamLib
from acts.controllers.fuchsia_lib.syslog_lib import FuchsiaSyslogError
from acts.controllers.fuchsia_lib.syslog_lib import start_syslog
from acts.controllers.fuchsia_lib.sysinfo_lib import FuchsiaSysInfoLib
from acts.controllers.fuchsia_lib.utils_lib import create_ssh_connection
from acts.controllers.fuchsia_lib.utils_lib import SshResults
from acts.controllers.fuchsia_lib.wlan_deprecated_configuration_lib import FuchsiaWlanDeprecatedConfigurationLib
from acts.controllers.fuchsia_lib.wlan_lib import FuchsiaWlanLib
from acts.controllers.fuchsia_lib.wlan_ap_policy_lib import FuchsiaWlanApPolicyLib
from acts.controllers.fuchsia_lib.wlan_policy_lib import FuchsiaWlanPolicyLib
from acts.libs.proc import job
from acts.utils import get_fuchsia_mdns_ipv6_address

MOBLY_CONTROLLER_CONFIG_NAME = "FuchsiaDevice"
ACTS_CONTROLLER_REFERENCE_NAME = "fuchsia_devices"

FUCHSIA_DEVICE_EMPTY_CONFIG_MSG = "Configuration is empty, abort!"
FUCHSIA_DEVICE_NOT_LIST_CONFIG_MSG = "Configuration should be a list, abort!"
FUCHSIA_DEVICE_INVALID_CONFIG = ("Fuchsia device config must be either a str "
                                 "or dict. abort! Invalid element %i in %r")
FUCHSIA_DEVICE_NO_IP_MSG = "No IP address specified, abort!"
FUCHSIA_COULD_NOT_GET_DESIRED_STATE = "Could not %s %s."
FUCHSIA_INVALID_CONTROL_STATE = "Invalid control state (%s). abort!"
FUCHSIA_SSH_CONFIG_NOT_DEFINED = ("Cannot send ssh commands since the "
                                  "ssh_config was not specified in the Fuchsia"
                                  "device config.")

FUCHSIA_SSH_USERNAME = "fuchsia"
FUCHSIA_TIME_IN_NANOSECONDS = 1000000000

SL4F_APK_NAME = "com.googlecode.android_scripting"
DAEMON_INIT_TIMEOUT_SEC = 1

DAEMON_ACTIVATED_STATES = ["running", "start"]
DAEMON_DEACTIVATED_STATES = ["stop", "stopped"]

FUCHSIA_DEFAULT_LOG_CMD = 'iquery --absolute_paths --cat --format= --recursive'
FUCHSIA_DEFAULT_LOG_ITEMS = [
    '/hub/c/scenic.cmx/[0-9]*/out/objects',
    '/hub/c/root_presenter.cmx/[0-9]*/out/objects',
    '/hub/c/wlanstack2.cmx/[0-9]*/out/public',
    '/hub/c/basemgr.cmx/[0-9]*/out/objects'
]

FUCHSIA_RECONNECT_AFTER_REBOOT_TIME = 5

ENABLE_LOG_LISTENER = True

CHANNEL_OPEN_TIMEOUT = 5

FUCHSIA_GET_VERSION_CMD = 'cat /config/build-info/version'

FUCHSIA_REBOOT_TYPE_SOFT = 'soft'
FUCHSIA_REBOOT_TYPE_HARD = 'hard'

FUCHSIA_DEFAULT_CONNECT_TIMEOUT = 30
FUCHSIA_DEFAULT_COMMAND_TIMEOUT = 3600

FUCHSIA_COUNTRY_CODE_TIMEOUT = 15
FUCHSIA_DEFAULT_COUNTRY_CODE_US = 'US'

MDNS_LOOKUP_RETRY_MAX = 3
SAVED_NETWORKS = "saved_networks"
CLIENT_STATE = "client_connections_state"
CONNECTIONS_ENABLED = "ConnectionsEnabled"
CONNECTIONS_DISABLED = "ConnectionsDisabled"


class FuchsiaDeviceError(signals.ControllerError):
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


class FuchsiaDevice:
    """Class representing a Fuchsia device.

    Each object of this class represents one Fuchsia device in ACTS.

    Attributes:
        address: The full address to contact the Fuchsia device at
        log: A logger object.
        port: The TCP port number of the Fuchsia device.
    """
    def __init__(self, fd_conf_data):
        """
        Args:
            fd_conf_data: A dict of a fuchsia device configuration data
                Required keys:
                    ip: IP address of fuchsia device
                optional key:
                    port: Port for the sl4f web server on the fuchsia device
                        (Default: 80)
                    ssh_config: Location of the ssh_config file to connect to
                        the fuchsia device
                        (Default: None)
        """
        self.conf_data = fd_conf_data
        if "ip" not in fd_conf_data:
            raise FuchsiaDeviceError(FUCHSIA_DEVICE_NO_IP_MSG)
        self.ip = fd_conf_data["ip"]
        self.port = fd_conf_data.get("port", 80)
        self.ssh_config = fd_conf_data.get("ssh_config", None)
        self.ssh_username = fd_conf_data.get("ssh_username",
                                             FUCHSIA_SSH_USERNAME)
        self.hard_reboot_on_fail = fd_conf_data.get("hard_reboot_on_fail",
                                                    False)
        self.device_pdu_config = fd_conf_data.get("PduDevice", None)
        self.config_country_code = fd_conf_data.get(
            'country_code', FUCHSIA_DEFAULT_COUNTRY_CODE_US)
        self._persistent_ssh_conn = None

        # Whether to use 'policy' (default) or 'drivers' for connect/disconnect
        # calls
        self.association_mechanism = fd_conf_data.get("association_mechanism",
                                                      None)

        self.log = acts_logger.create_tagged_trace_logger(
            "FuchsiaDevice | %s" % self.ip)

        if utils.is_valid_ipv4_address(self.ip):
            self.address = "http://{}:{}".format(self.ip, self.port)
        elif utils.is_valid_ipv6_address(self.ip):
            self.address = "http://[{}]:{}".format(self.ip, self.port)
        else:
            mdns_ip = None
            for retry_counter in range(MDNS_LOOKUP_RETRY_MAX):
                mdns_ip = get_fuchsia_mdns_ipv6_address(self.ip)
                if mdns_ip:
                    break
                else:
                    time.sleep(1)
            if mdns_ip and utils.is_valid_ipv6_address(mdns_ip):
                self.ip = mdns_ip
                self.address = "http://[{}]:{}".format(self.ip, self.port)
            else:
                raise ValueError('Invalid IP: %s' % self.ip)

        self.log = acts_logger.create_tagged_trace_logger(
            "FuchsiaDevice | %s" % self.ip)

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

        # Grab commands from FuchsiaAvdtpLib
        self.avdtp_lib = FuchsiaAvdtpLib(self.address, self.test_counter,
                                         self.client_id)

        # Grab commands from FuchsiaLightLib
        self.light_lib = FuchsiaLightLib(self.address, self.test_counter,
                                         self.client_id)

        # Grab commands from FuchsiaBacklightLib
        self.backlight_lib = FuchsiaBacklightLib(self.address,
                                                 self.test_counter,
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

        # Grab commands from FuchsiaGpioLib
        self.gpio_lib = FuchsiaGpioLib(self.address, self.test_counter,
                                       self.client_id)

        # Grab commands from FuchsiaHardwarePowerStatecontrolLib
        self.hardware_power_statecontrol_lib = FuchsiaHardwarePowerStatecontrolLib(
            self.address, self.test_counter, self.client_id)

        # Grab commands from FuchsiaHwinfoLib
        self.hwinfo_lib = FuchsiaHwinfoLib(self.address, self.test_counter,
                                           self.client_id)

        # Grab commands from FuchsiaI2cLib
        self.i2c_lib = FuchsiaI2cLib(self.address, self.test_counter,
                                     self.client_id)

        # Grab commands from FuchsiaInputReportLib
        self.input_report_lib = FuchsiaInputReportLib(self.address,
                                                      self.test_counter,
                                                      self.client_id)

        # Grab commands from FuchsiaKernelLib
        self.kernel_lib = FuchsiaKernelLib(self.address, self.test_counter,
                                           self.client_id)

        # Grab commands from FuchsiaLoggingLib
        self.logging_lib = FuchsiaLoggingLib(self.address, self.test_counter,
                                             self.client_id)

        # Grab commands from FuchsiaNetstackLib
        self.netstack_lib = FuchsiaNetstackLib(self.address, self.test_counter,
                                               self.client_id)

        # Grab commands from FuchsiaLightLib
        self.ram_lib = FuchsiaRamLib(self.address, self.test_counter,
                                     self.client_id)

        # Grab commands from FuchsiaProfileServerLib
        self.sdp_lib = FuchsiaProfileServerLib(self.address, self.test_counter,
                                               self.client_id)

        # Grab commands from FuchsiaRegulatoryRegionLib
        self.regulatory_region_lib = FuchsiaRegulatoryRegionLib(
            self.address, self.test_counter, self.client_id)

        # Grab commands from FuchsiaSysInfoLib
        self.sysinfo_lib = FuchsiaSysInfoLib(self.address, self.test_counter,
                                             self.client_id)

        # Grabs command from FuchsiaWlanDeprecatedConfigurationLib
        self.wlan_deprecated_configuration_lib = FuchsiaWlanDeprecatedConfigurationLib(
            self.address, self.test_counter, self.client_id)

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

        self.skip_sl4f = False
        # Start sl4f on device
        self.start_services(skip_sl4f=self.skip_sl4f)
        # Init server
        self.init_server_connection()

        self.configure_regulatory_domain(self.config_country_code)

        self.setup_commands = fd_conf_data.get('setup_commands', [])
        self.teardown_commands = fd_conf_data.get('teardown_commands', [])

        try:
            self.run_commands_from_config(self.setup_commands)
        except FuchsiaDeviceError:
            # Prevent a threading error, since controller isn't fully up yet.
            self.clean_up()
            raise FuchsiaDeviceError('Failed to run setup commands.')

        # Ensure it's an actual device, not a mock unit test
        if self.ssh_config:
            # Allow tests to control the WLAN policy layer
            self.wlan_policy_lib.wlanCreateClientController()
            self.preserved_networks_and_client_state = self.remove_and_preserve_networks_and_client_state(
            )
            client_conn_response = self.wlan_policy_lib.wlanStartClientConnections(
            )
            if client_conn_response.get('error'):
                raise FuchsiaDeviceError(
                    'Failed to start wlan client connections: %s' %
                    client_conn_response['error'])

    @backoff.on_exception(
        backoff.constant,
        (ConnectionRefusedError, requests.exceptions.ConnectionError),
        interval=1.5,
        max_tries=4)
    def init_server_connection(self):
        """Initializes HTTP connection with SL4F server."""
        self.log.debug("Initializing server connection")
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

    def run_commands_from_config(self, cmd_dicts):
        """Runs commands on the Fuchsia device from the config file. Useful for
        device and/or Fuchsia specific configuration.

        Args:
            cmd_dicts: list of dictionaries containing the following
                'cmd': string, command to run on device
                'timeout': int, seconds to wait for command to run (optional)
                'skip_status_code_check': bool, disregard errors if true
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

            self.log.info(
                'Running command "%s".%s' %
                (cmd, ' Ignoring result.' if skip_status_code_check else ''))
            result = self.send_command_ssh(
                cmd,
                timeout=timeout,
                skip_status_code_check=skip_status_code_check)

            if not skip_status_code_check and result.stderr:
                raise FuchsiaDeviceError(
                    'Error when running command "%s": %s' %
                    (cmd, result.stderr))

    def build_id(self, test_id):
        """Concatenates client_id and test_id to form a command_id

        Args:
            test_id: string, unique identifier of test command
        """
        return self.client_id + "." + str(test_id)

    def reboot(self,
               use_ssh=False,
               unreachable_timeout=FUCHSIA_DEFAULT_CONNECT_TIMEOUT,
               ping_timeout=FUCHSIA_DEFAULT_CONNECT_TIMEOUT,
               ssh_timeout=FUCHSIA_DEFAULT_CONNECT_TIMEOUT,
               reboot_type=FUCHSIA_REBOOT_TYPE_SOFT,
               testbed_pdus=None):
        """Reboot a FuchsiaDevice.

        Soft reboots the device, verifies it becomes unreachable, then verfifies
        it comes back online. Reinitializes SL4F so the tests can continue.

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
        # Call Reboot
        if reboot_type == FUCHSIA_REBOOT_TYPE_SOFT:
            if use_ssh:
                self.log.info('Sending reboot command via SSH.')
                with utils.SuppressLogOutput():
                    self.clean_up_services()
                    self.send_command_ssh(
                        'dm reboot',
                        timeout=FUCHSIA_RECONNECT_AFTER_REBOOT_TIME,
                        skip_status_code_check=True)
            else:
                self.log.info('Initializing reboot of FuchsiaDevice (%s)'
                              ' with SL4F.' % self.ip)
                self.log.info('Calling SL4F reboot command.')
                with utils.SuppressLogOutput():
                    if self.log_process:
                        self.log_process.stop()
                    self.hardware_power_statecontrol_lib.suspendReboot(
                        timeout=3)
                    if self._persistent_ssh_conn:
                        self._persistent_ssh_conn.close()
                        self._persistent_ssh_conn = None
        elif reboot_type == FUCHSIA_REBOOT_TYPE_HARD:
            self.log.info('Power cycling FuchsiaDevice (%s)' % self.ip)
            device_pdu, device_pdu_port = pdu.get_pdu_port_for_device(
                self.device_pdu_config, testbed_pdus)
            with utils.SuppressLogOutput():
                if self.log_process:
                    self.log_process.stop()
                if self._persistent_ssh_conn:
                    self._persistent_ssh_conn.close()
                    self._persistent_ssh_conn = None
            self.log.info('Killing power to FuchsiaDevice (%s)...' % self.ip)
            device_pdu.off(str(device_pdu_port))

        # Wait for unreachable
        self.log.info('Verifying device is unreachable.')
        timeout = time.time() + unreachable_timeout
        while (time.time() < timeout):
            if utils.can_ping(job, self.ip):
                self.log.debug('Device is still pingable. Retrying.')
            else:
                if reboot_type == FUCHSIA_REBOOT_TYPE_HARD:
                    self.log.info('Restoring power to FuchsiaDevice (%s)...' %
                                  self.ip)
                    device_pdu.on(str(device_pdu_port))
                break
        else:
            self.log.info('Device failed to go offline. Reintializing Sl4F.')
            self.start_services()
            self.init_server_connection()
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
        self.log.info(
            'Restarting log process and reinitiating SL4F on FuchsiaDevice %s'
            % self.ip)
        self.log_process.start()
        self.start_services()

        # Verify SL4F is up.
        self.log.info(
            'Initiating connection to SL4F and verifying commands can run.')
        try:
            self.init_server_connection()
            self.hwinfo_lib.getDeviceInfo()
        except Exception as err:
            raise ConnectionError(
                'Failed to connect and run command via SL4F. Err: %s' % err)

        try:
            self.run_commands_from_config(self.setup_commands)

        except FuchsiaDeviceError:
            # Prevent a threading error, since controller isn't fully up yet.
            self.clean_up()
            raise FuchsiaDeviceError(
                'Failed to run setup commands after reboot.')

        self.wlan_policy_lib.wlanCreateClientController()
        self.wlan_policy_lib.wlanStartClientConnections()
        self.wlan_policy_lib.wlanSetNewListener()

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
        """
        command_result = False
        ssh_conn = None
        if not self.ssh_config:
            self.log.warning(FUCHSIA_SSH_CONFIG_NOT_DEFINED)
        else:
            try:
                ssh_conn = create_ssh_connection(
                    self.ip,
                    self.ssh_username,
                    self.ssh_config,
                    connect_timeout=connect_timeout)
                cmd_result_stdin, cmd_result_stdout, cmd_result_stderr = (
                    ssh_conn.exec_command(test_cmd, timeout=timeout))
                if not skip_status_code_check:
                    command_result = SshResults(cmd_result_stdin,
                                                cmd_result_stdout,
                                                cmd_result_stderr,
                                                cmd_result_stdout.channel)
            except Exception as e:
                self.log.warning("Problem running ssh command: %s"
                                 "\n Exception: %s" % (test_cmd, e))
                return e
            finally:
                if ssh_conn is not None:
                    ssh_conn.close()
        return command_result

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
        ping_result = self.send_command_ssh(
            'ping -c %s -i %s -t %s -s %s %s %s' %
            (count, interval, timeout, size, additional_ping_params, dest_ip))
        if isinstance(ping_result, job.Error):
            ping_result = ping_result.result

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
        """Cleans up the FuchsiaDevice object and releases any resources it
        claimed.
        """
        self.restore_preserved_networks_and_client_state(
            self.preserved_networks_and_client_state)
        try:
            self.run_commands_from_config(self.teardown_commands)
        except FuchsiaDeviceError:
            self.log.warning('Failed to run teardown_commands.')

        self.clean_up_services()

    def clean_up_services(self):
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
            response = requests.get(url=self.cleanup_address, data=data).json()
            self.log.debug(response)
        except Exception as err:
            self.log.exception("Cleanup request failed with %s:" % err)
        finally:
            self.test_counter += 1
            self.stop_services()

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
        if not process_name[-4:] == '.cmx':
            process_name = '%s.cmx' % process_name
        unable_to_connect_msg = None
        process_state = False
        try:
            if not self._persistent_ssh_conn:
                self._persistent_ssh_conn = (create_ssh_connection(
                    self.ip, self.ssh_username, self.ssh_config))
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

    def policy_save_and_connect(self, ssid, security, password=None):
        """ Saves and connects to the network. This is the policy version of
            connect and check_connect_response because the policy layer
            requires a saved network and the policy connect does not return
            success or failure
        Args:
            ssid: The network name
            security: The security of the network as a string
            password: the credential of the network if it has one
        """
        # Save network and check response
        result_save = self.wlan_policy_lib.wlanSaveNetwork(ssid,
                                                           security,
                                                           target_pwd=password)
        if result_save.get("error") != None:
            self.log.info("Failed to save network (%s) for connection: %s" %
                          (ssid, result_save.get("error")))
            return False
        # Make connect call and check response
        result_connect = self.wlan_policy_lib.wlanConnect(ssid, security)
        if result_connect.get("error") != None:
            self.log.info("Failed to initiate connect with error: %s" %
                          result_connect.get("error"))
            return False
        return self.wait_for_connect(ssid, security)

    def wait_for_connect(self, ssid, security_type, timeout=30):
        """ Wait until the device has connected to the specified network, or raise
            a test failure if we time out
        Args:
            ssid: The network name to wait for a connection to.
            security_type: The security of the network we are trying connect to
            timeout: The seconds we will wait to see an update indicating a
                     connect to this network.
        Returns:
            True if we see a connect to the network, False otherwise.
        """
        security_type = str(security_type)
        # Wait until we've connected.
        end_time = time.time() + timeout
        while time.time() < end_time:
            time_left = end_time - time.time()
            if time_left <= 0:
                return False

            # if still connectin loop. If failed to connect, fail test
            try:
                update = self.wlan_policy_lib.wlanGetUpdate(timeout=time_left)
            except requests.exceptions.Timeout:
                self.log.info("Timed out waiting for response from device "
                              "while waiting for network with SSID \"%s\" to "
                              "connect. Device took too long to connect or "
                              "the request timed out for another reason." %
                              ssid)
                return False
            if update.get("error") != None:
                self.log.info("Error occurred getting status update: %s" %
                              update["error"])
                return False

            for network in update["result"]["networks"]:
                net_id = network['id']
                if not net_id["ssid"] == ssid or not net_id["type_"].upper(
                ) == security_type.upper():
                    continue
                if 'state' not in network:
                    self.log.info(
                        "Client state summary's network is missing field 'state'"
                    )
                    return False
                elif network["state"].upper() == "Connected".upper():
                    return True
            # Wait a bit before requesting another status update
            time.sleep(1)
        # Stopped getting updates because out timeout
        self.log.info("Timed out waiting for network with SSID \"%s\" to "
                      "connect" % ssid)
        return False

    def wait_for_disconnect(self,
                            ssid,
                            security_type,
                            state,
                            status,
                            timeout=30):
        """ Wait for a disconnect of the specified network on the given device. This
            will check that the correct connection state and disconnect status are
            given in update. If we do not see a disconnect after some time, this will
            return false.
        Args:
            ssid: The name of the network we are connecting to.
            security_type: The security as a string, ie "none", "wep", "wpa",
                        "wpa2", or "wpa3"
            state: The connection state we are expecting, ie "Disconnected" or
                "Failed"
            status: The disconnect status we expect, it "ConnectionStopped" or
                "ConnectionFailed"
            timeout: The seconds we will watch for a disconnect before giving up
        Returns: True if we saw a disconnect as specified, or False otherwise.
        """
        end_time = time.time() + timeout
        while time.time() < end_time:
            # Time out on waiting for update if past the time we allow for
            # waiting for disconnect
            time_left = end_time - time.time()
            if time_left <= 0:
                return False

            try:
                update = self.wlan_policy_lib.wlanGetUpdate(timeout=time_left)
            except requests.exceptions.Timeout:
                self.log.info("Timed out waiting for response from device "
                              "while waiting for network with SSID \"%s\" to "
                              "disconnect. Device took too long to disconnect "
                              "or the request timed out for another reason." %
                              ssid)
                return False

            if update.get("error") != None:
                self.log.info("Error occurred getting status update: %s" %
                              update["error"])
                return False
            # Update should include network, either connected to or recently disconnected.
            if len(update["result"]["networks"]) == 0:
                self.log.info("Status update is missing network")
                return False

            for network in update["result"]["networks"]:
                net_id = network['id']
                if not net_id["ssid"] == ssid or not net_id["type_"].upper(
                ) == security_type.upper():
                    continue
                if 'state' not in network or "status" not in network:
                    self.log.info(
                        "Client state summary's network is missing fields")
                    return False
                # If still connected, we will wait for another update and check again
                elif network["state"].upper() == "Connected".upper():
                    continue
                elif network["state"].upper() == "Connecting".upper():
                    self.log.info(
                        "Update is 'Connecting', but device should already be "
                        "connected; expected disconnect")
                    return False
                # Check that the network state and disconnect status are expected, ie
                # that it isn't ConnectionFailed when we expect ConnectionStopped
                elif network["state"].upper() != state.upper(
                ) or network["status"].upper() != status.upper():
                    self.log.info(
                        "Connection failed: a network failure occurred that is unrelated"
                        "to remove network or incorrect status update. \nExpected state: "
                        % (state, status, network))
                    return False
                else:
                    return True
            # Wait a bit before requesting another status update
            time.sleep(1)
        # Stopped getting updates because out timeout
        self.log.info("Timed out waiting for network with SSID \"%s\" to "
                      "connect" % ssid)
        return False

    def remove_all_and_disconnect(self):
        """ The policy level's version of disconnect. It removes all saved
            networks and watches to see that we are not connected to anything.
        Returns:
            True if we successfully remove all networks and disconnect
            False if there is an error or we timeout on the disconnect
        """
        self.wlan_policy_lib.wlanSetNewListener()
        result_remove = self.wlan_policy_lib.wlanRemoveAllNetworks()
        if result_remove.get('error') != None:
            self.log.info("Error occurred removing all networks: %s" %
                          result_remove.get('error'))
            return False
        return self.wait_for_no_connections()

    def wait_for_no_connections(self, timeout=30):
        """ Waits to see that there are no existing connections the device. This is
            to ensure a good starting point for tests that look for a connection.
        Returns:
            True if we successfully see no connections
            False if we timeout or get an error
        """
        start_time = time.time()
        while True:
            time_left = timeout - (time.time() - start_time)
            if time_left <= 0:
                self.log.info("Timed out waiting for disconnect")
                return False
            try:
                update = self.wlan_policy_lib.wlanGetUpdate(timeout=time_left)
            except requests.exceptions.Timeout:
                self.log.info(
                    "Timed out getting status update while waiting for all"
                    " connections to end.")
            if update["error"] != None:
                self.log.info("Failed to get status update")
                return False
            # If any network is connected or being connected to, wait for them
            # to disconnect.
            has_connection = False
            for network in update["result"]["networks"]:
                if network['state'].upper() in [
                        "Connected".upper(), "Connecting".upper()
                ]:
                    has_connection = True
                    break
            if not has_connection:
                return True

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
                response = self.regulatory_region_lib.setRegion(
                    desired_country_code)
                if response.get('error'):
                    raise FuchsiaDeviceError(
                        'Failed to set regulatory domain. Err: %s' %
                        response['error'])
                end_time = time.time() + FUCHSIA_COUNTRY_CODE_TIMEOUT
                while time.time() < end_time:
                    ascii_cc = self.wlan_lib.wlanGetCountry(0).get('result')
                    str_cc = ''.join(chr(c) for c in ascii_cc)
                    if str_cc == desired_country_code:
                        self.log.debug('Country code successfully set to %s.' %
                                       desired_country_code)
                        return
                    self.log.debug(
                        'Country code is still set to %s. Retrying.' % str_cc)
                    time.sleep(1)
                raise FuchsiaDeviceError('Country code never updated to %s' %
                                         desired_country_code)

    @backoff.on_exception(backoff.constant,
                          (FuchsiaSyslogError, socket.timeout),
                          interval=1.5,
                          max_tries=4)
    def start_services(self, skip_sl4f=False):
        """Starts long running services on the Fuchsia device.

        1. Start SL4F if not skipped.

        Args:
            skip_sl4f: Does not attempt to start SL4F if True.
        """
        self.log.debug("Attempting to start Fuchsia device services on %s." %
                       self.ip)
        if self.ssh_config:
            self.log_process = start_syslog(self.serial, self.log_path,
                                            self.ip, self.ssh_username,
                                            self.ssh_config)

            if ENABLE_LOG_LISTENER:
                try:
                    self.log_process.start()
                except FuchsiaSyslogError as e:
                    # Before backing off and retrying, stop the syslog if it
                    # failed to setup correctly, to prevent threading error when
                    # retrying
                    self.log_process.stop()
                    raise

            if not skip_sl4f:
                self.control_daemon("sl4f.cmx", "start")

            out_name = "fuchsia_device_%s_%s.txt" % (self.serial, 'fw_version')
            full_out_path = os.path.join(self.log_path, out_name)
            fuchsia_version = self.send_command_ssh(
                FUCHSIA_GET_VERSION_CMD).stdout
            fw_file = open(full_out_path, 'w')
            fw_file.write('%s\n' % fuchsia_version)
            fw_file.close()

    def stop_services(self):
        """Stops long running services on the fuchsia device.

        Terminate sl4f sessions if exist.
        """
        self.log.debug("Attempting to stop Fuchsia device services on %s." %
                       self.ip)
        if self.ssh_config:
            try:
                self.control_daemon("sl4f.cmx", "stop")
            except Exception as err:
                self.log.exception("Failed to stop sl4f.cmx with: %s" % err)
            if self.log_process:
                if ENABLE_LOG_LISTENER:
                    self.log_process.stop()

    def reinitialize_services(self):
        """Reinitialize long running services and establish connection to
        SL4F."""
        self.start_services()
        self.init_server_connection()
        self.configure_regulatory_domain(self.config_country_code)

    def save_network(self, ssid, security_type, password=None):
        """Saves a network via the polcu layer.

        Args:
            ssid: string, network to save
            security_type: string, security type of network
                (see wlan_policy_lib)
            password: string, password of network, if any

        Returns:
            True, if save successful, False otherwise
        """
        save_response = self.wlan_policy_lib.wlanSaveNetwork(
            ssid, security_type, password)
        if save_response.get('error'):
            self.log.warn('Failed to save network %s with error' %
                          save_response['error'])
            return False
        return True

    def remove_and_preserve_networks_and_client_state(self):
        """ Preserves networks already saved on devices before removing them to
            setup up for a clean test environment. Records the state of client
            connections before tests. Initializes the client controller
            and enables connections.
        Args:
            fuchsia_devices: the devices under test
        Returns:
            A dict of the data to restore after tests indexed by device. The
            data for each device is a dict of the saved data, ie saved networks
            and state of client connections.
        """
        # Save preexisting saved networks
        preserved_networks_and_state = {}
        saved_networks_response = self.wlan_policy_lib.wlanGetSavedNetworks()
        if saved_networks_response.get('error'):
            raise FuchsiaDeviceError(
                'Failed to get preexisting saved networks: %s' %
                saved_networks_response['error'])
        if saved_networks_response.get('result') != None:
            preserved_networks_and_state[
                SAVED_NETWORKS] = saved_networks_response['result']

        # Remove preexisting saved networks
        remove_networks_response = self.wlan_policy_lib.wlanRemoveAllNetworks()
        if remove_networks_response.get('error'):
            raise FuchsiaDeviceError(
                'Failed to remove preexisting saved networks: %s' %
                remove_networks_response['error'])

        # Get the currect client connection state (connections enabled or
        # disabled and enable connections by default.
        set_listener_response = self.wlan_policy_lib.wlanSetNewListener()
        if set_listener_response.get('err'):
            raise FuchsiaDeviceError('Failed to set new policy listener: %s' %
                                     set_listener_response['error'])
        update_response = self.wlan_policy_lib.wlanGetUpdate()
        update_result = update_response.get('result', {})
        if update_result.get('state'):
            preserved_networks_and_state[CLIENT_STATE] = update_result['state']
        else:
            self.log.warn('Failed to get update; test will not start or '
                          'stop client connections at the end of the test.')

        return preserved_networks_and_state

    def restore_preserved_networks_and_client_state(self, preserved_data):
        """ Restores initial saved networks and client state on device.

        Args:
            preserved_data: dict, containing
                - 'saved_networks': list, saved network configs
                - 'client_connections_state': string, client connections
                    state of device
                    ('ConnectiondsEnabled' or 'ConnectionsDisabled')

        Returns:
            True, if restore is successful, else False
        """
        remove_response = self.wlan_policy_lib.wlanRemoveAllNetworks()
        if remove_response.get('error'):
            self.log.warn(
                'Failed to remove saved networks before restore: %s' %
                remove_response['error'])
        restore_success = True
        for network in preserved_data[SAVED_NETWORKS]:
            if not self.save_network(network["ssid"], network["security_type"],
                                     network["credential_value"]):
                restore_success = False
        starting_state = preserved_data[CLIENT_STATE]
        if starting_state == CONNECTIONS_ENABLED:
            response = self.wlan_policy_lib.wlanStartClientConnections()
        elif starting_state == CONNECTIONS_DISABLED:
            response = self.wlan_policy_lib.wlanStopClientConnections()
        else:
            raise AttributeError('Invalid client state: %s' % starting_state)
        if response.get('error'):
            self.log.warn('Failed to restore client connections: %s' %
                          response['error'])
            restore_success = False
        return restore_success

    def load_config(self, config):
        pass

    def take_bug_report(self,
                        test_name,
                        begin_time,
                        additional_log_objects=None):
        """Takes a bug report on the device and stores it in a file.

        Args:
            test_name: Name of the test case that triggered this bug report.
            begin_time: Epoch time when the test started.
            additional_log_objects: A list of additional objects in Fuchsia to
                query in the bug report.  Must be in the following format:
                /hub/c/scenic.cmx/[0-9]*/out/objects
        """
        if not additional_log_objects:
            additional_log_objects = []
        log_items = []
        matching_log_items = FUCHSIA_DEFAULT_LOG_ITEMS
        for additional_log_object in additional_log_objects:
            if additional_log_object not in matching_log_items:
                matching_log_items.append(additional_log_object)
        sn_path = context.get_current_context().get_full_output_path()
        os.makedirs(sn_path, exist_ok=True)
        time_stamp = acts_logger.normalize_log_line_timestamp(
            acts_logger.epoch_to_log_line_timestamp(begin_time))
        out_name = "FuchsiaDevice%s_%s" % (
            self.serial, time_stamp.replace(" ", "_").replace(":", "-"))
        snapshot_out_name = f"{out_name}.zip"
        out_name = "%s.txt" % out_name
        full_out_path = os.path.join(sn_path, out_name)
        full_sn_out_path = os.path.join(sn_path, snapshot_out_name)
        self.log.info("Taking snapshot for %s on FuchsiaDevice%s." %
                      (test_name, self.serial))
        if self.ssh_config is not None:
            try:
                subprocess.run([
                    f"ssh -F {self.ssh_config} {self.ip} snapshot > {full_sn_out_path}"
                ],
                               shell=True)
                self.log.info("Snapshot saved at: {}".format(full_sn_out_path))
            except Exception as err:
                self.log.error("Failed to take snapshot with: {}".format(err))

        system_objects = self.send_command_ssh('iquery --find /hub').stdout
        system_objects = system_objects.split()

        for matching_log_item in matching_log_items:
            for system_object in system_objects:
                if re.match(matching_log_item, system_object):
                    log_items.append(system_object)

        log_command = '%s %s' % (FUCHSIA_DEFAULT_LOG_CMD, ' '.join(log_items))
        bug_report_data = self.send_command_ssh(log_command).stdout

        bug_report_file = open(full_out_path, 'w')
        bug_report_file.write(bug_report_data)
        bug_report_file.close()

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
            out_name = "%s.pcap" % custom_name
        else:
            out_name = "%s.pcap" % out_name
        full_out_path = os.path.join(bt_snoop_path, out_name)
        bt_snoop_data = self.send_command_ssh('bt-snoop-cli -d -f pcap').stdout
        bt_snoop_file = open(full_out_path, 'w')
        bt_snoop_file.write(bt_snoop_data)
        bt_snoop_file.close()


class FuchsiaDeviceLoggerAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        msg = "[FuchsiaDevice|%s] %s" % (self.extra["ip"], msg)
        return msg, kwargs
