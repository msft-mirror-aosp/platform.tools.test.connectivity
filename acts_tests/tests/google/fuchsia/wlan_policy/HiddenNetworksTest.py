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
from acts import signals
from acts.controllers.ap_lib import hostapd_constants
from acts.controllers.ap_lib import hostapd_security
from acts_contrib.test_utils.abstract_devices.utils_lib.wlan_utils import setup_ap
from acts_contrib.test_utils.abstract_devices.utils_lib.wlan_policy_utils import reboot_device, restore_state, save_network, setup_policy_tests
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest
from acts.utils import rand_ascii_str
import time

# These tests should have a longer timeout for connecting than normal connect
# tests because the device should probabilistically perform active scans for
# hidden networks. Multiple scans are necessary to verify a very low chance of
# random failure.
TIME_WAIT_FOR_CONNECT = 45
TIME_ATTEMPT_SCANS = 60

CONNECTIONS_ENABLED = "ConnectionsEnabled"
CONNECTIONS_DISABLED = "ConnectionsDisabled"
SECURITY_NONE = "none"
WPA2 = "wpa2"


class HiddenNetworksTest(WifiBaseTest):
    """ Tests that WLAN Policy will detect hidden networks

    Test Bed Requirement:
    * One or more Fuchsia devices
    * One Access Point
    """
    def setup_class(self):
        super().setup_class()
        # Start an AP with a hidden network
        self.hidden_ssid = rand_ascii_str(hostapd_constants.AP_SSID_LENGTH_2G)
        self.access_point = self.access_points[0]
        self.hidden_password = rand_ascii_str(
            hostapd_constants.AP_PASSPHRASE_LENGTH_2G)
        self.hidden_security = WPA2
        security = hostapd_security.Security(
            security_mode=self.hidden_security, password=self.hidden_password)

        self.access_point.stop_all_aps()
        setup_ap(self.access_point,
                 'whirlwind',
                 hostapd_constants.AP_DEFAULT_CHANNEL_5G,
                 self.hidden_ssid,
                 hidden=True,
                 security=security)

        if len(self.fuchsia_devices) < 1:
            raise EnvironmentError("No Fuchsia devices found.")
        # Save the existing saved networks before we remove them for tests
        # And remember whether client connections have started
        self.preexisting_state = setup_policy_tests(self.fuchsia_devices)

    def setup_test(self):
        for fd in self.fuchsia_devices:
            # Set new update listener so that the next test can always get the
            # most recent udpdate immediately.
            new_listener_result = fd.wlan_policy_lib.wlanSetNewListener()
            if new_listener_result["error"] != None:
                self.log.warn(
                    "Error occurred initializing a new update listener for the facade, may"
                    "cause errors in updates for tests: %s" %
                    new_listener_result["error"])

            resultRemove = fd.wlan_policy_lib.wlanRemoveAllNetworks()
            if resultRemove["error"] != None:
                self.log.error(
                    "Error occurred when deleting all saved networks in test setup: %s"
                    % resultRemove["error"])
                raise EnvironmentError(
                    "Failed to remove all networks in setup")

            resultStart = fd.wlan_policy_lib.wlanStartClientConnections()
            if resultStart["error"] != None:
                self.log.error(
                    "Error occurred when starting client connections in test setup: %s"
                    % resultStart["error"])
                raise EnvironmentError(
                    "Failed to start client connections in setup")

    def teardown_class(self):
        self.access_point.stop_all_aps()
        for fd in self.fuchsia_devices:
            # Put back the networks that were saved before tests began.
            restore_state(self.fuchsia_devices, self.preexisting_state)

    def test_scan_hidden_networks(self):
        # Scan a few times and check that we see the hidden networks in the
        # results at least once. Even if hidden networks are scanned
        # probabilistically, we should see it after a few tries.
        for fd in self.fuchsia_devices:
            # A hidden network must be saved to be found in scan results.
            # Stop client connections to not trigger a connect when saving,
            # which would interfere with requested scans.
            fd.wlan_policy_lib.wlanStopClientConnections()
            if not save_network(fd, self.hidden_ssid, self.hidden_security,
                                self.hidden_password):
                raise EnvironmentError("Failed to save network")
            fd.wlan_policy_lib.wlanStartClientConnections()
            start_time = time.time()
            num_performed_scans = 0

            while time.time() < start_time + TIME_ATTEMPT_SCANS:
                num_performed_scans = num_performed_scans + 1
                scan_result = fd.wlan_policy_lib.wlanScanForNetworks()
                if scan_result["error"] != None:
                    self.log.error(
                        "Failed to scan for networks with error %s" %
                        scan_result["error"])
                    raise EnvironmentError("Failed to scan")
                else:
                    scans = scan_result["result"]
                if self.hidden_ssid in scans:
                    self.log.info(
                        "SSID of hidden network seen after %d scans" %
                        num_performed_scans)
                    return
                # Don't overload SL4F with scan requests
                time.sleep(1)

            self.log.error("Failed to see SSID after %d scans" %
                           num_performed_scans)
            raise signals.TestFailure("Failed to see hidden network in scans")

    def test_auto_connect_hidden_on_startup(self):
        """ Test that if we are not connected to anything but have a hidden
            network saved, we will eventually actively scan for it and connect."""
        # Start up AP with an open network with a random SSID

        for fd in self.fuchsia_devices:
            # Test that we will auto connect without anything being triggered by
            # saving a new network.
            fd.wlan_policy_lib.wlanStopClientConnections()

            # Save the network.
            if not save_network(fd, self.hidden_ssid, self.hidden_security,
                                self.hidden_password):
                raise EnvironmentError("Failed to save network")

            # Reboot the device and check that it auto connects.
            reboot_device(fd)
            if not fd.wait_for_connect(self.hidden_ssid,
                                       self.hidden_security,
                                       timeout=TIME_WAIT_FOR_CONNECT):
                raise signals.TestFailure("Failed to connect to network")

    def test_auto_connect_hidden_on_save(self):
        """ Test that if we save a hidden network and are not connected to
            anything, the device will connect to the hidden network that was
            just saved. """
        for fd in self.fuchsia_devices:
            if not fd.wait_for_no_connections():
                self.log.info(
                    "Failed to get into a disconnected state to start the test"
                )
                raise EnvironmentError("Failed to disconnect all")

            # Save the network and make sure that we see the device auto connect to it.
            if not save_network(fd, self.hidden_ssid, self.hidden_security,
                                self.hidden_password):
                raise EnvironmentError("Failed to save network")

            if not fd.wait_for_connect(self.hidden_ssid,
                                       self.hidden_security,
                                       timeout=TIME_WAIT_FOR_CONNECT):
                raise signals.TestFailure("Failed to connect to network")
