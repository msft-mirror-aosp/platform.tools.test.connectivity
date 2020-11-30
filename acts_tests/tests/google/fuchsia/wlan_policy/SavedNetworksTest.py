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
"""
A test that saves various networks and verifies the behavior of save, get, and
remove through the ClientController API of WLAN policy.
"""

from acts import signals
from acts.controllers.ap_lib import hostapd_ap_preset
from acts.controllers.ap_lib import hostapd_constants
from acts.controllers.ap_lib import hostapd_security
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest
from acts_contrib.test_utils.abstract_devices.utils_lib.wlan_utils import setup_ap
from acts_contrib.test_utils.abstract_devices.utils_lib.wlan_policy_utils import reboot_device, restore_state, save_network, setup_policy_tests
from acts.utils import rand_ascii_str, rand_hex_str, timeout
import requests
import time
import types

PSK_LEN = 64
TIME_WAIT_FOR_DISCONNECT = 30
TIME_WAIT_FOR_CONNECT = 30

STATE_CONNECTED = "Connected"
STATE_CONNECTING = "Connecting"
CONNECTIONS_ENABLED = "ConnectionsEnabled"
CONNECTIONS_DISABLED = "ConnectionsDisabled"
SECURITY_NONE = "none"
WEP = "wep"
WPA = "wpa"
WPA2 = "wpa2"
WPA3 = "wpa3"
CREDENTIAL_TYPE_NONE = "none"
PASSWORD = "password"
PSK = "psk"
CREDENTIAL_VALUE_NONE = ""


