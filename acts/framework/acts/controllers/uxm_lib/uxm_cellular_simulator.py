#   Copyright 2022 - The Android Open Source Project
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
import os
import socket
import time

from acts.controllers.cellular_simulator import AbstractCellularSimulator


class UXMCellularSimulator(AbstractCellularSimulator):
    """A cellular simulator for UXM callbox. """

    # Keys to obtain data from cell_info dictionary.
    KEY_CELL_NUMBER = "cell_number"
    KEY_CELL_TYPE = "cell_type"

    # UXM socket port
    UXM_PORT = 5125

    # UXM SCPI COMMAND
    SCPI_IMPORT_STATUS_QUERY_CMD = 'SYSTem:SCPI:IMPort:STATus?'
    SCPI_SYSTEM_ERROR_CHECK_CMD = 'SYST:ERR?\n'
    # require: path to SCPI file
    SCPI_IMPORT_SCPI_FILE_CMD = 'SYSTem:SCPI:IMPort "{}"\n'
    # require: 1. cell type (E.g. NR5G), 2. cell number (E.g CELL1)
    SCPI_CELL_ON_CMD = 'BSE:CONFig:{}:{}:ACTive 1'
    # require: 1. cell type (E.g. NR5G), 2. cell number (E.g CELL1)
    SCPI_CELL_OFF_CMD = 'BSE:CONFig:{}:{}:ACTive 0'
    # require: 1. cell type (E.g. NR5G), 2. cell number (E.g CELL1)
    SCPI_GET_CELL_STATUS = 'BSE:STATus:{}:{}?'
    SCPI_CHECK_CONNECTION_CMD = '*IDN?\n'

    def __init__(self, ip_address, custom_files):
        """Initializes the cellular simulator.

        Args:
            ip_address: the ip address of dektop where Keysight Test Application
                is installed.
            custom_files: a list of file path for custom files.
        """
        super().__init__()
        self.custom_files = custom_files
        self.rockbottom_script = None
        self.cells = []

        # get roclbottom file
        for file in self.custom_files:
            if 'rockbottom_' in file:
                self.rockbottom_script = file

        # connect to Keysight Test Application via socket
        self.socket = self._socket_connect(ip_address, self.UXM_PORT)
        self.check_socket_connection()
        self.timeout = 120

    def set_rockbottom_script_path(self, path):
        """Set path to rockbottom script.

        Args:
            path: path to rockbottom script.
        """
        self.rockbottom_script = path

    def set_cell_info(self, cell_info):
        """Set type and number for multiple cells.

        Args:
            cell_info: list of dictionaries,
                each dictionary contain cell type
                and cell number for each cell
                that the simulator need to control.
        """
        if not cell_info:
            raise ValueError('Missing cell info from configurations file')
        self.cells = cell_info

    def turn_cell_on(self, cell_type, cell_number):
        """Turn UXM's cell on.

        Args:
            cell_type: type of cell (e.g NR5G, LTE).
            cell_number: ordinal number of a cell.
        """
        if cell_type and cell_number:
            self._socket_send_SCPI_command(
                self.SCPI_CELL_ON_CMD.format(cell_type, cell_number))
        else:
            raise ValueError('Invalid cell info\n' +
                             f' cell type: {cell_type}\n' +
                             f' cell number: {cell_number}\n')

    def turn_cell_off(self, cell_type, cell_number):
        """Turn UXM's cell off.

        Args:
            cell_type: type of cell (e.g NR5G, LTE).
            cell_number: ordinal number of a cell.
        """
        if cell_type and cell_number:
            self._socket_send_SCPI_command(
                self.SCPI_CELL_OFF_CMD.format(cell_type, cell_number))
        else:
            raise ValueError('Invalid cell info\n' +
                             f' cell type: {cell_type}\n' +
                             f' cell number: {cell_number}\n')

    def get_cell_status(self, cell_type, cell_number):
        """Get status of cell.

        Args:
            cell_type: type of cell (e.g NR5G, LTE).
            cell_number: ordinal number of a cell.
        """
        if not cell_type or not cell_number:
            raise ValueError('Invalid cell with\n' +
                             f' cell type: {cell_type}\n' +
                             f' cell number: {cell_number}\n')

        return self._socket_send_SCPI_for_result_command(
            self.SCPI_GET_CELL_STATUS.format(cell_type, cell_number))

    def check_socket_connection(self):
        """Check if the socket connection is established.

        Query the identification of the Keysight Test Application
        we are trying to connect to. Empty response indicates
        connection fail, and vice versa.
        """
        self.socket.sendall(self.SCPI_CHECK_CONNECTION_CMD.encode())
        response = self.socket.recv(1024).decode()
        if response:
            self.log.info(f'Connected to: {response}')
        else:
            self.log.error('Fail to connect to callbox')

    def _socket_connect(self, host, port):
        """Create socket connection.

        Args:
            host: IP address of desktop where Keysight Test Application resides.
            port: port that Keysight Test Application is listening for socket
                communication.
        Return:
            s: socket object.
        """
        self.log.info('Establishing connection to callbox via socket')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        return s

    def _socket_send_SCPI_command(self, command):
        """Send SCPI command without expecting response.

        Args:
            command: a string SCPI command.
        """
        # make sure there is a line break for the socket to send command
        command = command + '\n'
        # send command
        self.socket.sendall(command.encode())
        self.log.info(f'Sent {command}')

    def _socket_receive_SCPI_result(self):
        """Receive response from socket. """
        i = 1
        response = ''
        while i < self.timeout and not response:
            response = self.socket.recv(1024).decode()
            i += 1
        return response

    def _socket_send_SCPI_for_result_command(self, command):
        """Send SCPI command and expecting response.

        Args:
            command: a string SCPI command.
        """
        self._socket_send_SCPI_command(command)
        response = self._socket_receive_SCPI_result()
        return response

    def check_system_error(self):
        """Query system error from Keysight Test Application.

        Return:
            status: a message indicate the number of errors
                and detail of errors if any.
                a string `0,"No error"` indicates no error.
        """
        status = self._socket_send_SCPI_for_result_command(
            self.SCPI_SYSTEM_ERROR_CHECK_CMD)
        self.log.info(f'System error status: {status}')
        return status

    def import_configuration(self, path):
        """Import SCPI config file.

        Args:
            path: path to SCPI file.
        """
        self._socket_send_SCPI_command(
            self.SCPI_IMPORT_SCPI_FILE_CMD.format(path))
        time.sleep(30)

    def destroy(self):
        """Close socket connection with UXM. """
        self.socket.close()

    def setup_lte_scenario(self, path):
        """Configures the equipment for an LTE simulation.

        Args:
            path: path to SCPI config file.
        """
        self.import_configuration(path)

    def dut_rockbottom(self, dut):
        """Set the dut to rockbottom state.

        Args:
            dut: a CellularAndroid controller.
        """
        # The rockbottom script might include a device reboot, so it is
        # necessary to stop SL4A during its execution.
        dut.ad.stop_services()
        self.log.info('Executing rockbottom script for ' + dut.ad.model)
        os.chmod(self.rockbottom_script, 0o777)
        os.system('{} {}'.format(self.rockbottom_script, dut.ad.serial))
        # Make sure the DUT is in root mode after coming back
        dut.ad.root_adb()
        # Restart SL4A
        dut.ad.start_services()

    def wait_until_attached_one_cell(self,
                                     cell_type,
                                     cell_number,
                                     dut,
                                     wait_for_camp_interval,
                                     attach_retries,
                                     change_dut_setting_allow=True):
        """Wait until connect to given UXM cell.

        After turn off airplane mode, sleep for
        wait_for_camp_interval seconds for device to camp.
        If not device is not connected after the wait,
        either toggle airplane mode on/off or reboot device.
        Args:
            cell_type: type of cell
                which we are trying to connect to.
            cell_number: ordinal number of a cell
                which we are trying to connect to.
            dut: a CellularAndroid controller.
            wait_for_camp_interval: sleep interval,
                wait for device to camp.
            attach_retries: number of retry
                to wait for device
                to connect to 1 basestation.
            change_dut_setting_allow: turn on/off APM
                or reboot device helps with device camp time.
                However, if we are trying to connect to second cell
                changing APM status or reboot is not allowed.
        Raise:
            AbstractCellularSimulator.CellularSimulatorError:
                device unable to connect to cell.
        """
        # airplane mode off
        dut.toggle_airplane_mode(False)
        time.sleep(5)
        # turn cell on
        self.turn_cell_on(cell_type, cell_number)
        time.sleep(5)

        # waits for connect
        for index in range(1, attach_retries):
            # airplane mode on
            time.sleep(wait_for_camp_interval)
            cell_state = self.get_cell_status(cell_type, cell_number)
            self.log.info(f'cell state: {cell_state}')
            if cell_state == 'CONN\n':
                return True
            if change_dut_setting_allow:
                if (index % 4) == 0:
                    dut.ad.reboot()
                    if self.rockbottom_script:
                        self.dut_rockbottom(dut)
                    else:
                        self.log.warning(
                            f'Rockbottom script {self} was not executed after reboot')
                else:
                    # airplane mode on
                    dut.toggle_airplane_mode(True)
                    time.sleep(5)
                    # airplane mode off
                    dut.toggle_airplane_mode(False)

        # Phone cannot connected to basestation of callbox
        raise AbstractCellularSimulator.CellularSimulatorError(
            f'Phone was unable to connect to cell: {cell_type}-{cell_number}')

    def wait_until_attached(self, dut, timeout, attach_retries):
        """Waits until the DUT is attached to all required cells.

        Args:
            dut: a CellularAndroid controller.
            timeout: sleep interval,
                wait for device to camp in 1 try.
            attach_retries: number of retry
                to wait for device
                to connect to 1 basestation.
        """
        # get cell info
        first_cell_type = self.cells[0][self.KEY_CELL_TYPE]
        first_cell_number = self.cells[0][self.KEY_CELL_NUMBER]
        if len(self.cells) == 2:
            second_cell_type = self.cells[1][self.KEY_CELL_TYPE]
            second_cell_number = self.cells[1][self.KEY_CELL_NUMBER]

        # connect to 1st cell
        try:
            self.wait_until_attached_one_cell(first_cell_type,
                                              first_cell_number, dut, timeout,
                                              attach_retries)
        except Exception as exc:
            raise RuntimeError(f'Cannot connect to first cell') from exc

        # connect to 2nd cell
        if len(self.cells) == 2:
            self.turn_cell_on(
                second_cell_type,
                second_cell_number,
            )
            self._socket_send_SCPI_command(
                'BSE:CONFig:LTE:CELL1:CAGGregation:AGGRegate:NRCC:DL None')
            self._socket_send_SCPI_command(
                'BSE:CONFig:LTE:CELL1:CAGGregation:AGGRegate:NRCC:UL None')
            self._socket_send_SCPI_command(
                'BSE:CONFig:LTE:CELL1:CAGGregation:AGGRegate:NRCC:DL CELL1')
            self._socket_send_SCPI_command(
                'BSE:CONFig:LTE:CELL1:CAGGregation:AGGRegate:NRCC:DL CELL1')
            time.sleep(1)
            self._socket_send_SCPI_command(
                "BSE:CONFig:LTE:CELL1:CAGGregation:AGGRegate:NRCC:APPly")
            try:
                self.wait_until_attached_one_cell(first_cell_type,
                                                  first_cell_number, dut,
                                                  timeout, attach_retries,
                                                  False)
            except Exception as exc:
                raise RuntimeError(f'Cannot connect to second cell') from exc

    def set_lte_rrc_state_change_timer(self, enabled, time=10):
        """Configures the LTE RRC state change timer.

        Args:
            enabled: a boolean indicating if the timer should be on or off.
            time: time in seconds for the timer to expire.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_band(self, bts_index, band):
        """Sets the band for the indicated base station.

        Args:
            bts_index: the base station number.
            band: the new band.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def get_duplex_mode(self, band):
        """Determines if the band uses FDD or TDD duplex mode

        Args:
            band: a band number.

        Returns:
            an variable of class DuplexMode indicating if band is FDD or TDD.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_input_power(self, bts_index, input_power):
        """Sets the input power for the indicated base station.

        Args:
            bts_index: the base station number.
            input_power: the new input power.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_output_power(self, bts_index, output_power):
        """Sets the output power for the indicated base station.

        Args:
            bts_index: the base station number.
            output_power: the new output power.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_tdd_config(self, bts_index, tdd_config):
        """Sets the tdd configuration number for the indicated base station.

        Args:
            bts_index: the base station number.
            tdd_config: the new tdd configuration number.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_ssf_config(self, bts_index, ssf_config):
        """Sets the Special Sub-Frame config number for the indicated.

        base station.

        Args:
            bts_index: the base station number.
            ssf_config: the new ssf config number.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_bandwidth(self, bts_index, bandwidth):
        """Sets the bandwidth for the indicated base station.

        Args:
            bts_index: the base station number
            bandwidth: the new bandwidth
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_downlink_channel_number(self, bts_index, channel_number):
        """Sets the downlink channel number for the indicated base station.

        Args:
            bts_index: the base station number.
            channel_number: the new channel number.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_mimo_mode(self, bts_index, mimo_mode):
        """Sets the mimo mode for the indicated base station.

        Args:
            bts_index: the base station number
            mimo_mode: the new mimo mode
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_transmission_mode(self, bts_index, tmode):
        """Sets the transmission mode for the indicated base station.

        Args:
            bts_index: the base station number.
            tmode: the new transmission mode.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_scheduling_mode(self,
                            bts_index,
                            scheduling,
                            mcs_dl=None,
                            mcs_ul=None,
                            nrb_dl=None,
                            nrb_ul=None):
        """Sets the scheduling mode for the indicated base station.

        Args:
            bts_index: the base station number.
            scheduling: the new scheduling mode.
            mcs_dl: Downlink MCS.
            mcs_ul: Uplink MCS.
            nrb_dl: Number of RBs for downlink.
            nrb_ul: Number of RBs for uplink.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_dl_256_qam_enabled(self, bts_index, enabled):
        """Determines what MCS table should be used for the downlink.

        This only saves the setting that will be used when configuring MCS.

        Args:
            bts_index: the base station number.
            enabled: whether 256 QAM should be used.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_ul_64_qam_enabled(self, bts_index, enabled):
        """Determines what MCS table should be used for the uplink.

        This only saves the setting that will be used when configuring MCS.

        Args:
            bts_index: the base station number.
            enabled: whether 64 QAM should be used.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_mac_padding(self, bts_index, mac_padding):
        """Enables or disables MAC padding in the indicated base station.

        Args:
            bts_index: the base station number.
            mac_padding: the new MAC padding setting.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_cfi(self, bts_index, cfi):
        """Sets the Channel Format Indicator for the indicated base station.

        Args:
            bts_index: the base station number.
            cfi: the new CFI setting.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_paging_cycle(self, bts_index, cycle_duration):
        """Sets the paging cycle duration for the indicated base station.

        Args:
            bts_index: the base station number.
            cycle_duration: the new paging cycle duration in milliseconds.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def set_phich_resource(self, bts_index, phich):
        """Sets the PHICH Resource setting for the indicated base station.

        Args:
            bts_index: the base station number.
            phich: the new PHICH resource setting.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def lte_attach_secondary_carriers(self, ue_capability_enquiry):
        """Activates the secondary carriers for CA.

        Requires the DUT to be attached to the primary carrier first.

        Args:
            ue_capability_enquiry: UE capability enquiry message to be sent to
              the UE before starting carrier aggregation.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def wait_until_communication_state(self, timeout=120):
        """Waits until the DUT is in Communication state.

        Args:
            timeout: after this amount of time the method will raise
                a CellularSimulatorError exception. Default is 120 seconds.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def wait_until_idle_state(self, timeout=120):
        """Waits until the DUT is in Idle state.

        Args:
            timeout: after this amount of time the method will raise a
                CellularSimulatorError exception. Default is 120 seconds.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def detach(self):
        """ Turns off all the base stations so the DUT loose connection."""
        for cell in self.cells:
            cell_type = cell[self.KEY_CELL_TYPE]
            cell_number = cell[self.KEY_CELL_NUMBER]
            self._socket_send_SCPI_command(
                self.SCPI_CELL_OFF_CMD.format(cell_type, cell_number))

    def stop(self):
        """Stops current simulation.

        After calling this method, the simulator will need to be set up again.
        """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def start_data_traffic(self):
        """Starts transmitting data from the instrument to the DUT. """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')

    def stop_data_traffic(self):
        """Stops transmitting data from the instrument to the DUT. """
        raise NotImplementedError(
            'This UXM callbox simulator does not support this feature.')
