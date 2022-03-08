#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
import re
from acts import signals

SVID_RANGE = {
    'GPS': [(1, 32)],
    'SBAS': [(120, 192)],
    'GLO': [(1, 24), (93, 106)],
    'QZS': [(193, 200)],
    'BDS': [(1, 63)],
    'GAL': [(1, 36)],
    'NIC': [(1, 14)]
}


def parse_gnssstatus(line, ad):
    """Parse gnssstatus with given raw line.

    Args:
        line: A string identify the gnssstatus raw line
        ad: An android device obj
    """
    gnss_status_obj = GnssStatus(line)
    test_res = gnss_status_obj.get_gnssstatus_health()
    if test_res != '':
        ad.log.info(line)
        raise signals.TestFailure('Gnsstatus validate failed:\n%s' % test_res)


class GnssStatus:
    """GnssStatus object, it will create an obj with a raw gnssstatus line."""
    gnssstatus_re = (r'Type: (.*) SV: (.*) C/No: (.*), (.*) Elevation: (.*) '
                     r'Azimuth: (.*) Signal')
    failures = []

    def __init__(self, gnssstatus_raw):
        status_res = re.search(self.gnssstatus_re, gnssstatus_raw)
        if not status_res:
            raise signals.TestFailure('Fail to create GnssStatus obj: %s' %
                                    gnssstatus_raw)
        self.sv = status_res.group(1)
        self.svid = int(status_res.group(2))
        self.cn = float(status_res.group(3))
        self.base_cn = float(status_res.group(4))
        self.elev = float(status_res.group(5))
        self.azim = float(status_res.group(6))
        self._validate_gnssstatus()

    def _validate_gnssstatus(self):
        """A validate function for each property."""
        self._validate_sv()
        self._validate_cn()
        self._validate_elev()
        self._validate_azim()

    def _validate_sv(self):
        """A validate function for SV ID."""
        if not SVID_RANGE.get(self.sv):
            raise signals.TestError('Satellite identify fail: %s' % self.sv)

        for id_range in SVID_RANGE[self.sv]:
            if id_range[0] <= self.svid <= id_range[1]:
                break
        else:
            fail_details = '%s ID %s not in SV Range' % (self.sv, self.svid)
            self.failures.append(fail_details)

    def _validate_cn(self):
        """A validate function for CN value."""
        if not 0 <= self.cn <= 63:
            self.failures.append('Ant CN not in range: %s' % self.cn)
        if not 0 <= self.base_cn <= 63:
            self.failures.append('Base CN not in range: %s' % self.cn)

    def _validate_elev(self):
        """A validate function for Elevation (should between 0-90)."""
        if not 0 <= self.elev <= 90:
            self.failures.append('Elevation not in range: %s' % self.elev)

    def _validate_azim(self):
        """A validate function for Azimuth (should between 0-360)."""
        if not 0 <= self.azim <= 360:
            self.failures.append('Azimuth not in range: %s' % self.azim)

    def get_gnssstatus_health(self):
        """A function return the obj property health state

           Return: Failure msg or blank.
        """
        gnss_health_info = '\n'.join(self.failures)
        return gnss_health_info
