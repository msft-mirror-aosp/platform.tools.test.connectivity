#!/usr/bin/env python3
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

import acts.controllers.cellular_lib.BaseCellConfig as base_cell
import acts.controllers.cellular_lib.LteSimulation as lte_sim


class NrCellConfig(base_cell.BaseCellConfig):
    """ NR cell configuration class.

    Attributes:
        band: an integer indicating the required band number.
        bandwidth: a integer indicating the required channel bandwidth
    """

    PARAM_BAND = "band"
    PARAM_BW = "bw"
    PARAM_DL_MCS = "dlmcs"
    PARAM_DL_RBS = "dl_rbs"
    PARAM_PADDING = "mac_padding"
    PARAM_MIMO = "mimo"
    PARAM_NRARFCN = "nr_arfcn"
    PARAM_SCHEDULING = "scheduling"
    PARAM_SCHEDULING_DYNAMIC = "dynamic"
    PARAM_SCHEDULING_STATIC = "static"
    PARAM_UL_MCS = "ulmcs"
    PARAM_UL_RBS = "ul_rbs"
    PARAM_TA = "tracking_area"
    PARAM_DRX = "drx"
    PARAM_DISABLE_ALL_UL_SLOTS = "disable_all_ul_slots"
    PARAM_CONFIG_FLEXIBLE_SLOTS = "config_flexible_slots"

    def __init__(self, log):
        """ Initialize the base station config by setting all its
        parameters to None.
        Args:
            log: logger object.
        """
        super().__init__(log)
        self.band = None
        self.bandwidth = None
        self.dl_rbs = None
        self.ul_rbs = None
        self.dl_mcs = None
        self.ul_mcs = None
        self.mac_padding = None
        self.mimo_mode = None
        self.nr_arfcn = None
        self.drx_connected_mode = None
        self.disable_all_ul_slots = None
        self.config_flexible_slots = None

    def configure(self, parameters):
        """ Configures an NR cell using a dictionary of parameters.

        Args:
            parameters: a configuration dictionary
        """
        if self.PARAM_BAND not in parameters:
            raise ValueError(
                "The configuration dictionary must include a key '{}' with "
                "the required band number.".format(self.PARAM_BAND))
        nr_band = parameters[self.PARAM_BAND]
        if nr_band[0] == 'n':
            nr_band = nr_band[1:]
        self.band = nr_band

        if self.PARAM_NRARFCN in parameters:
            self.nr_arfcn = int(parameters[self.PARAM_NRARFCN])

        if self.PARAM_BW not in parameters:
            raise ValueError(
                "The config dictionary must include parameter {} with an "
                "int value (to indicate 1.4 MHz use 14).".format(
                    self.PARAM_BW))
        bw = float(parameters[self.PARAM_BW])

        if abs(bw - 14) < 0.00000000001:
            bw = 1.4

        self.bandwidth = bw

        if self.PARAM_TA in parameters:
            self.tracking_area = int(parameters[self.PARAM_TA])
        else:
            self.tracking_area = None

        # Setup mimo mode
        if self.PARAM_MIMO not in parameters:
            raise ValueError(
                "The config dictionary must include parameter '{}' with the "
                "mimo mode.".format(self.PARAM_MIMO))

        for mimo_mode in lte_sim.MimoMode:
            if parameters[self.PARAM_MIMO] == mimo_mode.value:
                self.mimo_mode = mimo_mode
                break
        else:
            raise ValueError("The value of {} must be one of the following:"
                             "1x1, 2x2 or 4x4.".format(self.PARAM_MIMO))

        if self.PARAM_SCHEDULING not in parameters:
            self.scheduling_mode = lte_sim.SchedulingMode.STATIC
            self.log.warning(
                "The test config does not include the '{}' key. Setting to "
                "static by default.".format(self.PARAM_SCHEDULING))
        elif parameters[
                self.PARAM_SCHEDULING] == self.PARAM_SCHEDULING_DYNAMIC:
            self.scheduling_mode = lte_sim.SchedulingMode.DYNAMIC
        elif parameters[self.PARAM_SCHEDULING] == self.PARAM_SCHEDULING_STATIC:
            self.scheduling_mode = lte_sim.SchedulingMode.STATIC
        else:
            raise ValueError("Key '{}' must have a value of "
                             "'dynamic' or 'static'.".format(
                                 self.PARAM_SCHEDULING))

        if self.scheduling_mode == lte_sim.SchedulingMode.STATIC:

            if self.PARAM_PADDING not in parameters:
                self.log.warning(
                    "The '{}' parameter was not set. Enabling MAC padding by "
                    "default.".format(self.PARAM_PADDING))
                self.mac_padding = True
            else:
                self.mac_padding = parameters[self.PARAM_PADDING]

            if self.PARAM_DL_MCS in parameters:
                self.dl_mcs = int(parameters[self.PARAM_DL_MCS])

            if self.PARAM_UL_MCS in parameters:
                self.ul_mcs = int(parameters[self.PARAM_UL_MCS])

            # Temproraily setting: set 273 for bandwidth of 100 MHz
            self.dl_rbs = 273
            self.ul_rbs = 273

        self.disable_all_ul_slots = parameters.get(
            self.PARAM_DISABLE_ALL_UL_SLOTS, False)
        self.config_flexible_slots = parameters.get(
            self.PARAM_CONFIG_FLEXIBLE_SLOTS, False)

    def __str__(self):
        return str(vars(self))
