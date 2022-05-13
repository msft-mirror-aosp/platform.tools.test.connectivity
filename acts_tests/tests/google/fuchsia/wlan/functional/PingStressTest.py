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
"""
Script for exercising various ping scenarios

"""

import threading

from collections import namedtuple

from acts import signals
from acts.controllers.access_point import setup_ap
from acts.controllers.ap_lib import hostapd_constants
from acts_contrib.test_utils.wifi.WifiBaseTest import WifiBaseTest
from acts_contrib.test_utils.abstract_devices.wlan_device import create_wlan_device
from acts.utils import rand_ascii_str

LOCALHOST_IP = '127.0.0.1'
GOOGLE_DNS_1_IP = '8.8.8.8'
GOOGLE_DNS_2_IP = '8.8.4.4'

PING_RESULT_TIMEOUT_SEC = 60 * 5

Test = namedtuple(
    typename='Args',
    field_names=['name', 'dest_ip', 'count', 'interval', 'timeout', 'size'],
    defaults=[3, 1000, 1000, 25])


class PingStressTest(WifiBaseTest):

    def setup_generated_tests(self):
        self.generate_tests(
            self.send_ping, lambda test_name, *_: f'test_{test_name}', [
                Test("simple_ping", GOOGLE_DNS_1_IP),
                Test("ping_local", LOCALHOST_IP),
                Test("ping_AP", lambda ap: ap.ssh_settings.hostname),
                Test("ping_with_params",
                     GOOGLE_DNS_1_IP,
                     count=5,
                     interval=800,
                     size=50),
                Test("long_ping", GOOGLE_DNS_1_IP, count=50),
                Test("medium_packet_ping", GOOGLE_DNS_1_IP, size=64),
                Test("medium_packet_long_ping",
                     GOOGLE_DNS_1_IP,
                     count=50,
                     timeout=1500,
                     size=64),
                Test("large_packet_ping", GOOGLE_DNS_1_IP, size=500),
                Test("large_packet_long_ping",
                     GOOGLE_DNS_1_IP,
                     count=50,
                     timeout=5000,
                     size=500),
            ])

    def setup_class(self):
        super().setup_class()

        self.ssid = rand_ascii_str(10)
        self.dut = create_wlan_device(self.fuchsia_devices[0])
        self.access_point = self.access_points[0]
        setup_ap(access_point=self.access_point,
                 profile_name='whirlwind',
                 channel=hostapd_constants.AP_DEFAULT_CHANNEL_2G,
                 ssid=self.ssid,
                 setup_bridge=True)
        self.dut.associate(self.ssid)

    def teardown_class(self):
        self.dut.disconnect()
        self.dut.reset_wifi()
        self.download_ap_logs()
        self.access_point.stop_all_aps()

    def send_ping(self,
                  test_name,
                  dest_ip,
                  count=3,
                  interval=1000,
                  timeout=1000,
                  size=25):
        if callable(dest_ip):
            dest_ip = dest_ip(self.access_point)

        self.log.info(f'Attempting to ping {dest_ip} for test_{test_name}...')
        ping_result = self.dut.can_ping(dest_ip, count, interval, timeout,
                                        size)
        if ping_result:
            self.log.info('Ping was successful.')
        else:
            if '8.8' in dest_ip:
                raise signals.TestFailure('Ping was unsuccessful. Consider '
                                          'possibility of server failure.')
            else:
                raise signals.TestFailure('Ping was unsuccessful.')
        return True

    def test_simultaneous_pings(self):
        ping_urls = [
            GOOGLE_DNS_1_IP,
            GOOGLE_DNS_2_IP,
            GOOGLE_DNS_1_IP,
            GOOGLE_DNS_2_IP,
        ]
        ping_threads = []
        ping_results = []

        def ping_thread(self, dest_ip, ping_results):
            self.log.info('Attempting to ping %s...' % dest_ip)
            ping_result = self.dut.can_ping(dest_ip, count=10, size=50)
            if ping_result:
                self.log.info('Success pinging: %s' % dest_ip)
            else:
                self.log.info('Failure pinging: %s' % dest_ip)
            ping_results.append(ping_result)

        try:
            # Start multiple ping at the same time
            for index, url in enumerate(ping_urls):
                self.log.info('Create and start thread %d.' % index)
                t = threading.Thread(target=ping_thread,
                                     args=(self, url, ping_results))
                ping_threads.append(t)
                t.start()

            # Wait for all threads to complete or timeout
            for t in ping_threads:
                t.join(PING_RESULT_TIMEOUT_SEC)

        finally:
            is_alive = False

            for index, t in enumerate(ping_threads):
                if t.is_alive():
                    t = None
                    is_alive = True

            if is_alive:
                raise signals.TestFailure('Thread %d timedout' % index)

        for index in range(0, len(ping_results)):
            if not ping_results[index]:
                self.log.info("Ping failed for %d" % index)
                raise signals.TestFailure('Thread %d failed to ping. '
                                          'Consider possibility of server '
                                          'failure' % index)
        return True
