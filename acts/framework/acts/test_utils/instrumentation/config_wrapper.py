#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
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

import collections
import copy


class InvalidParamError(Exception):
    pass


def _is_dict(o):
    return isinstance(o, dict) or isinstance(o, collections.UserDict)


class ConfigWrapper(collections.UserDict):
    """Class representing a test or preparer config."""

    def __init__(self, config=None):
        """Initialize a ConfigWrapper

        Args:
            config: A dict representing the preparer/test parameters
        """
        if config is None:
            config = {}
        super().__init__(
            {
                key: (ConfigWrapper(val) if _is_dict(val) else val)
                for key, val in config.items()
            }
        )

    def get(self, param_name, default=None, verify_fn=lambda _: True,
            failure_msg=''):
        """Get parameter from config, verifying that the value is valid
        with verify_fn.

        Args:
            param_name: Name of the param to fetch
            default: Default value of param.
            verify_fn: Callable to verify the param value. If it returns False,
                an exception will be raised.
            failure_msg: Exception message upon verify_fn failure.
        """
        result = self.data.get(param_name, default)
        if not verify_fn(result):
            raise InvalidParamError('Invalid value "%s" for param %s. %s'
                                    % (result, param_name, failure_msg))
        return result

    def get_config(self, param_name):
        """Get a sub-config from config. Returns an empty ConfigWrapper if no
        such sub-config is found.
        """
        return ConfigWrapper(copy.deepcopy(self.get(param_name, default={})))

    def get_int(self, param_name, default=0):
        """Get integer parameter from config. Will raise an exception
        if result is not of type int.
        """
        return self.get(param_name, default=default,
                        verify_fn=lambda val: type(val) is int,
                        failure_msg='Param must be of type int.')

    def get_numeric(self, param_name, default=0):
        """Get int or float parameter from config. Will raise an exception if
        result is not of type int or float.
        """
        return self.get(param_name, default=default,
                        verify_fn=lambda val: type(val) in (int, float),
                        failure_msg='Param must be of type int or float.')


def merge(config_a, config_b):
    """Merges dic_b into dic_a

    Recursively updates the fields of config_a with the value that comes from
    config_b.

    For example:
    config_a = {'dic': {'a': 0, 'c': 3, 'sub': {'x': 1}}}
    config_b = {'dic': {'a': 2, 'b': 2, 'sub': {'y': 2}}}

    would result in
    {'dic': {'a': 2, 'b': 2, 'c': 3, 'sub': {'x': 1, 'y': 2}}}

    Args:
         config_a: A ConfigWrapper
         config_b: A ConfigWrapper
    Return:
        A ConfigWrapper.
    """
    res = collections.UserDict(config_a)
    for (key, value) in config_b.items():
        if key in res and _is_dict(res[key]):
            res[key] = merge(res[key], value)
        else:
            res[key] = copy.deepcopy(value)
    return ConfigWrapper(res)





