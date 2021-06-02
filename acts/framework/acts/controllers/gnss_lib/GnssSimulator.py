#!/usr/bin/env python3
#
# Copyright (C) 2021 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Python module for General abstract GNSS Simulator.
@author: Clay Liao (jianhsiungliao@)
"""
from acts.controllers.spectracom_lib import gsg6
from acts.controllers.spirent_lib import gss7000
from acts import logger


class AbstractGnssSimulator:
    """General abstract GNSS Simulator"""

    def __init__(self, simulator, ip_addr, ip_port, ip_port_ctrl=7717):
        """Init AbstractGnssSimulator

        Args:
            simulator: GNSS simulator name,
                Type, str
                Option 'gss7000/gsg6'
            ip_addr: IP Address.
                Type, str
            ip_port: TCPIP Port,
                Type, str
            ip_port_ctrl: TCPIP port,
                Type, int
                Default, 7717
        """
        self.simulator_name = str(simulator).lower()
        self.ip_addr = ip_addr
        self.ip_port = ip_port
        self.ip_port_ctrl = ip_port_ctrl
        self._logger = logger.create_tagged_trace_logger(
            '%s %s:%s' % (simulator, self.ip_addr, self.ip_port))
        if self.simulator_name == 'gsg6':
            self._logger.info('GNSS simulator is GSG6')
            self.simulator = gsg6.GSG6(self.ip_addr, self.ip_port)
        elif self.simulator_name == 'gss7000':
            self._logger.info('GNSS simulator is GSS7000')
            self.simulator = gss7000.GSS7000(self.ip_addr, self.ip_port,
                                             self.ip_port_ctrl)
        else:
            self._logger.error('No matched GNSS simulator')
            raise AttributeError(
                'The GNSS simulator in config file is {} which is not supported.'
                .format(self.simulator_name))

    def connect(self):
        """Connect to GNSS Simulator"""
        self._logger.debug('Connect to GNSS Simulator {}'.format(
            self.simulator_name.upper()))
        self.simulator.connect()

    def close(self):
        """Disconnect from GNSS Simulator"""
        self._logger.debug('Disconnect from GNSS Simulator {}'.format(
            self.simulator_name.upper()))
        self.simulator.close()

    def start_scenario(self, scenario=''):
        """Start the running scenario.

        Args:
            scenario: path of scenario,
                Type, str
        """
        self._logger.info('Start GNSS Scenario {}'.format(scenario))
        self.simulator.start_scenario(scenario)

    def stop_scenario(self):
        """Stop the running scenario."""
        self._logger.debug('Stop playing scenario')
        self.simulator.stop_scenario()

    def set_power(self, power_level=-130):
        """Set scenario power level.
        Args:
            power_level: target power level in dBm for gsg6 or gss7000,
                gsg6 power_level range is [-160, -65],
                gss7000 power_level range is [-170, -115]
                Type, float,
        """
        self.simulator.set_power(power_level)

    def set_power_offset(self, gss7000_ant=1, pwr_offset=0):
        """Set scenario power level offset based on reference level.
           The default reference level is -130dBm for GPS L1.
        Args:
            ant: target gss7000 RF port,
                Type, int
            pwr_offset: target power offset in dB,
                Type, float
        """
        if self.simulator_name == 'gsg6':
            power_level = -130 + pwr_offset
            self.simulator.set_power(power_level)
        elif self.simulator_name == 'gss7000':
            self.simulator.set_power_offset(gss7000_ant, pwr_offset)
        else:
            self._logger.error('No GNSS simulator is available')
