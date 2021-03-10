#!/usr/bin/env python3.4
#
#   Copyright 2021 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import collections
import hashlib
import logging
import math
import re
import statistics
import time

SHORT_SLEEP = 1
MED_SLEEP = 6
#TEST_TIMEOUT = 10
#STATION_DUMP = 'iw wlan0 station dump'
#SCAN = 'wpa_cli scan'
#SCAN_RESULTS = 'wpa_cli scan_results'
#SIGNAL_POLL = 'wpa_cli signal_poll'
#WPA_CLI_STATUS = 'wpa_cli status'
DISCONNECTION_MESSAGE_BRCM = 'driver adapter not found'
#CONST_3dB = 3.01029995664
RSSI_ERROR_VAL = float('nan')

#RTT_REGEX = re.compile(r'^\[(?P<timestamp>\S+)\] .*? time=(?P<rtt>\S+)')
#LOSS_REGEX = re.compile(r'(?P<loss>\S+)% packet loss')
#FW_REGEX = re.compile(r'FW:(?P<firmware>\S+) HW:')
#CHANNELS_6GHz = ['6g{}'.format(4 * x + 1) for x in range(59)]
#BAND_TO_CHANNEL_MAP = {
#    '2.4GHz': list(range(1, 14)),
#    'UNII-1': [36, 40, 44, 48],
#    'UNII-2':
#    [52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124, 128, 132, 140],
#    'UNII-3': [149, 153, 157, 161, 165],
#    '6GHz': CHANNELS_6GHz
#}
#CHANNEL_TO_BAND_MAP = {
#    channel: band
#    for band, channels in BAND_TO_CHANNEL_MAP.items() for channel in channels
#}


# Rssi Utilities
def empty_rssi_result():
    return collections.OrderedDict([('data', []), ('mean', None),
                                    ('stdev', None)])


def get_connected_rssi(dut,
                       num_measurements=1,
                       polling_frequency=SHORT_SLEEP,
                       first_measurement_delay=0,
                       disconnect_warning=True,
                       ignore_samples=0,
                       interface=None):
    # yapf: disable
    connected_rssi = collections.OrderedDict(
        [('time_stamp', []),
         ('bssid', []), ('ssid', []), ('frequency', []),
         ('signal_poll_rssi', empty_rssi_result()),
         ('signal_poll_avg_rssi', empty_rssi_result()),
         ('chain_0_rssi', empty_rssi_result()),
         ('chain_1_rssi', empty_rssi_result())])

    # yapf: enable
    previous_bssid = 'disconnected'
    t0 = time.time()
    time.sleep(first_measurement_delay)
    for idx in range(num_measurements):
        measurement_start_time = time.time()
        connected_rssi['time_stamp'].append(measurement_start_time - t0)
        # Get signal poll RSSI
        status_output = dut.adb.shell('wl assoc')
        match = re.search('BSSID:.*', status_output)

        if match:
            current_bssid = match.group(0).split('\t')[0]
            current_bssid = current_bssid.split(' ')[1]
            connected_rssi['bssid'].append(current_bssid)

        else:
            current_bssid = 'disconnected'
            connected_rssi['bssid'].append(current_bssid)
            if disconnect_warning and previous_bssid != 'disconnected':
                logging.warning('WIFI DISCONNECT DETECTED!')

        previous_bssid = current_bssid
        match = re.search('SSID:.*', status_output)
        if match:
            ssid = match.group(0).split(': ')[1]
            connected_rssi['ssid'].append(ssid)
        else:
            connected_rssi['ssid'].append('disconnected')

        #TODO: SEARCH MAP ; PICK CENTER CHANNEL
        match = re.search('Primary channel:.*', status_output)
        if match:
            frequency = int(match.group(0).split(':')[1])
            connected_rssi['frequency'].append(frequency)
        else:
            connected_rssi['frequency'].append(RSSI_ERROR_VAL)

        try:
            per_chain_rssi = dut.adb.shell('wl phy_rssi_ant')
            per_chain_rssi = per_chain_rssi.split(' ')
            chain_0_rssi = int(per_chain_rssi[1])
            chain_1_rssi = int(per_chain_rssi[4])
        except:
            chain_0_rssi = RSSI_ERROR_VAL
            chain_1_rssi = RSSI_ERROR_VAL
        connected_rssi['chain_0_rssi']['data'].append(chain_0_rssi)
        connected_rssi['chain_1_rssi']['data'].append(chain_1_rssi)
        combined_rssi = math.pow(10, chain_0_rssi / 10) + math.pow(
            10, chain_1_rssi / 10)
        combined_rssi = 10 * math.log10(combined_rssi)
        connected_rssi['signal_poll_rssi']['data'].append(combined_rssi)
        connected_rssi['signal_poll_avg_rssi']['data'].append(combined_rssi)
        measurement_elapsed_time = time.time() - measurement_start_time
        time.sleep(max(0, polling_frequency - measurement_elapsed_time))

    # Statistics, Statistics
    for key, val in connected_rssi.copy().items():
        if 'data' not in val:
            continue
        filtered_rssi_values = [x for x in val['data'] if not math.isnan(x)]
        if len(filtered_rssi_values) > ignore_samples:
            filtered_rssi_values = filtered_rssi_values[ignore_samples:]
        if filtered_rssi_values:
            connected_rssi[key]['mean'] = statistics.mean(filtered_rssi_values)
            if len(filtered_rssi_values) > 1:
                connected_rssi[key]['stdev'] = statistics.stdev(
                    filtered_rssi_values)
            else:
                connected_rssi[key]['stdev'] = 0
        else:
            connected_rssi[key]['mean'] = RSSI_ERROR_VAL
            connected_rssi[key]['stdev'] = RSSI_ERROR_VAL

    return connected_rssi


