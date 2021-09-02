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
Python module for Spirent GSS7000 GNSS simulator.
@author: Clay Liao (jianhsiungliao@)
"""
from time import sleep
import xml.etree.ElementTree as ET
from acts.controllers import abstract_inst


def get_xml_text(xml_string='', tag=''):
    """Parse xml from string and return specific tag

        Args:
            xml_string: xml string,
                Type, Str.
            tag: tag in xml,
                Type, Str.

        Returns:
            text: Text content in the tag
                Type, Str.
        """
    if xml_string and tag:
        root = ET.fromstring(xml_string)
        try:
            text = str(root.find(tag).text).rstrip().lstrip()
        except ValueError:
            text = 'INVALID DATA'
    else:
        text = 'INVALID DATA'
    return text


class GSS7000Error(abstract_inst.SocketInstrumentError):
    """GSS7000 Instrument Error Class."""


class AbstractInstGss7000(abstract_inst.SocketInstrument):
    """Abstract instrument for  GSS7000"""

    def _query(self, cmd):
        """query instrument via Socket.

        Args:
            cmd: Command to send,
                Type, Str.

        Returns:
            resp: Response from Instrument via Socket,
                Type, Str.
        """
        self._send(cmd)
        self._wait()
        resp = self._recv()
        return resp

    def _wait(self, wait_time=1):
        """wait function
        Args:
            wait_time: wait time in sec.
                Type, int,
                Default, 1.
        """
        sleep(wait_time)


class GSS7000Ctrl(AbstractInstGss7000):
    """GSS7000 control daemon class"""

    def __init__(self, ip_addr, ip_port=7717):
        """Init method for GSS7000 Control Daemon.

        Args:
            ip_addr: IP Address.
                Type, str.
            ip_port: TCPIP Port.
                Type, str.
        """
        super().__init__(ip_addr, ip_port)
        self.idn = 'Spirent-GSS7000 Control Daemon'

    def connect(self):
        """Init and Connect to GSS7000 Control Daemon."""
        # Connect socket then connect socket again
        self._close_socket()
        self._connect_socket()
        # Stop GSS7000 Control Daeamon Then Start
        self._query('STOP_ENGINE')
        self._wait()
        self._query('START_ENGINE')

    def close(self):
        """Close GSS7000 control daemon"""
        self._close_socket()
        self._logger.debug('Closed connection to GSS7000 control daemon')


class GSS7000(AbstractInstGss7000):
    """GSS7000 Class, inherted from abstract_inst SocketInstrument."""

    def __init__(self, ip_addr, engine_ip_port=15650, ctrl_ip_port=7717):
        """Init method for GSS7000.

        Args:
            ip_addr: IP Address.
                Type, str.
            engine_ip_port: TCPIP Port for
                Type, str.
            ctrl_ip_port: TCPIP Port for Control Daemon
        """
        super().__init__(ip_addr, engine_ip_port)
        self.idn = ''
        self.connected = False
        self.gss7000_ctrl_daemon = GSS7000Ctrl(ip_addr, ctrl_ip_port)
        # Close control daemon and engine sockets at the beginning
        self.gss7000_ctrl_daemon._close_socket()
        self._close_socket()

    def connect(self):
        """Connect GSS7000 engine daemon"""
        # Connect control daemon socket
        self._logger.debug('Connect to GSS7000')
        self.gss7000_ctrl_daemon.connect()
        # Connect to remote engine socket
        self._wait()
        self._connect_socket()
        self.connected = True
        self.get_hw_capability()

    def close(self):
        """Close GSS7000 engine daemon"""
        # Close GSS7000 control daemon
        self.gss7000_ctrl_daemon.close()
        # Close GSS7000 engine daemon
        self._close_socket()
        self._logger.debug('Closed connection to GSS7000 engine daemon')

    def _parse_hw_cap(self, xml):
        """Parse GSS7000 hardware capability xml to dict.
            Args:
                xml: hardware capability xml,
                    Type, str.
            Returns:
                capability: Hardware capability dictionary
                    Type, dict.
        """
        root = ET.fromstring(xml)
        capability_dict = dict()
        sig_cap_list = root.find('data').find('Signal_capabilities').findall(
            'Signal')
        for signal in sig_cap_list:
            key = signal.attrib['ID']
            value = str(signal.text).rstrip().lstrip()
            capability_dict.setdefault(key, value)
        return capability_dict

    def get_hw_capability(self):
        """Check GSS7000 hardware capability

            Returns:
                capability: Hardware capability dictionary,
                    Type, dict.
        """
        if self.connected:
            capability_xml = self._query('GET_LICENCED_HARDWARE_CAPABILITY')
            capability = self._parse_hw_cap(capability_xml)

        else:
            capability = dict()
        self._logger.debug(capability)
        return capability

    def get_idn(self):
        """Get the SimREPLAYplus Version

        Returns:
            SimREPLAYplus Version
        """
        idn_xml = self._query('*IDN?')
        self.idn = get_xml_text(idn_xml, 'data')
        return self.idn

    def load_scenario(self, scenario=''):
        """Load the scenario.

        Args:
            scenario: path of scenario,
                Type, str
        """
        if scenario == '':
            errmsg = ('Missing scenario file')
            raise GSS7000Error(error=errmsg, command='load_scenario')
        else:
            self._logger.debug('Stopped the original scenario')
            self._query('-,EN,1')
            cmd = 'SC,' + scenario
            self._logger.debug('Loading scenario')
            self._query(cmd)
            self._logger.debug('Scenario is loaded')
            return True
        return False

    def start_scenario(self, scenario=''):
        """Load and Start the running scenario.

        Args:
            scenario: path of scenario,
                Type, str
        """
        if scenario:
            if self.load_scenario(scenario):
                self._query('RU')
            else:
                infmsg = 'No scenario is loaded. Stop running scenario'
                self._logger.debug(infmsg)
        else:
            pass

        if scenario:
            infmsg = 'Started running scenario {}'.format(scenario)
        else:
            infmsg = 'Started running current scenario'

        self._logger.debug(infmsg)

    def get_scenario_name(self):
        """Get current scenario name"""
        sc_name_xml = self._query('SC_NAME')
        return get_xml_text(sc_name_xml, 'data')

    def stop_scenario(self):
        """Stop the running scenario."""
        self._query('-,EN,1')
        self._logger.debug('Stopped running scenario')

    def set_power_offset(self, ant=1, power_offset=0):
        """Set Power Offset of GSS7000 Tx
        Args:
            ant: antenna number of GSS7000
            power_offset: transmit power offset level
                Type, float.
                Decimal, unit [dB]

        Raises:
            GSS7000Error: raise when power offset level is not in [-40, 15] range.
        """
        if not -40 <= power_offset <= 15:
            errmsg = ('"power_offset" must be within [-40, 15], '
                      'current input is {}').format(str(power_offset))
            raise GSS7000Error(error=errmsg, command='set_power_offset')

        cmd = '-,POW_LEV,V1_A{},{},GPS,0,0,1,1,1,1,0'.format(
            str(ant), str(round(power_offset, 1)))
        self._query(cmd)

        infmsg = 'Set veichel 1 antenna {} power offset: {}'.format(
            str(ant), str(round(power_offset, 1)))
        self._logger.debug(infmsg)

    def set_ref_power(self, ref_dBm=-130):
        """Set Ref Power of GSS7000 Tx
        Args:
            ref_dBm: transmit reference power level in dBm for GSS7000
                Type, float.
                Decimal, unit [dBm]

        Raises:
            GSS7000Error: raise when power offset level is not in [-170, -115] range.
        """
        if not -170 <= ref_dBm <= -115:
            errmsg = ('"power_offset" must be within [-170, -115], '
                      'current input is {}').format(str(ref_dBm))
            raise GSS7000Error(error=errmsg, command='set_ref_power')
        cmd = 'REF_DBM,{}'.format(str(round(ref_dBm, 1)))
        self._query(cmd)
        infmsg = 'Set reference power level: {}'.format(str(round(ref_dBm, 1)))
        self._logger.debug(infmsg)

    def get_status(self, return_txt=False):
        """Get current GSS7000 Status
        Args:
            return_txt: booling for determining the return results
                Type, booling.
        """
        status_xml = self._query('NULL')
        status = get_xml_text(status_xml, 'status')
        if return_txt:
            status_dict = {
                '0':
                    'No Scenario loaded',
                '1':
                    'Not completed loading a scenario',
                '2':
                    'Idle, ready to run a scenario',
                '3':
                    'Arming the scenario',
                '4':
                    'Completed arming; or waiting for a command or'
                    'trigger signal to start the scenario',
                '5':
                    'Scenario running',
                '6':
                    'Current scenario is paused.',
                '7':
                    'Active scenario has stopped and has not been reset.'
                    'Waiting for further commands.'
            }
            return status_dict.get(status)
        else:
            return int(status)

    def set_power(self, power_level=-130):
        """Set Power Level of GSS7000 Tx
        Args:
            power_level: transmit power level
                Type, float.
                Decimal, unit [dBm]

        Raises:
            GSS7000Error: raise when power level is not in [-170, -115] range.
        """
        if not -170 <= power_level <= -115:
            errmsg = ('"power_level" must be within [-170, -115], '
                      'current input is {}').format(str(power_level))
            raise GSS7000Error(error=errmsg, command='set_power')

        power_offset = power_level + 130
        self.set_power_offset(1, power_offset)
        self.set_power_offset(2, power_offset)

        infmsg = 'Set GSS7000 transmit power to "{}"'.format(
            round(power_level, 1))
        self._logger.debug(infmsg)
