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


class NrCellConfig(base_cell.BaseCellConfig):
    """ NR cell configuration class.

    Attributes:
    """
    def __init__(self, log):
        """ Initialize the base station config by setting all its
        parameters to None. """
        super().__init__(log)

    def configure(self, parameters):
        """ Configures an NR cell using a dictionary of parameters.

        Args:
            parameters: a configuration dictionary
        """
        raise NotImplementedError()