def get_scan_rssi(dut, tracked_bssids, num_measurements=1):
    scan_rssi = collections.OrderedDict()
    for bssid in tracked_bssids:
        scan_rssi[bssid] = empty_rssi_result()
    for idx in range(num_measurements):
        scan_output = dut.adb.shell('cmd wifi start-scan')
        time.sleep(MED_SLEEP)
        scan_output = dut.adb.shell('cmd wifi list-scan-results')
        for bssid in tracked_bssids:
            bssid_result = re.search(bssid + '.*',
                                     scan_output,
                                     flags=re.IGNORECASE)
            if bssid_result:
                bssid_result = bssid_result.group(0).split()
                print(bssid_result)
                scan_rssi[bssid]['data'].append(int(bssid_result[2]))
            else:
                scan_rssi[bssid]['data'].append(RSSI_ERROR_VAL)
    # Compute mean RSSIs. Only average valid readings.
    # Output RSSI_ERROR_VAL if no readings found.
    for key, val in scan_rssi.items():
        filtered_rssi_values = [x for x in val['data'] if not math.isnan(x)]
        if filtered_rssi_values:
            scan_rssi[key]['mean'] = statistics.mean(filtered_rssi_values)
            if len(filtered_rssi_values) > 1:
                scan_rssi[key]['stdev'] = statistics.stdev(
                    filtered_rssi_values)
            else:
                scan_rssi[key]['stdev'] = 0
        else:
            scan_rssi[key]['mean'] = RSSI_ERROR_VAL
            scan_rssi[key]['stdev'] = RSSI_ERROR_VAL
    return scan_rssi


def get_sw_signature(dut):
    bdf_output = dut.adb.shell('cksum /vendor/firmware/bcmdhd*')
    logging.debug('BDF Checksum output: {}'.format(bdf_output))
    bdf_signature = sum(
        [int(line.split(' ')[0]) for line in bdf_output.splitlines()]) % 1000

    fw_version = dut.adb.shell('getprop vendor.wlan.firmware.version')
    driver_version = dut.adb.shell('getprop vendor.wlan.driver.version')
    logging.debug('Firmware version : {}. Driver version: {}'.format(
        fw_version, driver_version))
    fw_signature = '{}+{}'.format(fw_version, driver_version)
    fw_signature = int(hashlib.md5(fw_signature.encode()).hexdigest(),
                       16) % 1000
    serial_hash = int(hashlib.md5(dut.serial.encode()).hexdigest(), 16) % 1000
    return {
        'config_signature': bdf_signature,
        'fw_signature': fw_signature,
        'serial_hash': serial_hash
    }


def push_config(dut, config_file):
    config_files_list = dut.adb.shell('ls /vendor/etc/*.cal').splitlines()
    for dst_file in config_files_list:
        dut.push_system_file(config_file, dst_file)
    dut.reboot()


def start_wifi_logging(dut):
    pass


def stop_wifi_logging(dut):
    pass


def push_firmware(dut, firmware_files):
    """Function to push Wifi firmware files

    Args:
        dut: dut to push bdf file to
        firmware_files: path to wlanmdsp.mbn file
        datamsc_file: path to Data.msc file
    """
    for file in firmware_files:
        dut.push_system_file(file, '/vendor/firmware/')
    dut.reboot()


