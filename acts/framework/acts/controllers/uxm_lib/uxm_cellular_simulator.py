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
import socket
import time

from acts.controllers.cellular_simulator import AbstractCellularSimulator


class UXMCellularSimulator(AbstractCellularSimulator):
    """A cellular simulator for UXM callbox. """
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

    def __init__(self, ip_address):
        """Initializes the cellular simulator.

        Args:
            ip_address: the ip address of dektop where Keysight Test Application
                is installed.
            port: port where Keysigh Test Application is listening for socket
                communication.
        """
        super().__init__()
        self.cell_type = None
        self.cell_number = None

        # connect to Keysight Test Application via socket
        self.socket = self._socket_connect(ip_address, self.UXM_PORT)
        self.check_socket_connection()
        self.timeout = 120

    def set_cell_type(self, cell_type):
        """Set cell type. """
        self.cell_type = cell_type

    def set_cell_number(self, cell_number):
        """Set the cell number. """
        self.cell_number = cell_number

    def turn_cell_on(self):
        """Turn UXM's cell on. """
        self._socket_send_SCPI_command(
            self.SCPI_CELL_ON_CMD.format(self.cell_type, self.cell_number))

    def turn_cell_off(self):
        """Turn UXM's cell off. """
        self._socket_send_SCPI_command(
            self.SCPI_CELL_OFF_CMD.format(self.cell_type, self.cell_number))

    def get_cell_status(self):
        """Get status of cell. """
        return self._socket_send_SCPI_for_result_command(
            self.SCPI_GET_CELL_STATUS.format(self.cell_type, self.cell_number))

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
            path: path to SCPI config file
        """
        self.import_configuration(path)

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

    def wait_until_attached(self, timeout=120):
        """Waits until the DUT is attached to the primary carrier.

        Args:
            timeout: after this amount of time the method will raise a
                CellularSimulatorError exception. Default is 120 seconds.
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
        self._socket_send_SCPI_command(
            self.SCPI_CELL_OFF_CMD.format(self.cell_type, self.cell_number))

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
