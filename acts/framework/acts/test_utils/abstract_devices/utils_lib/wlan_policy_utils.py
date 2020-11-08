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

SAVED_NETWORKS = "saved_networks"
CLIENT_STATE = "client_connections_state"
CONNECTIONS_ENABLED = "ConnectionsEnabled"
CONNECTIONS_DISABLED = "ConnectionsDisabled"


def setup_policy_tests(fuchsia_devices):
    """ Preserves networks already saved on devices before removing them to
        setup up for a clean test environment. Records the state of client
        connections before tests. Initializes the client controller
        and enables connections.
    Args:
        fuchsia_devices: the devices under test
    Returns:
        A dict of the data to restore after tests indexed by device. The data
        for each device is a dict of the saved data, ie saved networks and
        state of client connections.
    """
    preserved_data_by_device = {}
    for fd in fuchsia_devices:
        data = {}
        # Collect and delete networks saved on the device.
        fd.wlan_policy_lib.wlanCreateClientController()
        result_get = fd.wlan_policy_lib.wlanGetSavedNetworks()
        if result_get.get("result") != None:
            data[SAVED_NETWORKS] = result_get['result']
        fd.wlan_policy_lib.wlanRemoveAllNetworks()

        # Get the currect client connection state (connections enabled or disabled)
        # and enable connections by default.
        fd.wlan_policy_lib.wlanSetNewListener()
        result_update = fd.wlan_policy_lib.wlanGetUpdate()
        if result_update.get("result") != None and result_update.get(
                "result").get("state") != None:
            data[CLIENT_STATE] = result_update.get("result").get("state")
        else:
            fd.log.warn("Failed to get update; test will not start or "
                        "stop client connections at the end of the test.")
        fd.wlan_policy_lib.wlanStartClientConnections()

        preserved_data_by_device[fd] = data
    return preserved_data_by_device


def restore_state(fuchsia_devices, preserved_data):
    """ Restore the state of the test device to what it was before tests began.
        Remove any remaining saved networks, and restore the saved networks and
        client connections state recorded by setup_policy_tests
    Args:
        fuchsia_devices: The fuchsia devices under test
        preserved data: Dict of data indexed by fuchsia device, as returned
                        by setup_policy_tests
    """
    for fd in fuchsia_devices:
        data = preserved_data[fd]
        fd.wlan_policy_lib.wlanRemoveAllNetworks()
        for network in data[SAVED_NETWORKS]:
            save_network(fd, network["ssid"], network["security_type"],
                         network["credential_value"])
        for starting_state in data[CLIENT_STATE]:
            if starting_state == CONNECTIONS_ENABLED:
                fd.wlan_policy_lib.wlanStartClientConnections()
            elif starting_state == CONNECTIONS_DISABLED:
                fd.wlan_policy_lib.wlanStopClientConnections()


def save_network(fd, ssid, security_type, password=""):
    """ Saves a network as specified on the given device and verify that the operation succeeded.
        Returns true if there was no error, and false otherwise
    Args:
        fd: The Fuchsia device to save the network on
        ssid: The SSID or name of the network to save.
        security_type: The security type to save the network as, ie "none",
                    "wep", "wpa", "wpa2", or "wpa3"
        password: The password to save for the network. Empty string represents
                no password, and PSK should be provided as 64 character hex string.
    """
    result_save = fd.wlan_policy_lib.wlanSaveNetwork(ssid, security_type,
                                                     password)
    if result_save.get("error") != None:
        fd.log.info("Failed to save network %s with error: %s" %
                    (ssid, result_save["error"]))
        return False
    else:
        return True


def start_connections(fd):
    """ Starts client connections on the specified device and verifies that it
        succeeds, and raises a test failure if not.
    Returns:
        True if there are no errors, False if there are errors.
    """
    resultStart = fd.wlan_policy_lib.wlanStartClientConnections()
    if resultStart.get("error") != None:
        fd.log.error(
            "Error occurred when starting client connections in test setup: %s"
            % resultStart.get("error"))
        return False
    else:
        return True


def stop_connections(fd):
    """ Stops client connections on the device and verify that there are no
        errors are returned, and raises a test failure if there are.
    Returns:
        True if there are noe errors, False otherwise.
    """
    result_stop = fd.wlan_policy_lib.wlanStopClientConnections()
    if result_stop.get("error") != None:
        fd.log.error("Error occurred stopping client connections: %s" %
                     result_stop.get("error"))
        return False
    else:
        return True


def reboot_device(fd):
    """ Reboot the device and reinitialize the device after.
    Args:
        fd: The device to reboot.
    """
    fd.reboot()
    fd.wlan_policy_lib.wlanCreateClientController()
    fd.wlan_policy_lib.wlanStartClientConnections()
    fd.wlan_policy_lib.wlanSetNewListener()