def disable_beamforming(dut):
    dut.adb.shell('wl txbf 0')


class LinkLayerStats():

    LLSTATS_CMD = 'wl dump ampdu; wl counters;'
    LL_STATS_CLEAR_CMD = 'wl dump_clear ampdu; wl reset_cnts;'
    MCS_REGEX = re.compile(r'(?P<count>[0-9]+)\((?P<percent>[0-9]+)%\)')
    RX_REGEX = re.compile(r'RX HE\s+:\s*(?P<nss1>[0-9, ,(,),%]*)'
                          '\n\s*:?\s*(?P<nss2>[0-9, ,(,),%]*)')
    TX_REGEX = re.compile(r'TX HE\s+:\s*(?P<nss1>[0-9, ,(,),%]*)'
                          '\n\s*:?\s*(?P<nss2>[0-9, ,(,),%]*)')
    TX_PER_REGEX = re.compile(r'HE PER\s+:\s*(?P<nss1>[0-9, ,(,),%]*)'
                              '\n\s*:?\s*(?P<nss2>[0-9, ,(,),%]*)')
    RX_FCS_REGEX = re.compile(
        r'rxbadfcs (?P<rx_bad_fcs>[0-9]*).+\n.+goodfcs (?P<rx_good_fcs>[0-9]*)'
    )
    RX_AGG_REGEX = re.compile(r'rxmpduperampdu (?P<aggregation>[0-9]*)')
    TX_AGG_REGEX = re.compile(r' mpduperampdu (?P<aggregation>[0-9]*)')
    TX_AGG_STOP_REGEX = re.compile(
        r'agg stop reason: tot_agg_tried (?P<agg_tried>[0-9]+) agg_txcancel (?P<agg_canceled>[0-9]+) (?P<agg_stop_reason>.+)'
    )
    TX_AGG_STOP_REASON_REGEX = re.compile(
        r'(?P<reason>\w+) [0-9]+ \((?P<value>[0-9]+%)\)')
    MCS_ID = collections.namedtuple(
        'mcs_id', ['mode', 'num_streams', 'bandwidth', 'mcs', 'gi'])
    MODE_MAP = {'0': '11a/g', '1': '11b', '2': '11n', '3': '11ac'}
    BW_MAP = {'0': 20, '1': 40, '2': 80}

    def __init__(self, dut, llstats_enabled=True):
        self.dut = dut
        self.llstats_enabled = llstats_enabled
        self.llstats_cumulative = self._empty_llstats()
        self.llstats_incremental = self._empty_llstats()

    def update_stats(self):
        if self.llstats_enabled:
            try:
                llstats_output = self.dut.adb.shell(self.LLSTATS_CMD,
                                                    timeout=0.3)
                self.dut.adb.shell_nb(self.LL_STATS_CLEAR_CMD)
            except:
                llstats_output = ''
        else:
            llstats_output = ''
        self._update_stats(llstats_output)

    def reset_stats(self):
        self.llstats_cumulative = self._empty_llstats()
        self.llstats_incremental = self._empty_llstats()

    def _empty_llstats(self):
        return collections.OrderedDict(mcs_stats=collections.OrderedDict(),
                                       mpdu_stats=collections.OrderedDict(),
                                       summary=collections.OrderedDict())

    def _empty_mcs_stat(self):
        return collections.OrderedDict(txmpdu=0,
                                       rxmpdu=0,
                                       mpdu_lost=0,
                                       retries=0,
                                       retries_short=0,
                                       retries_long=0)

    def _mcs_id_to_string(self, mcs_id):
        mcs_string = '{} Nss{} MCS{} GI{}'.format(mcs_id.mode,
                                                  mcs_id.num_streams,
                                                  mcs_id.mcs, mcs_id.gi)
        return mcs_string

    def _parse_mcs_stats(self, llstats_output):
        llstats_dict = {}
        # Look for per-peer stats
        match = re.search(self.RX_REGEX, llstats_output)
        if not match:
            self.reset_stats()
            return collections.OrderedDict()
        # Find and process all matches for per stream stats
        rx_match = re.search(self.RX_REGEX, llstats_output)
        tx_match = re.search(self.TX_REGEX, llstats_output)
        tx_per_match = re.search(self.TX_PER_REGEX, llstats_output)
        for nss in [1, 2]:
            rx_mcs_iter = re.finditer(self.MCS_REGEX, rx_match.group(nss))
            tx_mcs_iter = re.finditer(self.MCS_REGEX, tx_match.group(nss))
            tx_per_iter = re.finditer(self.MCS_REGEX, tx_per_match.group(nss))
            for mcs, (rx_mcs_stats, tx_mcs_stats,
                      tx_per_mcs_stats) in enumerate(
                          zip(rx_mcs_iter, tx_mcs_iter, tx_per_iter)):
                current_mcs = self.MCS_ID('11ax', nss, 0, mcs, 0)
                current_stats = collections.OrderedDict(
                    txmpdu=int(tx_mcs_stats.group('count')),
                    rxmpdu=int(rx_mcs_stats.group('count')),
                    mpdu_lost=0,
                    retries=tx_per_mcs_stats.group('count'),
                    retries_short=0,
                    retries_long=0)
                llstats_dict[self._mcs_id_to_string(
                    current_mcs)] = current_stats
        return llstats_dict

    def _parse_mpdu_stats(self, llstats_output):
        rx_agg_match = re.search(self.RX_AGG_REGEX, llstats_output)
        tx_agg_match = re.search(self.TX_AGG_REGEX, llstats_output)
        tx_agg_stop_match = re.search(self.TX_AGG_STOP_REGEX, llstats_output)
        rx_fcs_match = re.search(self.RX_FCS_REGEX, llstats_output)
        if rx_agg_match and tx_agg_match and tx_agg_stop_match and rx_fcs_match:
            agg_stop_dict = collections.OrderedDict(
                rx_aggregation=int(rx_agg_match.group('aggregation')),
                tx_aggregation=int(tx_agg_match.group('aggregation')),
                tx_agg_tried=int(tx_agg_stop_match.group('agg_tried')),
                tx_agg_canceled=int(tx_agg_stop_match.group('agg_canceled')),
                rx_good_fcs=int(rx_fcs_match.group('rx_good_fcs')),
                rx_bad_fcs=int(rx_fcs_match.group('rx_bad_fcs')),
                agg_stop_reason=collections.OrderedDict())
            agg_reason_match = re.finditer(
                self.TX_AGG_STOP_REASON_REGEX,
                tx_agg_stop_match.group('agg_stop_reason'))
            for reason_match in agg_reason_match:
                agg_stop_dict['agg_stop_reason'][reason_match.group(
                    'reason')] = reason_match.group('value')

        else:
            agg_stop_dict = collections.OrderedDict()
        return agg_stop_dict

    def _generate_stats_summary(self, llstats_dict):
        llstats_summary = collections.OrderedDict(common_tx_mcs=None,
                                                  common_tx_mcs_count=0,
                                                  common_tx_mcs_freq=0,
                                                  common_rx_mcs=None,
                                                  common_rx_mcs_count=0,
                                                  common_rx_mcs_freq=0)
        txmpdu_count = 0
        rxmpdu_count = 0
        for mcs_id, mcs_stats in llstats_dict['mcs_stats'].items():
            if mcs_stats['txmpdu'] > llstats_summary['common_tx_mcs_count']:
                llstats_summary['common_tx_mcs'] = mcs_id
                llstats_summary['common_tx_mcs_count'] = mcs_stats['txmpdu']
            if mcs_stats['rxmpdu'] > llstats_summary['common_rx_mcs_count']:
                llstats_summary['common_rx_mcs'] = mcs_id
                llstats_summary['common_rx_mcs_count'] = mcs_stats['rxmpdu']
            txmpdu_count += mcs_stats['txmpdu']
            rxmpdu_count += mcs_stats['rxmpdu']
        if txmpdu_count:
            llstats_summary['common_tx_mcs_freq'] = (
                llstats_summary['common_tx_mcs_count'] / txmpdu_count)
        if rxmpdu_count:
            llstats_summary['common_rx_mcs_freq'] = (
                llstats_summary['common_rx_mcs_count'] / rxmpdu_count)
        return llstats_summary

    def _update_stats(self, llstats_output):
        self.llstats_cumulative = self._empty_llstats()
        self.llstats_incremental = self._empty_llstats()
        self.llstats_incremental['raw_output'] = llstats_output
        self.llstats_incremental['mcs_stats'] = self._parse_mcs_stats(
            llstats_output)
        self.llstats_incremental['mpdu_stats'] = self._parse_mpdu_stats(
            llstats_output)
        self.llstats_incremental['summary'] = self._generate_stats_summary(
            self.llstats_incremental)
        self.llstats_cumulative['summary'] = self._generate_stats_summary(
            self.llstats_cumulative)
