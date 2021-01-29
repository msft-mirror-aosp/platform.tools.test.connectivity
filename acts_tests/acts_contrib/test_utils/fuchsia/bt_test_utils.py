#!/usr/bin/env python3
#
# Copyright (C) 2018 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import time


def le_scan_for_device_by_name(fd,
                               log,
                               search_name,
                               timeout,
                               partial_match=False):
    """Scan for and returns the first BLE advertisement with the device name.

    Args:
        fd: The Fuchsia device to start LE scanning on.
        log: The log var passed in from the test.
        search_name: The name to find.
        timeout: How long to scan for.
        partial_match: Only do a partial match for the LE advertising name.
          This will return the first result that had a partial match.

    Returns:
        The dictionary of device information.
    """
    scan_filter = {"name_substring": search_name}
    fd.gattc_lib.bleStartBleScan(scan_filter)
    end_time = time.time() + timeout
    found_device = None
    while time.time() < end_time and not found_device:
        time.sleep(1)
        scan_res = fd.gattc_lib.bleGetDiscoveredDevices()['result']
        for device in scan_res:
            name, did, connectable = device["name"], device["id"], device[
                "connectable"]
            if name == search_name or (partial_match and search_name in name):
                log.info("Successfully found advertisement! name, id: {}, {}".
                         format(name, did))
                found_device = device
    fd.gattc_lib.bleStopBleScan()
    if not found_device:
        log.error("Failed to find device with name {}.".format(search_name))
    return found_device


def bredr_scan_for_device_by_name(fd,
                                  log,
                                  search_name,
                                  timeout,
                                  partial_match=False):
    """Discover for and returns the first Classic device that matches search_name.

    Args:
        fd: The Fuchsia device to start Classic discovery on.
        log: The log var passed in from the test.
        search_name: The name to find.
        timeout: How long to scan for.
        partial_match: Only do a partial match for the search_name.
          This will return the first result that had a partial match.

    Returns:
        The dictionary of device information.
    """
    fd.bts_lib.requestDiscovery(True)

    end_time = time.time() + timeout
    found_device = None
    while time.time() < end_time and not found_device:
        scan_res = fd.bts_lib.getKnownRemoteDevices()['result']
        for device in scan_res:
            name, did = scan_res[device]["name"], scan_res[device]["id"]
            if name == search_name or (partial_match and search_name in name):
                log.info("Successfully found peer! name, id: {}, {}".format(
                    name, did))
                found_device = did
        time.sleep(1)
    fd.bts_lib.requestDiscovery(False)
    if not found_device:
        log.error("Failed to find device with name {}.".format(search_name))
        return found_device
    return found_device


def unbond_all_known_devices(fd, log):
    """Unbond all known devices from input Fuchsia Device.

    Args:
        fd: The Fuchsia device to unbond devices from.
        log: The log var passed in from the test.
    """
    fd.bts_lib.requestDiscovery(True)
    device_list = fd.bts_lib.getKnownRemoteDevices()['result']
    fd.bts_lib.requestDiscovery(False)
    for device in device_list:
        d = device_list[device]
        if d['bonded'] or d['connected']:
            log.info("Unbonding device: {}".format(d))
            log.info(fd.bts_lib.forgetDevice(d['id'])['result'])


def verify_device_state_by_name(fd, log, search_name, state, services=None):
    """Verify a connection state change happened an input device.

    Args:
        fd: The Fuchsia device to unbond devices from.
        log: The log var passed in from the test.
        search_name: The device name to find.
        state: The expected state.
        services: An optional list of services to expect based on the connected
            device.
    """
    fd.bts_lib.requestDiscovery(True)

    seconds_allowed_for_state_change = 10
    end_time = time.time() + seconds_allowed_for_state_change
    found_state = None
    while time.time() < end_time and not found_state:
        device_list = fd.bts_lib.getKnownRemoteDevices()['result']
        for device in device_list:
            d = device_list[device]
            name = d['name']
            if name == search_name:
                print(d)
                input("continue?")
                if state == "CONNECTED" and d['connected']:
                    log.info("Found connected device {}".format(d))
                    found_state = True
                    break
                if state == "BONDED" and d['bonded']:
                    log.info("Found bonded device {}".format(d))
                    found_state = True
                    break
        time.sleep(1)
    #TODO: Verify services.
    fd.bts_lib.requestDiscovery(False)
    return found_state
