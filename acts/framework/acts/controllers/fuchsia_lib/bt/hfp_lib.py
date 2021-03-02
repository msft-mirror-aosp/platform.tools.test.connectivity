#!/usr/bin/env python3
#
#   Copyright 2021 - The Android Open Source Project
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

from acts.controllers.fuchsia_lib.base_lib import BaseLib


class FuchsiaHfpLib(BaseLib):
    def __init__(self, addr, tc, client_id):
        self.address = addr
        self.test_counter = tc
        self.client_id = client_id

    def init(self):
        """Initializes the HFP service.

        Returns:
            Dictionary, None if success, error if error.
        """
        test_cmd = "hfp_facade.HfpInit"

        test_args = {}
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def removeService(self):
        """Removes the HFP service from the Fuchsia device

        Returns:
            Dictionary, None if success, error if error.
        """
        test_cmd = "hfp_facade.HfpRemoveService"
        test_args = {}
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def listPeers(self):
        """List all connected HFP peer devices.

        Returns:
            Dictionary, None if success, error if error.
        """
        test_cmd = "hfp_facade.ListPeers"
        test_args = {}
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def setActivePeer(self, peer_id):
        """Set the active HFP peer device. All peer specific commands will be
        directed to this device.

        Args:
            peer_id: The id of the peer to set as active. Use "listPeers" to
            find connected peer ids.

        Returns:
            Dictionary, None if success, error if error.
        """
        test_cmd = "hfp_facade.SetActivePeer"
        test_args = { "peer_id": peer_id }
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def listCalls(self):
        """List all calls known to the sl4f component.

        Returns:
            Dictionary, None if success, error if error.
        """
        test_cmd = "hfp_facade.ListCalls"
        test_args = {}
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def initiateIncomingCall(self, remote):
        """Opens an incoming call channel and alerts the HFP peer.

        Args:
            remote: The number of the remote party.

        Returns:
            Dictionary, call_id if success, error if error.
        """
        test_cmd = "hfp_facade.IncomingCall"
        test_args = {"remote": remote }
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def initiateOutgoingCall(self, remote):
        """Opens an outgoing call channel and alerts the HFP peer.

        Args:
            remote: The number of the remote party.

        Returns:
            Dictionary, call_id if success, error if error.
        """
        test_cmd = "hfp_facade.OutgoingCall"
        test_args = {"remote": remote }
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def setCallActive(self, call_id):
        """Sets the specified call to the "OngoingActive" state.

        Args:
            call_id: The unique id of the call.

        Returns:
            Dictionary, None if success, error if error.
        """
        test_cmd = "hfp_facade.SetCallActive"
        test_args = {"call_id": call_id }
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def setCallHeld(self, call_id):
        """Sets the specified call to the "OngoingHeld" state.

        Args:
            call_id: The unique id of the call.

        Returns:
            Dictionary, None if success, error if error.
        """
        test_cmd = "hfp_facade.SetCallHeld"
        test_args = {"call_id": call_id }
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def setCallTerminated(self, call_id):
        """Sets the specified call to the "Terminated" state.

        Args:
            call_id: The unique id of the call.

        Returns:
            Dictionary, None if success, error if error.
        """
        test_cmd = "hfp_facade.SetCallTerminated"
        test_args = {"call_id": call_id }
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)

    def setCallTransferredToAg(self, call_id):
        """Sets the specified call to the "TransferredToAg" state.

        Args:
            call_id: The unique id of the call.

        Returns:
            Dictionary, None if success, error if error.
        """
        test_cmd = "hfp_facade.SetCallTransferredToAg"
        test_args = {"call_id": call_id }
        test_id = self.build_id(self.test_counter)
        self.test_counter += 1

        return self.send_command(test_id, test_cmd, test_args)
