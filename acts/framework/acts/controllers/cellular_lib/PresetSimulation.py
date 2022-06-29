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
import time

from acts.controllers.cellular_lib.BaseSimulation import BaseSimulation
from acts.controllers.cellular_lib import BaseCellularDut


class PresetSimulation(BaseSimulation):
    """5G preset simulation.

    The simulation will be configed by importing SCPI config file
    instead of individually set params.
    """

    def __init__(self,
                 simulator,
                 log,
                 dut,
                 test_config,
                 calibration_table,
                 nr_mode=None):
        """Initializes the simulator for 5G preset simulation.

        Args:
            simulator: a cellular simulator controller.
            log: a logger handle.
            dut: a device handler implementing BaseCellularDut.
            test_config: test configuration obtained from the config file.
            calibration_table: a dictionary containing path losses
                for different bands.
        """

        super().__init__(simulator, log, dut, test_config, calibration_table,
                         nr_mode)

        # Set to KeySight APN
        log.info('Configuring APN.')
        self.dut.set_apn('Keysight', 'Keysight')
        self.num_carriers = None

        # Force device to LTE only so that it connects faster
        try:
            self.dut.set_preferred_network_type(
                BaseCellularDut.PreferredNetworkType.NR_LTE)
        except Exception as e:
            # If this fails the test should be able to run anyways, even if it
            # takes longer to find the cell.
            self.log.warning('Setting preferred RAT failed: ' + str(e))

    def setup_simulator(self):
        """Do initial configuration in the simulator. """
        self.log.info('This simulation does not require initial setup.')

    def configure(self, parameters):
        """Configures simulation by importing scpi file.

        A pre-made SCPI file include all the essential configuration
        for the simulation is imported by send SCPI import command
        to the callbox.

        Args:
            parameters: a configuration dictionary which includes scpi file path
                if there is only one carrier, a list if there are multiple cells.
        """
        self.simulator.import_configuration(parameters[0]['scpi_file'])
        self.simulator.set_cell_type(parameters[0]['cell_type'])
        self.simulator.set_cell_number(parameters[0]['cell_number'])

    def start(self):
        """Start simulation.

        Waiting for the DUT to connect to the callbox.
        """

        if not self.attach():
            raise RuntimeError('Could not attach to base station.')

    def attach(self):
        """Attach UE to the callbox.

        Toggle airplane mode on-off and wait for a specified timeout,
        repeat until the UE connect to the callbox.
        """
        # airplane mode on
        self.dut.toggle_airplane_mode(True)
        time.sleep(5)
        # turn cell on
        self.simulator.turn_cell_on()
        time.sleep(5)
        # airplane mode off
        self.dut.toggle_airplane_mode(False)

        # waits for connect
        for index in range(20):
            time.sleep(60)
            cell_state = self.simulator.get_cell_status()
            self.log.info(f'cell state: {cell_state}')
            if cell_state == 'CONN\n':
                return True
            elif (index % 15) == 0:
                # airplane mode on
                self.dut.toggle_airplane_mode(True)
                time.sleep(5)
                # airplane mode off
                self.dut.toggle_airplane_mode(False)
            elif (index % 30) == 29:
                self.dut.reboot()
        return False

    def calibrated_downlink_rx_power(self, bts_config, rsrp):
        """Convert RSRP to total signal power from the basestation.

        Args:
            bts_config: the current configuration at the base station
            rsrp: desired rsrp, contained in a key value pair
        """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def downlink_calibration(self, rat=None, power_units_conversion_func=None):
        """Computes downlink path loss and returns the calibration value.

        See base class implementation for details.

        Args:
            rat: ignored, replaced by 'lteRsrp'.
            power_units_conversion_func: ignored, replaced by
                self.rsrp_to_signal_power.

        Returns:
            Downlink calibration value and measured DL power. Note that the
            phone only reports RSRP of the primary chain
        """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def rsrp_to_signal_power(self, rsrp, bts_config):
        """Converts rsrp to total band signal power

        RSRP is measured per subcarrier, so total band power needs to be
        multiplied by the number of subcarriers being used.

        Args:
            rsrp: desired rsrp in dBm.
            bts_config: a base station configuration object.

        Returns:
            Total band signal power in dBm
        """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def maximum_downlink_throughput(self):
        """Calculates maximum achievable downlink throughput in.

        The calculation is based on the current simulation state
        Returns:
            Maximum throughput in mbps.
        """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def bts_maximum_downlink_throughtput(self, bts_config):
        """Calculates maximum achievable downlink throughput for a single

        base station from its configuration object.

        Args:
            bts_config: a base station configuration object.

        Returns:
            Maximum throughput in mbps.
        """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def maximum_uplink_throughput(self):
        """Calculates maximum achievable uplink throughput.

        Returns:
            Maximum throughput in mbps.
        """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def bts_maximum_uplink_throughtput(self, bts_config):
        """Calculates maximum achievable uplink throughput

        The calculation is for selected basestation
        from its configuration object.
        Args:
            bts_config: an LTE base station configuration object.

        Returns:
            Maximum throughput in mbps.

        """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def calibrate(self, band):
        """Calculates UL and DL path loss if it wasn't done before

        Before running the base class implementation, configure the base station
        to only use one downlink antenna with maximum bandwidth.

        Args:
            band: the band that is currently being calibrated.
        """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def start_traffic_for_calibration(self):
        """If MAC padding is enabled, there is no need to start IP traffic. """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def stop_traffic_for_calibration(self):
        """If MAC padding is enabled, IP traffic wasn't started. """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')

    def get_measured_ul_power(self, samples=5, wait_after_sample=3):
        """Calculates UL power.

        The calculation is based on measurements from the callbox
        and the calibration data.
        Args:
            samples: the numble of samples to average
            wait_after_sample: time in seconds to wait in between samples

        Returns:
            the ul power at the UE antenna ports in dBs
        """
        raise NotImplementedError(
            'This simulation mode does not support this configuration option')