class SavedNetworksTest(WifiBaseTest):
    """WLAN policy commands test class.

    Test Bed Requirement:
    * One or more Fuchsia devices
    * One Access Point
    """
    def setup_class(self):
        super().setup_class()
        # Keep track of whether we have started an access point in a test
        if len(self.fuchsia_devices) < 1:
            raise EnvironmentError("No Fuchsia devices found.")
        # Save the existing saved networks before we remove them for tests
        # And remember whether client connections have started
        self.preserved_state = setup_policy_tests(self.fuchsia_devices)
        self.preexisting_client_connections_state = {}
        for fd in self.fuchsia_devices:
            fd.wlan_policy_lib.wlanSetNewListener()
            result_update = fd.wlan_policy_lib.wlanGetUpdate()
            if result_update.get("result") != None and result_update.get(
                    "result").get("state") != None:
                self.preexisting_client_connections_state[
                    fd] = result_update.get("result").get("state")
            else:
                self.log.warn(
                    "Failed to get update; test will not start or "
                    "stop client connections at the end of the test.")
            fd.wlan_policy_lib.wlanStartClientConnections()

    def setup_test(self):
        for fd in self.fuchsia_devices:
            # Set new update listener so that the next test can always get the
            # most recent udpdate immediately.
            new_listener_result = fd.wlan_policy_lib.wlanSetNewListener()
            if new_listener_result.get("error") != None:
                self.log.warn(
                    "Error occurred initializing a new update listener for the facade, may"
                    "cause errors in updates for tests: %s" %
                    new_listener_result["error"])

            resultRemove = fd.wlan_policy_lib.wlanRemoveAllNetworks()
            if resultRemove.get("error") != None:
                self.log.error(
                    "Error occurred when deleting all saved networks in test setup: %s"
                    % resultRemove["error"])
                raise EnvironmentError(
                    "Failed to remove all networks in setup")
        self.access_points[0].stop_all_aps()

    def teardown_class(self):
        for fd in self.fuchsia_devices:
            # Start/stop client connections based on state before tests began.
            if fd in self.preexisting_client_connections_state:
                starting_state = self.preexisting_client_connections_state[fd]
                if starting_state == CONNECTIONS_ENABLED:
                    fd.wlan_policy_lib.wlanStartClientConnections()
                elif starting_state == CONNECTIONS_DISABLED:
                    fd.wlan_policy_lib.wlanStopClientConnections()
                else:
                    self.log.info(
                        "Unrecognized client connections starting state: %s" %
                        starting_state)
            # Remove any networks remaining from tests
            fd.wlan_policy_lib.wlanRemoveAllNetworks()
        # Put back the networks that were saved before tests began.
        restore_state(self.fuchsia_devices, self.preserved_state)
        self.access_points[0].stop_all_aps()

    def get_saved_networks(self, fd):
        """ Get the saved networks or fail the test if there is an error getting the networks
        Args:
            fd: the Fuchsia device to get saved networks from
        """
        result_get = fd.wlan_policy_lib.wlanGetSavedNetworks()
        if result_get.get("error") != None:
            self.log.info("Failed to get saved networks with error: %s" %
                          result_get["error"])
            raise signals.TestFailure('Failed to get saved networks')
        return result_get["result"]

    def save_bad_network(self, fd, ssid, security_type, password=""):
        """ Saves a network as specified on the given device and verify that we
        Args:
            fd: The Fuchsia device to save the network on
            ssid: The SSID or name of the network to save.
            security_type: The security type to save the network as, ie "none",
                        "wep", "wpa", "wpa2", or "wpa3"
            password: The password to save for the network. Empty string represents
                    no password, and PSK should be provided as 64 character hex string.
        """
        result_save = fd.wlan_policy_lib.wlanSaveNetwork(
            ssid, security_type, password)
        if result_save.get("error") == None:
            self.log.info(
                "Attempting to save bad network config %s did not give an error"
                % ssid)
            raise signals.TestFailure("Failed to get error saving bad network")

    def check_get_saved_network(self, fd, ssid, security_type, credential_type,
                                credential_value):
        """ Verify that get saved networks sees the single specified network. Used
            for the tests that save and get a single network. Maps security types of
            expected and actual to be case insensitive.
        Args:
            fd: Fuchsia device to run on.
            ssid: The name of the network to check for.
            security_type: The security of the network, ie "none", "wep", "wpa",
                        "wpa2", or "wpa3".
            credential_type: The type of credential saved for the network, ie
                            "none", "password", or "psk".
            credential_value: The actual credential, or "" if there is no credential.
        """
        expected_networks = [{
            "ssid": ssid,
            "security_type": security_type,
            "credential_type": credential_type,
            "credential_value": credential_value
        }]
        self.check_saved_networks(fd, expected_networks)

    def check_saved_networks(self, fd, expected_networks):
        """ Verify that the saved networks we get from the device match the provided
            list of networks.
        Args:
            fd: The Fuchsia device to run on.
            expected_networks: The list of networks we expect to get from the device,
                            unordered and in the same format as we would get:
                            [{"credential_type": _, "credential_value": _,
                            "security_type": _, "ssid": _}, ...] There should be
                            no duplicates in expected networks.
        """
        actual_networks = list(
            map(self.lower_case_network, self.get_saved_networks(fd)))
        expected_networks = list(
            map(self.lower_case_network, self.get_saved_networks(fd)))

        if len(actual_networks) != len(expected_networks):
            self.log.info(
                "Number of expected saved networks does not match the actual number."
                "Expected: %d, actual: %d" %
                (len(actual_networks), len(expected_networks)))
            raise signals.TestFailure(
                "Failed to get the expected number of saved networks")
        for network in actual_networks:
            if network not in expected_networks:
                self.log.info(
                    "Actual and expected networks do not match. Actual: %s,\n"
                    "Expected: %s" % (actual_networks, expected_networks))
                raise signals.TestFailure("Got an unexpected saved network")

    def lower_case_network(self, network):
        if "security_type" not in network:
            self.log.error("Missing security type in network %s" % network)
            raise signals.TestFailure("Network is missing security type")
        if "credential_type" not in network:
            self.log.error("Missing credential type in network %s" % network)
            raise signals.TestFailure("Network is missing credential type")
        {"ssid": network["ssid"], "security_type": network["security_type"]}

    def remove_network(self, fd, ssid, security_type, password=""):
        """ Remove the given network on the device and check that it was
            successfully removed.
        Args:
            fd: The Fuchsia device to run on.
            ssid: The name of the network to remove.
            security_type: The network's security, ie "none", "wep", "wpa", "wpa2",
                        or "wpa3"
            password: The password of the network to remove, or "" if none.
        """
        # Expected networks are the networks on the device before remove, minus
        # the removed network.
        expected_networks = self.get_saved_networks(fd)
        expected_networks.remove(ssid)
        expected_networks.sort()
        result_remove = fd.wlan_policy_lib.wlanRemoveNetwork(
            ssid, security_type, password)
        if result_remove.get("error") != None:
            self.log.info("Failed to remove network with error: %s",
                          result_remove["error"])
            raise signals.TestFailure("Failed to remove saved network")

        saved_networks = get_saved_networks(fd)
        saved_networks.sort()
        if expected_networks != saved_networks:
            self.log.info(
                "Failed to remove network %s. Actual networks: %s, expected"
                " networks"
                ": %s" % (ssid, saved_networks, expected_networks))
            raise signals.TestFailure("Failed to remove network")

    def save_and_check_network(self, ssid, security_type, password=""):
        """ Perform a test for saving, getting, and removing a single network on each
            device.
        Args:
            ssid: The network name to use.
            security_type: The security of the network as a string, ie "none",
                        "wep", "wpa", "wpa2", or "wpa3" (case insensitive)
            password: The password of the network. PSK should be given as 64
                    hexadecimal characters and none should be an empty string.
        """
        for fd in self.fuchsia_devices:
            if not save_network(fd, ssid, security_type, password):
                raise signals.TestFailure("Failed to save network")
            self.check_get_saved_network(fd, ssid, security_type,
                                         self.credentialType(password),
                                         password)

    def start_ap(self, ssid, security_type, password=None, hidden=False):
        """ Starts an access point.
        Args:
            ssid: the SSID of the network to broadcast
            security_type: the security type of the network to be broadcasted. This can be
                None, "wep" "wpa", "wpa2", or "wpa3" (or from hostapd_constants.py)
            password: the password to connect to the broadcasted network. The password is ignored
                if security type is none.
        """
        # Put together the security configuration of the network to be
        # broadcasted. Open networks are represented by no security.
        if security_type == None or security_type.upper() == SECURITY_NONE:
            security = None
        else:
            security = hostapd_security.Security(security_mode=security_type,
                                                 password=password)

        if len(self.access_points) > 0:
            # Create an AP with default values other than the specified values.
            setup_ap(self.access_points[0],
                     'whirlwind',
                     hostapd_constants.AP_DEFAULT_CHANNEL_5G,
                     ssid,
                     security=security)

        else:
            self.log.error(
                "No access point available for test, please check config")
            raise EnvironmentError("Failed to set up AP for test")

    def credentialType(self, credentialValue):
        """ Returns the type of the credential to compare against values reported """
        if len(credentialValue) == PSK_LEN:
            return PSK
        elif len(credentialValue) == 0:
            return "none"
        else:
            return PASSWORD

    def same_network_identifier(self, net_id, ssid, security_type):
        """ Returns true if the network id is made of the given ssid and security
            type, and false otherwise. Security type check is case insensitive.
        """
        return net_id["ssid"] == ssid and net_id["type_"].upper(
        ) == security_type.upper()

    def wait_for_no_connections(self, fd):
        """ Waits to see that there are no existing connections the device. This is
            to ensure a good starting point for tests that look for a connection.
        Args:
            fd: The fuchsia device to run on.
        """
        start_time = time.time()
        while True:
            time_left = TIME_WAIT_FOR_DISCONNECT - (time.time() - start_time)
            if time_left <= 0:
                raise signals.TestFailure("Time out")
            try:
                update = fd.wlan_policy_lib.wlanGetUpdate(timeout=time_left)
            except requests.exceptions.Timeout:
                raise signals.TestFailure(
                    "Timed out getting status update while waiting for all"
                    " connections to end.")
            if update.get("error") != None:
                raise signals.TestFailure("Failed to get status update")
            # If any network is connected or being connected to, wait for them
            # to disconnect.
            has_connection = False
            for network in update["result"]["networks"]:
                if network['state'].upper() in [
                        STATE_CONNECTED.upper(),
                        STATE_CONNECTING.upper()
                ]:
                    has_connection = True
                    break
            if not has_connection:
                break

    """Tests"""

    def test_open_network_with_password(self):
        for fd in self.fuchsia_devices:
            # Save an open network with a password and verify that it fails to
            # save.
            self.save_bad_network(fd, rand_ascii_str(10), SECURITY_NONE,
                                  rand_ascii_str(8))
            self.check_saved_networks(fd, {})

    def test_open_network(self):
        ssid = rand_ascii_str(10)
        self.save_and_check_network(ssid, SECURITY_NONE)

    def test_network_with_psk(self):
        ssid = rand_ascii_str(11)
        # PSK are translated from hex to bytes when saved, and when returned
        # by get_saved_networks it will be lower case.
        psk = rand_hex_str(PSK_LEN).lower()
        self.save_and_check_network(ssid, WPA2, psk)

    def test_wep_network(self):
        ssid = rand_ascii_str(12)
        password = rand_ascii_str(13)
        self.save_and_check_network(ssid, WEP, password)

    def test_wpa2_network(self):
        ssid = rand_ascii_str(9)
        password = rand_ascii_str(15)
        self.save_and_check_network(ssid, WPA2, password)

    def test_wpa_network(self):
        ssid = rand_ascii_str(16)
        password = rand_ascii_str(9)
        self.save_and_check_network(ssid, WPA, password)

    def test_wpa3_network(self):
        ssid = rand_ascii_str(9)
        password = rand_ascii_str(15)
        self.save_and_check_network(ssid, WPA3, password)

    def test_save_network_persists(self):
        ssid = rand_ascii_str(10)
        security = WPA2
        password = rand_ascii_str(10)
        for fd in self.fuchsia_devices:
            if not save_network(fd, ssid, security, password):
                raise signals.TestFailure("Failed to save network")
            # Reboot the device. The network should be persistently saved
            # before the command is completed.
            reboot_device(fd)
            self.check_get_saved_network(fd, ssid, security, PASSWORD,
                                         password)

    def test_same_ssid_diff_security(self):
        for fd in self.fuchsia_devices:
            saved_networks = self.get_saved_networks(fd)
            ssid = rand_ascii_str(19)
            password = rand_ascii_str(12)
            if not save_network(fd, ssid, WPA2, password):
                raise signals.TestFailure("Failed to save network")
            saved_networks.append({
                "ssid": ssid,
                "security_type": WPA2,
                "credential_type": PASSWORD,
                "credential_value": password
            })
            if not save_network(fd, ssid, SECURITY_NONE):
                raise signals.TestFailure("Failed to save network")
            saved_networks.append({
                "ssid": ssid,
                "security_type": SECURITY_NONE,
                "credential_type": CREDENTIAL_TYPE_NONE,
                "credential_value": CREDENTIAL_VALUE_NONE
            })
            actual_networks = self.get_saved_networks(fd)
            # Both should be saved and present in network store since the have
            # different security types and therefore different network identifiers.
            self.check_saved_networks(fd, saved_networks)

    def test_remove_disconnects(self):
        # If we save, connect to, then remove the network while still connected
        # to it, we expect the network will disconnect. This test requires a
        # wpa2 network in the test config. Remove all other networks first so
        # that we can't auto connect to them
        ssid = rand_ascii_str(10)
        security = WPA2
        password = rand_ascii_str(10)
        self.start_ap(ssid, security, password)

        for fd in self.fuchsia_devices:
            self.wait_for_no_connections(fd)

            result_save = fd.wlan_policy_lib.wlanSaveNetwork(
                ssid, security, password)
            if result_save.get("error") != None:
                raise signals.TestFailure(
                    "Error occurred attempting to save network: %s" %
                    result_save["error"])
            # If we fail to send connect command, proceed with test anyway
            # because saving the network should trigger a connect
            result_connect = fd.wlan_policy_lib.wlanConnect(ssid, security)
            if result_connect.get("error") != None:
                self.log.info(
                    "Error occurred while attempting to send connect call: %s. "
                    "This test will rely on autoconnect." %
                    result_connect["error"])
            if not fd.wait_for_connect(
                    ssid, security, timeout=TIME_WAIT_FOR_CONNECT):
                raise signals.TestFailure("Failed to connect to network")

            result_remove = fd.wlan_policy_lib.wlanRemoveNetwork(
                ssid, security, password)
            if result_remove.get("error") != None:
                raise signals.TestFailure(
                    "Error occurred attempting to remove network")
            if not fd.wait_for_disconnect(ssid,
                                          security,
                                          "Disconnected",
                                          "ConnectionStopped",
                                          timeout=TIME_WAIT_FOR_DISCONNECT):
                raise signals.TestFailure(
                    "Failed to disconnect from removed network")

    def test_auto_connect_open(self):
        # Start up AP with an open network with a random SSID
        ssid = rand_ascii_str(10)
        self.start_ap(ssid, None)
        for fd in self.fuchsia_devices:
            self.wait_for_no_connections(fd)

            # Save the network and make sure that we see the device auto connect to it.
            security = SECURITY_NONE
            password = CREDENTIAL_VALUE_NONE
            result_save = fd.wlan_policy_lib.wlanSaveNetwork(
                ssid, security, password)
            if result_save.get("error") != None:
                raise signals.TestFailure("Failed to save network")
            if not fd.wait_for_connect(
                    ssid, security, timeout=TIME_WAIT_FOR_CONNECT):
                raise signals.TestFailure("Failed to connect to network")

    def test_auto_connect_wpa3(self):
        # Start up AP with an open network with a random SSID
        ssid = rand_ascii_str(10)
        security = WPA3
        password = rand_ascii_str(10)
        self.start_ap(ssid, security, password)
        for fd in self.fuchsia_devices:
            self.wait_for_no_connections(fd)

            # Save the network and make sure that we see the device auto connect to it.
            result_save = fd.wlan_policy_lib.wlanSaveNetwork(
                ssid, security, password)
            if result_save.get("error") != None:
                raise signals.TestFailure("Failed to save network")
            if not fd.wait_for_connect(
                    ssid, security, timeout=TIME_WAIT_FOR_CONNECT):
                raise signals.TestFailure("Failed to connect to network")
