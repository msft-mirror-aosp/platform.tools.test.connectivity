#!/usr/bin python3
#
#   Copyright 2019 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""Python module for Spectracom/Orolia GSG-6 GNSS simulator."""

import acts.controllers.gnssinst_lib.abstract_inst as abstract_inst


class GSG6Error(abstract_inst.SocketInstrumentError):
    """GSG-6 Instrument Error Class."""

    def __init__(self, error, command=None):
        """Init method for GSG-6 Error.

        Args:
            error: Exception error.
            command: Additional information on command,
                Type, Str.
        """
        super(GSG6Error, self).__init__(error)


class GSG6(abstract_inst.SocketInstrument):
    """GSG-6 Class, inherted from abstract_inst SocketInstrument."""

    def __init__(self, ip_addr, ip_port):
        """Init method for GSG-6.

        Args:
            ip_addr: IP Address.
                Type, str.
            ip_port: TCPIP Port.
                Type, str.
        """
        super(GSG6, self).__init__(ip_addr, ip_port)

        self.idn = ''

    def connect(self):
        """Init and Connect to GSG-6."""
        self._connect_socket()

        self.get_idn()

        infmsg = 'Connected to GSG-6, with ID: {}'.format(self.idn)
        self._logger.info(infmsg)

    def close(self):
        """Close GSG-6."""
        self._close_socket()

        infmsg = 'Closed connection to GSG-6'
        self._logger.info(infmsg)

    def get_idn(self):
        """Get the Idenification of GSG-6.

        Returns:
            GSG-6 Identifier
        """
        self.idn = self._query('*IDN?')

        return self.idn

    def start_scenario(self, scenario=''):
        """Start to run scenario.

        Args:
            scenario: Scenario to run.
                Type, str.
                Default, '', which will run current selected one.
        """
        if scenario:
            cmd = 'SOUR:SCEN:LOAD ' + scenario
            self._send(cmd)

        self._send('SOUR:SCEN:CONT START')

        if scenario:
            infmsg = 'Started running scenario {}'.format(scenario)
        else:
            infmsg = 'Started running current scenario'

        self._logger.info(infmsg)

    def stop_scenario(self):
        """Stop the running scenario."""

        self._send('SOUR:SCEN:CONT STOP')

        infmsg = 'Stopped running scenario'
        self._logger.info(infmsg)
