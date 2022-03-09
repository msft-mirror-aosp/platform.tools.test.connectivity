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
import pyvisa
import time
from acts import logger

VERY_SHORT_SLEEP = 0.1
SUBFRAME_DURATION = 0.001


class Keysight5GTestApp(object):
    """Controller for the Keysight 5G NR Test Application.

    This controller enables interacting with a Keysight Test Application
    running on a remote test PC and implements many of the configuration
    parameters supported in test app.
    """

    VISA_LOCATION = '/opt/keysight/iolibs/libktvisa32.so'

    def __init__(self, config):
        self.config = config
        self.log = logger.create_tagged_trace_logger("{}{}".format(
            self.config['brand'], self.config['model']))
        self.resource_manager = pyvisa.ResourceManager(self.VISA_LOCATION)
        self.test_app = self.resource_manager.open_resource(
            'TCPIP0::{}::{}::INSTR'.format(self.config['ip_address'],
                                           self.config['hislip_interface']))
        self.test_app.timeout = 200000
        self.test_app.write_termination = '\n'
        self.test_app.read_termination = '\n'
        self.test_app.query_delay = 0.005

        inst_id = self.send_cmd('*IDN?', 1)
        if 'Keysight' not in inst_id[0]:
            self.log.error(
                'Failed to connect to Keysight Test App: {}'.format(inst_id))
        else:
            self.log.info("Test App ID: {}".format(inst_id))

    def destroy(self):
        self.test_app.close()

    ### Programming Utilities
    @staticmethod
    def _format_cells(cells):
        "Helper function to format list of cells."
        if isinstance(cells, int):
            return 'CELL{}'.format(cells)
        elif isinstance(cells, str):
            return cells
        elif isinstance(cells, list):
            cell_list = [
                Keysight5GTestApp._format_cells(cell) for cell in cells
            ]
            cell_list = ','.join(cell_list)
            return cell_list

    @staticmethod
    def _format_response(response):
        "Helper function to format test app response."

        def _format_response_entry(entry):
            try:
                formatted_entry = float(entry)
            except:
                formatted_entry = entry
            return formatted_entry

        if ',' not in response:
            return _format_response_entry(response)
        response = response.split(',')
        formatted_response = [
            _format_response_entry(entry) for entry in response
        ]
        return formatted_response

    def send_cmd(self, command, read_response=0):
        "Helper function to write to or query test app."
        if read_response:
            try:
                return Keysight5GTestApp._format_response(
                    self.test_app.query(command))
            except:
                raise RuntimeError('Lost connection to test app.')
        else:
            try:
                self.test_app.write(command)
                self.send_cmd('*OPC?', 1)
            except:
                raise RuntimeError('Lost connection to test app.')
            return None

    def import_scpi_file(self, file_name):
        "Function to import SCPI file specified in file_name."
        self.send_cmd("SYSTem:SCPI:IMPort '{}'".format(file_name))
        while int(self.send_cmd('SYSTem:SCPI:IMPort:STATus?', 1)):
            self.send_cmd('*OPC?', 1)
        self.log.info('Done with SCPI import')

    ### Configure Cells
    def assert_cell_off_decorator(func):
        "Decorator function that ensures cells or off when configuring them"

        def inner(self, *args, **kwargs):
            if "nr" in func.__name__:
                cell_type = 'NR5G'
            else:
                cell_type = kwargs.get('cell_type', args[0])
            cell = kwargs.get('cell', args[1])
            cell_state = self.get_cell_state(cell_type, cell)
            if cell_state:
                self.log.error('Cell must be off when calling {}'.format(
                    func.__name__))
            return (func(self, *args, **kwargs))

        return inner

    def assert_cell_off(self, cell_type, cell):
        cell_state = self.get_cell_state(cell_type, cell)
        if cell_state:
            self.log.error('Cell must be off')

    def get_cell_state(self, cell_type, cell):
        """Function to get cell on/off state.

        Args:
            cell_type: LTE or NR5G cell
            cell: cell/carrier number
        Returns:
            cell_state: boolean. True if cell on
        """
        cell_state = int(
            self.send_cmd(
                'BSE:CONFig:{}:{}:ACTive:STATe?'.format(
                    cell_type, Keysight5GTestApp._format_cells(cell)), 1))
        return cell_state

    def wait_for_cell_status(self, cell_type, cell, states, timeout):
        """Function to wait for a specific cell status

        Args:
            cell_type: LTE or NR5G cell
            cell: cell/carrier number
            states: list of acceptable states (ON, CONN, AGG, ACT, etc)
            timeout: amount of time to wait for requested status
        Returns:
            True if one of the listed states is achieved
        Raises:
            Error if timed out waiting for acceptable state.
        """
        states = [states] if isinstance(states, str) else states
        for i in range(int(timeout / VERY_SHORT_SLEEP)):
            current_state = self.send_cmd(
                'BSE:STATus:{}:{}?'.format(
                    cell_type, Keysight5GTestApp._format_cells(cell)), 1)
            if current_state in states:
                return True
            time.sleep(VERY_SHORT_SLEEP)
        self.log.error('Timout waiting for {} {} {}'.format(
            cell_type, Keysight5GTestApp._format_cells(cell), states))
        return False

    def set_cell_state(self, cell_type, cell, state):
        """Function to set cell state

        Args:
            cell_type: LTE or NR5G cell
            cell: cell/carrier number
            state: requested state
        """
        self.send_cmd('BSE:CONFig:{}:{}:ACTive:STATe {}'.format(
            cell_type, Keysight5GTestApp._format_cells(cell), state))

    #@assert_cell_off_decorator
    def set_cell_bandwidth(self, cell_type, cell, bandwidth):
        """Function to set cell bandwidth

        Args:
            cell_type: LTE or NR5G cell
            cell: cell/carrier number
            bandwidth: requested bandwidth
        """
        self.assert_cell_off(cell_type, cell)
        self.send_cmd('BSE:CONFig:{}:{}:DL:BW {}'.format(
            cell_type, Keysight5GTestApp._format_cells(cell), bandwidth))

    #@assert_cell_off_decorator
    def set_cell_channel(self, cell_type, cell, channel):
        """Function to set cell frequency/channel

        Args:
            cell_type: LTE or NR5G cell
            cell: cell/carrier number
            channel: requested channel
        """
        self.assert_cell_off(cell_type, cell)
        self.send_cmd('BSE:CONFig:{}:{}:DL:CHANnel {}'.format(
            cell_type, Keysight5GTestApp._format_cells(cell), channel))

    #@assert_cell_off_decorator
    def set_cell_mimo_config(self, cell_type, cell, link, mimo_config):
        """Function to set cell mimo config.

        Allows setting mimo config. This field only appears for an FR1 cell
        with a DL MIMO Configuration of 1x1, or for an FR2 cell in a single
        RRH system.

        Args:
            cell_type: LTE or NR5G cell
            cell: cell/carrier number
            link: uplink or downlink
            mimo_config: requested mimo configuration (refer to SCPI
                         documentation for allowed range of values)
        """
        self.assert_cell_off(cell_type, cell)
        self.send_cmd('BSE:CONFig:{}:{}:{}:ANTenna:CONFig {}'.format(
            cell_type, Keysight5GTestApp._format_cells(cell), link,
            mimo_config))

    def set_cell_dl_power(self, cell_type, cell, power, full_bw):
        """Function to set cell power

        Args:
            cell_type: LTE or NR5G cell
            cell: cell/carrier number
            power: requested power
            full_bw: boolean controlling if requested power is per channel
                     or subcarrier
        """
        if full_bw:
            self.send_cmd('BSE:CONFIG:{}:{}:DL:POWer:CHANnel {}'.format(
                cell_type, Keysight5GTestApp._format_cells(cell), power))
        else:
            self.send_cmd('BSE:CONFIG:{}:{}:DL:POWer:EPRE {}'.format(
                cell_type, Keysight5GTestApp._format_cells(cell), power))

    #@assert_cell_off_decorator
    def set_cell_duplex_mode(self, cell_type, cell, duplex_mode):
        """Function to set cell power

        Args:
            cell_type: LTE or NR5G cell
            cell: cell/carrier number
            duplex mode: TDD or FDD
        """
        self.assert_cell_off(cell_type, cell)
        self.send_cmd('BSE:CONFig:{}:{}:DUPLEX:MODe {}'.format(
            cell_type, Keysight5GTestApp._format_cells(cell), duplex_mode))

    #@assert_cell_off_decorator
    def set_cell_band(self, cell_type, cell, band):
        """Function to set cell power

        Args:
            cell_type: LTE or NR5G cell
            cell: cell/carrier number
            band: LTE or NR band (e.g. 1,3,N260, N77)
        """
        self.assert_cell_off(cell_type, cell)
        self.send_cmd('BSE:CONFig:{}:{}:BAND {}'.format(
            cell_type, Keysight5GTestApp._format_cells(cell), band))

    def set_dl_carriers(self, cells):
        """Function to set aggregated DL NR5G carriers

        Args:
            cells: list of DL cells/carriers to aggregate with LTE (e.g. [1,2])
        """
        self.send_cmd('BSE:CONFig:NR5G:CELL1:CAGGregation:NRCC:DL {}'.format(
            Keysight5GTestApp._format_cells(cells)))

    def set_ul_carriers(self, cells):
        """Function to set aggregated UL NR5G carriers

        Args:
            cells: list of DL cells/carriers to aggregate with LTE (e.g. [1,2])
        """
        self.send_cmd('BSE:CONFig:NR5G:CELL1:CAGGregation:NRCC:UL {}'.format(
            Keysight5GTestApp._format_cells(cells)))

    #@assert_cell_off_decorator
    def set_nr_cell_schedule_scenario(self, cell, scenario):
        """Function to set NR schedule to one of predefince quick configs.

        Args:
            cell: cell number to address. schedule will apply to all cells
            scenario: one of the predefined test app schedlue quick configs
                      (e.g. FULL_TPUT, BASIC).
        """
        self.assert_cell_off('NR5G', cell)
        self.send_cmd(
            'BSE:CONFig:NR5G:{}:SCHeduling:QCONFig:SCENario {}'.format(
                Keysight5GTestApp._format_cells(cell), scenario))
        self.send_cmd('BSE:CONFig:NR5G:SCHeduling:QCONFig:APPLy:ALL')

    #@assert_cell_off_decorator
    def set_nr_cell_mcs(self, cell, dl_mcs, ul_mcs):
        """Function to set NR cell DL & UL MCS

        Args:
            cell: cell number to address. MCS will apply to all cells
            dl_mcs: mcs index to use on DL
            ul_mcs: mcs index to use on UL
        """
        self.assert_cell_off('NR5G', cell)
        self.send_cmd('BSE:CONFig:NR5G:{}:SCHeduling:QCONFig:DL:MCS {}'.format(
            Keysight5GTestApp._format_cells(cell), dl_mcs))
        self.send_cmd('BSE:CONFig:NR5G:{}:SCHeduling:QCONFig:UL:MCS {}'.format(
            Keysight5GTestApp._format_cells(cell), ul_mcs))
        self.send_cmd('BSE:CONFig:NR5G:SCHeduling:QCONFig:APPLy:ALL')

    def set_nr_ul_dft_precoding(self, cell, precoding):
        """Function to configure DFT-precoding on uplink.

        Args:
            cell: cell number to address. MCS will apply to all cells
            precoding: 0/1 to disable/enable precoding
        """
        self.assert_cell_off('NR5G', cell)
        precoding_str = "ENABled" if precoding else "DISabled"
        self.send_cmd(
            'BSE:CONFig:NR5G:{}:SCHeduling:QCONFig:UL:TRANsform:PRECoding {}'.
            format(Keysight5GTestApp._format_cells(cell), precoding_str))

    def configure_ul_clpc(self, channel, mode, target):
        """Function to configure UL power control on all cells/carriers

        Args:
            channel: physical channel must be PUSCh or PUCCh
            mode: mode supported by test app (all up/down bits, target, etc)
            target: target power if mode is set to target
        """
        self.send_cmd('BSE:CONFig:NR5G:UL:{}:CLPControl:MODE:ALL {}'.format(
            channel, mode))
        if "tar" in mode.lower():
            self.send_cmd(
                'BSE:CONFig:NR5G:UL:{}:CLPControl:TARGet:POWer:ALL {}'.format(
                    channel, target))

    def apply_carrier_agg(self):
        """Function to start carrier aggregation on already configured cells"""
        if self.wait_for_cell_status('LTE', 'CELL1', 'CONN', 60):
            self.send_cmd(
                'BSE:CONFig:LTE:CELL1:CAGGregation:AGGRegate:NRCC:APPly')
        else:
            raise RuntimeError('LTE must be connected to start aggregation.')

    def get_ip_throughput(self, cell_type):
        """Function to query IP layer throughput on LTE or NR

        Args:
            cell_type: LTE or NR5G
        Returns:
            dict containing DL and UL IP-layer throughput
        """
        #{ report-count, total-bytes, current transfer-rate, average transfer-rate, peak transfer-rate }
        dl_tput = self.send_cmd(
            'BSE:MEASure:{}:BTHRoughput:DL:THRoughput:IP?'.format(cell_type),
            1)
        ul_tput = self.send_cmd(
            'BSE:MEASure:{}:BTHRoughput:UL:THRoughput:IP?'.format(cell_type),
            1)
        return {'dl_tput': dl_tput, 'ul_tput': ul_tput}

    def _get_throughput(self, cell_type, link, cell):
        """Helper function to get PHY layer throughput on single cell"""
        if cell_type == 'LTE':
            tput_response = self.send_cmd(
                'BSE:MEASure:LTE:{}:BTHRoughput:{}:THRoughput:OTA:{}?'.format(
                    Keysight5GTestApp._format_cells(cell), link,
                    Keysight5GTestApp._format_cells(cell)), 1)
        elif cell_type == 'NR5G':
            #progress-count, ack-count, ack-ratio, nack-count, nack-ratio,  statdtx-count,  statdtx-ratio,  pdschBlerCount,  pdschBlerRatio,  pdschTputRatio.
            tput_response = self.send_cmd(
                'BSE:MEASure:NR5G:BTHRoughput:{}:THRoughput:OTA:{}?'.format(
                    link, Keysight5GTestApp._format_cells(cell)), 1)
        tput_result = {
            'frame_count': tput_response[0],
            'current_tput': tput_response[1],
            'min_tput': tput_response[2],
            'max_tput': tput_response[3],
            'average_tput': tput_response[4],
            'theoretical_tput': tput_response[5]
        }
        return tput_result

    def get_throughput(self, cell_type, cells):
        """Function to get PHY layer throughput on on or more cells

        This function returns the throughput data on the requested cells
        during the last BLER test run, i.e., throughpt data must be fetch at
        the end/after a BLE test run on the Keysight Test App.

        Args:
            cell_type: LTE or NR5G
            cells: list of cells to query for throughput data
        Returns:
            tput_result: dict containing all throughput statistics
        """
        if not isinstance(cells, list):
            cells = [cells]
        tput_result = collections.OrderedDict()
        for cell in cells:
            tput_result[cell] = {
                'DL': self._get_throughput(cell_type, 'DL', cell),
                'UL': self._get_throughput(cell_type, 'UL', cell)
            }
            frame_count = tput_result[cell]['DL']['frame_count']
        agg_tput = {
            'DL': {
                'frame_count': frame_count,
                'current_tput': 0,
                'min_tput': 0,
                'max_tput': 0,
                'average_tput': 0,
                'theoretical_tput': 0
            },
            'UL': {
                'frame_count': frame_count,
                'current_tput': 0,
                'min_tput': 0,
                'max_tput': 0,
                'average_tput': 0,
                'theoretical_tput': 0
            }
        }
        for cell, cell_tput in tput_result.items():
            for link, link_tput in cell_tput.items():
                for key, value in link_tput.items():
                    if 'tput' in key:
                        agg_tput[link][key] = agg_tput[link][key] + value
        tput_result['total'] = agg_tput
        return tput_result

    def _clear_bler_measurement(self, cell_type):
        """Helper function to clear BLER results."""
        if cell_type == 'LTE':
            self.send_cmd('BSE:MEASure:LTE:CELL1:BTHRoughput:CLEar')
        elif cell_type == 'NR5G':
            self.send_cmd('BSE:MEASure:NR5G:BTHRoughput:CLEar')

    def _configure_bler_measurement(self, cell_type, continuous, length):
        """Helper function to configure BLER results."""
        if continuous:
            if cell_type == 'LTE':
                self.send_cmd('BSE:MEASure:LTE:CELL1:BTHRoughput:CONTinuous 1')
            elif cell_type == 'NR5G':
                self.send_cmd('BSE:MEASure:NR5G:BTHRoughput:CONTinuous 1')
        elif length > 1:
            if cell_type == 'LTE':
                self.send_cmd(
                    'BSE:MEASure:LTE:CELL1:BTHRoughput:LENGth {}'.format(
                        length))
                self.send_cmd('BSE:MEASure:LTE:CELL1:BTHRoughput:CONTinuous 0')
            elif cell_type == 'NR5G':
                self.send_cmd(
                    'BSE:MEASure:NR5G:BTHRoughput:LENGth {}'.format(length))
                self.send_cmd('BSE:MEASure:NR5G:BTHRoughput:CONTinuous 0')

    def _set_bler_measurement_state(self, cell_type, state):
        """Helper function to start or stop BLER measurement."""
        if cell_type == 'LTE':
            self.send_cmd(
                'BSE:MEASure:LTE:CELL1:BTHRoughput:STATe {}'.format(state))
        elif cell_type == 'NR5G':
            self.send_cmd(
                'BSE:MEASure:NR5G:BTHRoughput:STATe {}'.format(state))

    def start_bler_measurement(self, cell_type, cells, length):
        """Function to kick off a BLER measurement

        Args:
            cell_type: LTE or NR5G
            length: integer length of BLER measurements in subframes
        """
        self._clear_bler_measurement('NR5G')
        self._clear_bler_measurement('LTE')
        self._set_bler_measurement_state(cell_type, 0)
        self._configure_bler_measurement(cell_type, 0, length)
        self._set_bler_measurement_state(cell_type, 1)
        bler_check = self.get_bler_result(cell_type, cells, length)
        time.sleep(0.1)
        if bler_check['total']['DL']['frame_count'] == 0:
            self.log.warning('BLER measurement did not start. Retrying')
            self.start_bler_measurement(cell_type, cells, length)

    def _get_bler(self, cell_type, link, cell):
        """Helper function to get single-cell BLER measurement results."""
        if cell_type == 'LTE':
            bler_response = self.send_cmd(
                'BSE:MEASure:LTE:CELL1:BTHRoughput:{}:BLER:CELL1?'.format(
                    link), 1)
        elif cell_type == 'NR5G':
            #progress-count, ack-count, ack-ratio, nack-count, nack-ratio,  statdtx-count,  statdtx-ratio,  pdschBlerCount,  pdschBlerRatio,  pdschTputRatio.
            bler_response = self.send_cmd(
                'BSE:MEASure:NR5G:BTHRoughput:{}:BLER:{}?'.format(
                    link, Keysight5GTestApp._format_cells(cell)), 1)
        bler_result = {
            'frame_count': bler_response[0],
            'ack_count': bler_response[1],
            'ack_ratio': bler_response[2],
            'nack_count': bler_response[3],
            'nack_ratio': bler_response[4]
        }
        return bler_result

    def get_bler_result(self, cell_type, cells, length, wait_for_length=1):
        """Function to get BLER results.

        This function gets the BLER measurements results on one or more
        requested cells. The function can either return BLER statistics
        immediately or wait until a certain number of subframes have been
        counted (e.g. if the BLER measurement is done)

        Args:
            cell_type: LTE or NR5G
            cells: list of cells for which to get BLER
            length: number of subframes to wait for (typically set to the
                    configured length of the BLER measurements)
            wait_for_length: boolean to block/wait till length subframes have
            been counted.
        Returns:
            bler_result: dict containing per-cell and aggregate BLER results
        """

        if not isinstance(cells, list):
            cells = [cells]
        while True:
            dl_bler = self._get_bler(cell_type, 'DL', cells[0])
            if dl_bler['frame_count'] < length:
                time.sleep(VERY_SHORT_SLEEP)
            else:
                break

        bler_result = collections.OrderedDict()
        for cell in cells:
            bler_result[cell] = {
                'DL': self._get_bler(cell_type, 'DL', cell),
                'UL': self._get_bler(cell_type, 'UL', cell)
            }
        agg_bler = {
            'DL': {
                'frame_count': length,
                'ack_count': 0,
                'ack_ratio': 0,
                'nack_count': 0,
                'nack_ratio': 0
            },
            'UL': {
                'frame_count': length,
                'ack_count': 0,
                'ack_ratio': 0,
                'nack_count': 0,
                'nack_ratio': 0
            }
        }
        for cell, cell_bler in bler_result.items():
            for link, link_bler in cell_bler.items():
                for key, value in link_bler.items():
                    if 'ack_count' in key:
                        agg_bler[link][key] = agg_bler[link][key] + value
        dl_ack_nack = agg_bler['DL']['ack_count'] + agg_bler['DL']['nack_count']
        ul_ack_nack = agg_bler['UL']['ack_count'] + agg_bler['UL']['nack_count']
        try:
            agg_bler['DL'][
                'ack_ratio'] = agg_bler['DL']['ack_count'] / dl_ack_nack
            agg_bler['DL'][
                'nack_ratio'] = agg_bler['DL']['nack_count'] / dl_ack_nack
            agg_bler['UL'][
                'ack_ratio'] = agg_bler['UL']['ack_count'] / ul_ack_nack
            agg_bler['UL'][
                'nack_ratio'] = agg_bler['UL']['nack_count'] / ul_ack_nack
        except:
            self.log.debug(bler_result)
            agg_bler['DL']['ack_ratio'] = float('nan')
            agg_bler['DL']['nack_ratio'] = float('nan')
            agg_bler['UL']['ack_ratio'] = float('nan')
            agg_bler['UL']['nack_ratio'] = float('nan')
        bler_result['total'] = agg_bler
        return bler_result

    def measure_bler(self, cell_type, cells, length):
        """Function to start and wait for BLER results.

        This function starts a BLER test on a number of cells and waits for the
        test to complete before returning the BLER measurements.

        Args:
            cell_type: LTE or NR5G
            cells: list of cells for which to get BLER
            length: number of subframes to wait for (typically set to the
                    configured length of the BLER measurements)
        Returns:
            bler_result: dict containing per-cell and aggregate BLER results
        """
        self.start_bler_measurement(cell_type, cells, length)
        time.sleep(length * SUBFRAME_DURATION)
        bler_result = self.get_bler_result(cell_type, cells, length, 1)
        return bler_result