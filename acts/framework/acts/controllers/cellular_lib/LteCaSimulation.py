#!/usr/bin/env python3
#
#   Copyright 2018 - The Android Open Source Project
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
import re
from acts.controllers.cellular_lib import LteSimulation


class LteCaSimulation(LteSimulation.LteSimulation):
    """ Carrier aggregation LTE simulation. """

    # Test config keywords
    KEY_FREQ_BANDS = "freq_bands"

    def __init__(self, simulator, log, dut, test_config, calibration_table):
        """ Initializes the simulator for LTE simulation with carrier
        aggregation.

        Loads a simple LTE simulation environment with 5 basestations.

        Args:
            simulator: the cellular instrument controller
            log: a logger handle
            dut: a device handler implementing BaseCellularDut
            test_config: test configuration obtained from the config file
            calibration_table: a dictionary containing path losses for
                different bands.

        """

        super().__init__(simulator, log, dut, test_config, calibration_table)

        # Create a configuration object for each base station and copy initial
        # settings from the PCC base station.
        self.bts_configs = [self.primary_config]

        for bts_index in range(1, self.simulator.LTE_MAX_CARRIERS):
            new_config = self.BtsConfig()
            new_config.incorporate(self.primary_config)
            self.simulator.configure_bts(new_config, bts_index)
            self.bts_configs.append(new_config)

        # Get LTE CA frequency bands setting from the test configuration
        if self.KEY_FREQ_BANDS not in test_config:
            self.log.warning("The key '{}' is not set in the config file. "
                             "Setting to null by default.".format(
                                 self.KEY_FREQ_BANDS))

        self.freq_bands = test_config.get(self.KEY_FREQ_BANDS, True)

    def configure(self, parameters):
        """ Configures PCC and SCCs using a dictionary of parameters.

        Args:
            parameters: a list of configuration dictionaris
        """
        new_cell_list = []
        for cell in parameters:
            if self.PARAM_BAND not in cell:
                raise ValueError(
                    "The configuration dictionary must include a key '{}' with "
                    "the required band number.".format(self.PARAM_BAND))

            band = cell[self.PARAM_BAND]

            if isinstance(band, str) and not band.isdigit():
                ca_class = band[-1].upper()
                band_num = int(band[:-1])

                if ca_class in ['A', 'C']:
                    # Remove the CA class label and add the cell
                    cell[self.PARAM_BAND].band = band_num
                    new_cell_list.append(cell)
                elif ca_class == 'B':
                    raise RuntimeError('Class B LTE CA not supported.')
                else:
                    raise ValueError('Invalid band value: ' + band)

                # Class C means that there are two contiguous carriers
                if ca_class == 'C':
                    new_cell_list.append(cell)
                    bw = int(cell[self.PARAM_BW])
                    new_cell_list[-1].dl_earfcn = int(
                        self.LOWEST_DL_CN_DICTIONARY[band_num] + bw * 10 - 2)
            else:
                # The band is just a number, so just add it to the list.
                new_cell_list.append(cell)

        self.simulator.set_band_combination(
            [c[self.PARAM_BAND] for c in new_cell_list])

        self.num_carriers = len(new_cell_list)

        # Setup the base station with the obtained configuration and then save
        # these parameters in the current configuration object
        for bts_index in range(self.num_carriers):
            cell_config = self.configure_lte_cell(parameters[bts_index])
            self.simulator.configure_bts(cell_config, bts_index)
            self.bts_configs[bts_index].incorporate(cell_config)

        # Now that the band is set, calibrate the link if necessary
        self.load_pathloss_if_required()

        # Get uplink power from primary carrier
        ul_power = self.get_uplink_power_from_parameters(parameters[0])

        # Power is not set on the callbox until after the simulation is
        # started. Saving this value in a variable for later
        self.sim_ul_power = ul_power

        # Get downlink power from primary carrier
        dl_power = self.get_downlink_power_from_parameters(parameters[0])

        # Power is not set on the callbox until after the simulation is
        # started. Saving this value in a variable for later
        self.sim_dl_power = dl_power

        # Now that the band is set, calibrate the link for the PCC if necessary
        self.load_pathloss_if_required()

    def maximum_downlink_throughput(self):
        """ Calculates maximum downlink throughput as the sum of all the active
        carriers.
        """
        return sum(
            self.bts_maximum_downlink_throughtput(self.bts_configs[bts_index])
            for bts_index in range(self.num_carriers))

    def start(self):
        """ Set the signal level for the secondary carriers, as the base class
        implementation of this method will only set up downlink power for the
        primary carrier component.

        After that, attaches the secondary carriers."""

        super().start()

        if self.sim_dl_power:
            self.log.info('Setting DL power for secondary carriers.')

            for bts_index in range(1, self.num_carriers):
                new_config = self.BtsConfig()
                new_config.output_power = self.calibrated_downlink_rx_power(
                    self.bts_configs[bts_index], self.sim_dl_power)
                self.simulator.configure_bts(new_config, bts_index)
                self.bts_configs[bts_index].incorporate(new_config)

        self.simulator.lte_attach_secondary_carriers(self.freq_bands)
