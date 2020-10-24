def setup_policy_tests(fuchsia_devices):
    """ Preserve networks already saved on devices before removing them to
        setup up for a clean test environment. Initialize the client controller
        and enable connections.
    Args:
        fuchsia_device: the devices under test
    Returns:
        A dict of the networks that were saved on the device, indexed by the device
    """
    preserved_saved_networks = {}
    for fd in fuchsia_devices:
        fd.wlan_policy_lib.wlanCreateClientController()
        result_get = fd.wlan_policy_lib.wlanGetSavedNetworks()
        preserved_saved_networks[fd] = result_get['result']
        fd.wlan_policy_lib.wlanRemoveAllNetworks()
    return preserved_saved_networks


def restore_saved_networks(fuchsia_devices, preserved_networks):
    for fd in fuchsia_devices:
        for network in preserved_networks[fd]:
            save_network(fd, network["ssid"], network["security_type"],
                         network["credential_value"])


def save_network(fd, ssid, security_type, password=""):
    """ Saves a network as specified on the given device and verify that the operation succeeded.
        Returns true if there was an error, false otherwise
    Args:
        fd: The Fuchsia device to save the network on
        ssid: The SSID or name of the network to save.
        security_type: The security type to save the network as, ie "none",
                    "wep", "wpa", "wpa2", or "wpa3"
        password: The password to save for the network. Empty string represents
                no password, and PSK should be provided as 64 character hex string.
    """
    result_save = fd.wlan_policy_lib.wlanSaveNetwork(ssid, security_type,
                                                     password)
    if result_save["error"] != None:
        self.log.info("Failed to save network %s with error: %s" % ssid,
                      result_save["error"])
        return False
    else:
        return True


def reboot_device(fd):
    """ Reboot the device and reinitialize the device after.
    Args:
        fd: The device to reboot.
    """
    fd.reboot()
    fd.wlan_policy_lib.wlanCreateClientController()
    fd.wlan_policy_lib.wlanStartClientConnections()
