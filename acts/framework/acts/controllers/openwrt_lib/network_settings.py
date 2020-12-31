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

SERVICE_DNSMASQ = "dnsmasq"
SERVICE_STUNNEL = "stunnel"
SERVICE_NETWORK = "network"
SERVICE_PPTPD = "pptpd"
SERVICE_FIREWALL = "firewall"
PPTP_PACKAGE = "pptpd kmod-mppe kmod-nf-nathelper-extra"
STUNNEL_CONFIG_PATH = "/etc/stunnel/DoTServer.conf"
HISTORY_CONFIG_PATH = "/etc/dirty_configs"
PPTPD_OPTION_PATH = "/etc/ppp/options.pptpd"
FIREWALL_CUSTOM_OPTION_PATH = "/etc/firewall.user"


class NetworkSettings(object):
    """Class for network settings.

    Attributes:
        ssh: ssh connection object.
        service_manager: Object manage service configuration
        ip: ip address for AccessPoint.
        log: Logging object for AccessPoint.
        config: A list to store changes on network settings.
        firewall_rules_list: A list of firewall rule name list
        cleanup_map: A dict for compare oppo functions.
    """

    def __init__(self, ssh, ip, logger):
        """Initialize wireless settings.

        Args:
            ssh: ssh connection object.
            ip: ip address for AccessPoint.
            logger: Logging object for AccessPoint.
        """
        self.ssh = ssh
        self.service_manager = ServiceManager(ssh)
        self.ip = ip
        self.log = logger
        self.config = set()
        self.firewall_rules_list = []
        self.cleanup_map = {
            "setup_dns_server": self.remove_dns_server,
            "setup_vpn_pptp_server": self.remove_vpn_pptp_server,
            "disable_ipv6": self.enable_ipv6
        }
        # This map contains cleanup functions to restore the configuration to
        # its default state. We write these keys to HISTORY_CONFIG_PATH prior to
        # making any changes to that subsystem.
        # This makes it easier to recover after an aborted test.
        self.update_firewall_rules_list()
        self.cleanup_network_settings()

    def cleanup_network_settings(self):
        """Reset all changes on Access point."""

        # Detect if any changes that is not clean up.
        if self.file_exists(HISTORY_CONFIG_PATH):
            out = self.ssh.run("cat %s" % HISTORY_CONFIG_PATH).stdout
            if out:
                self.config = set(out.split("\n"))

        if self.config:
            temp = self.config.copy()
            for change in temp:
                self.cleanup_map[change]()
            self.config = set()

        if self.file_exists(HISTORY_CONFIG_PATH):
            out = self.ssh.run("cat %s" % HISTORY_CONFIG_PATH).stdout
            if not out:
                self.ssh.run("rm %s" % HISTORY_CONFIG_PATH)

    def commit_changes(self):
        """Apply changes on Access point."""
        self.ssh.run("uci commit")
        self.service_manager.restart_services()
        self.create_config_file("\n".join(self.config),
                                HISTORY_CONFIG_PATH)

    def install(self, package_name):
        """Install package on OpenWrtAP via opkg.

        Args:
            package_name: package name want to install.
        """
        self.ssh.run("opkg update")
        self.ssh.run("opkg install %s" % package_name)

    def remove(self, package_name):
        """Remove package on OpenWrtAP via opkg.

        Args:
            package_name: package name want to install.
        """
        if self.package_installed(package_name):
            self.ssh.run("opkg remove %s" % package_name)
        else:
            self.log.info("No exist package %s found." % package_name)

    def package_installed(self, package_name):
        """Check if target package installed on OpenWrtAP.

        Args:
            package_name: package name want to check.

        Returns:
            True if installed.
        """
        if self.ssh.run("opkg list-installed %s" % package_name).stdout:
            return True
        return False

    def file_exists(self, abs_file_path):
        """Check if target file exist on specific path.

        Args:
            abs_file_path: Absolute path for the file.

        Returns:
            True if Existed.
        """
        path, file_name = abs_file_path.rsplit("/", 1)
        if self.ssh.run("ls %s | grep %s" % (path, file_name),
                        ignore_status=True).stdout:
            return True
        return False

    def count(self, config, key):
        """Count in uci config.

        Args:
            config: config or section to research
            key: keywords to  e.g. rule, domain
        Returns:
            Numbers of the count.
        """
        count = self.ssh.run("uci show %s | grep =%s" % (config, key),
                             ignore_status=True).stdout
        return len(count.split("\n"))

    def create_config_file(self, config, file_path):
        """Create config file. Overwrite if file already exist.

        Args:
            config: A string of content of config.
            file_path: Config's abs_path.
        """
        self.ssh.run("echo -e \"%s\" > %s" % (config, file_path))

    def replace_config_option(self, old_option, new_option, file_path):
        """Replace config option if pattern match.

        If find match pattern with old_option, then replace it with new_option.
        Else add new_option to the file.

        Args:
            old_option: the regexp pattern to replace.
            new_option: the option to add.
            file_path: Config's abs_path.
        """
        config = self.ssh.run("cat %s" % file_path).stdout
        config, count = re.subn(old_option, new_option, config)
        if not count:
            config = "\n".join([config, new_option])
        self.create_config_file(config, file_path)

    def remove_config_option(self, option, file_path):
        """Remove option from config file.

        Args:
            option: Option to remove. Support regular expression.
            file_path: Config's abs_path.
        Returns:
            Boolean for find option to remove.
        """
        config = self.ssh.run("cat %s" % file_path).stdout.split("\n")
        for line in config:
            count = re.subn(option, "", line)[1]
            if count > 0:
                config.remove(line)
                self.create_config_file("\n".join(config), file_path)
                return True
        self.log.warning("No match option to remove.")
        return False

    def setup_dns_server(self, domain_name):
        """Setup DNS server on OpenWrtAP.

        Args:
            domain_name: Local dns domain name.
        """
        self.config.add("setup_dns_server")
        self.log.info("Setup DNS server with domain name %s" % domain_name)
        self.ssh.run("uci set dhcp.@dnsmasq[0].local='/%s/'" % domain_name)
        self.ssh.run("uci set dhcp.@dnsmasq[0].domain='%s'" % domain_name)
        self.add_resource_record(domain_name, self.ip)
        self.service_manager.need_restart(SERVICE_DNSMASQ)
        self.commit_changes()

        # Check stunnel package is installed
        if not self.package_installed("stunnel"):
            self.install("stunnel")
            self.service_manager.stop(SERVICE_STUNNEL)
            self.service_manager.disable(SERVICE_STUNNEL)

        # Enable stunnel
        self.create_stunnel_config()
        self.ssh.run("stunnel /etc/stunnel/DoTServer.conf")

    def remove_dns_server(self):
        """Remove DNS server on OpenWrtAP."""
        if self.file_exists("/var/run/stunnel.pid"):
            self.ssh.run("kill $(cat /var/run/stunnel.pid)")
        self.ssh.run("uci set dhcp.@dnsmasq[0].local='/lan/'")
        self.ssh.run("uci set dhcp.@dnsmasq[0].domain='lan'")
        self.clear_resource_record()
        self.service_manager.need_restart(SERVICE_DNSMASQ)
        self.config.discard("setup_dns_server")
        self.commit_changes()

    def add_resource_record(self, domain_name, domain_ip):
        """Add resource record.

        Args:
            domain_name: A string for domain name.
            domain_ip: A string for domain ip.
        """
        self.ssh.run("uci add dhcp domain")
        self.ssh.run("uci set dhcp.@domain[-1].name='%s'" % domain_name)
        self.ssh.run("uci set dhcp.@domain[-1].ip='%s'" % domain_ip)
        self.service_manager.need_restart(SERVICE_DNSMASQ)

    def del_resource_record(self):
        """Delete the last resource record."""
        self.ssh.run("uci delete dhcp.@domain[-1]")
        self.service_manager.need_restart(SERVICE_DNSMASQ)

    def clear_resource_record(self):
        """Delete the all resource record."""
        rr = self.ssh.run("uci show dhcp | grep =domain",
                          ignore_status=True).stdout
        if rr:
            for _ in rr.split("\n"):
                self.del_resource_record()
        self.service_manager.need_restart(SERVICE_DNSMASQ)

    def create_stunnel_config(self):
        """Create config for stunnel service."""
        stunnel_config = [
            "pid = /var/run/stunnel.pid",
            "[dns]",
            "accept = 853",
            "connect = 127.0.0.1:53",
            "cert = /etc/stunnel/fullchain.pem",
            "key = /etc/stunnel/privkey.pem",
        ]
        config_string = "\n".join(stunnel_config)
        self.create_config_file(config_string, STUNNEL_CONFIG_PATH)

    def setup_vpn_pptp_server(self, local_ip, user, password):
        """Setup pptp vpn server on OpenWrt.

        Args:
            local_ip: local pptp server ip address.
            user: username for pptp user.
            password: password for pptp user.
        """
        #  Install pptp service
        if not self.package_installed(PPTP_PACKAGE):
            self.install(PPTP_PACKAGE)

        self.config.add("setup_vpn_pptp_server")
        # Edit /etc/config/pptpd & /etc/ppp/options.pptpd
        self.setup_pptpd(local_ip, user, password)
        # Edit /etc/config/firewall & /etc/firewall.user
        self.setup_firewall_rules_for_pptp()
        # Enable service
        self.service_manager.enable(SERVICE_PPTPD)
        self.service_manager.need_restart(SERVICE_PPTPD)
        self.service_manager.need_restart(SERVICE_FIREWALL)
        self.commit_changes()

    def remove_vpn_pptp_server(self):
        """Remove pptp vpn server on OpenWrt."""
        # Edit /etc/config/pptpd
        self.restore_pptpd()
        # Edit /etc/config/firewall & /etc/firewall.user
        self.restore_firewall_rules_for_pptp()
        # Disable service
        self.service_manager.disable(SERVICE_PPTPD)
        self.service_manager.need_restart(SERVICE_PPTPD)
        self.service_manager.need_restart(SERVICE_FIREWALL)
        self.config.discard("setup_vpn_pptp_server")
        self.commit_changes()

    def setup_pptpd(self, local_ip, username, password, ms_dns="8.8.8.8"):
        """Setup pptpd config for ip addr and account.

        Args:
            local_ip: vpn server address
            username: pptp vpn username
            password: pptp vpn password
            ms_dns: DNS server
        """
        # Calculate remote ip address
        # e.g. local_ip = 10.10.10.9
        # remote_ip = 10.10.10.10 -250
        remote_ip = local_ip.split(".")
        remote_ip.append(str(int(remote_ip.pop(-1)) + 1))
        remote_ip = ".".join(remote_ip)
        # Enable pptp service and set ip addr
        self.ssh.run("uci set pptpd.pptpd.enabled=1")
        self.ssh.run("uci set pptpd.pptpd.localip='%s'" % local_ip)
        self.ssh.run("uci set pptpd.pptpd.remoteip='%s-250'" % remote_ip)

        # Setup pptp service account
        self.ssh.run("uci set pptpd.@login[0].username='%s'" % username)
        self.ssh.run("uci set pptpd.@login[0].password='%s'" % password)
        self.service_manager.need_restart(SERVICE_PPTPD)

        self.replace_config_option(r"#*ms-dns \d+.\d+.\d+.\d+",
                                   "ms-dns %s" % ms_dns, PPTPD_OPTION_PATH)
        self.replace_config_option("(#no)*proxyarp",
                                   "proxyarp", PPTPD_OPTION_PATH)

    def restore_pptpd(self):
        """Disable pptpd."""
        self.ssh.run("uci set pptpd.pptpd.enabled=0")
        self.remove_config_option(r"\S+ pptp-server \S+ \*", PPP_CHAP_SECRET_PATH)
        self.service_manager.need_restart(SERVICE_PPTPD)

    def update_firewall_rules_list(self):
        """Update rule list in /etc/config/firewall."""
        new_rules_list = []
        for i in range(self.count("firewall", "rule")):
            rule = self.ssh.run("uci get firewall.@rule[%s].name" % i).stdout
            new_rules_list.append(rule)
        self.firewall_rules_list = new_rules_list

    def setup_firewall_rules_for_pptp(self):
        """Setup firewall for vpn pptp server."""
        self.update_firewall_rules_list()
        if "pptpd" not in self.firewall_rules_list:
            self.ssh.run("uci add firewall rule")
            self.ssh.run("uci set firewall.@rule[-1].name='pptpd'")
            self.ssh.run("uci set firewall.@rule[-1].target='ACCEPT'")
            self.ssh.run("uci set firewall.@rule[-1].proto='tcp'")
            self.ssh.run("uci set firewall.@rule[-1].dest_port='1723'")
            self.ssh.run("uci set firewall.@rule[-1].family='ipv4'")
            self.ssh.run("uci set firewall.@rule[-1].src='wan'")

        if "GRP" not in self.firewall_rules_list:
            self.ssh.run("uci add firewall rule")
            self.ssh.run("uci set firewall.@rule[-1].name='GRP'")
            self.ssh.run("uci set firewall.@rule[-1].target='ACCEPT'")
            self.ssh.run("uci set firewall.@rule[-1].src='wan'")
            self.ssh.run("uci set firewall.@rule[-1].proto='47'")

        iptable_rules = [
            "iptables -A input_rule -i ppp+ -j ACCEPT",
            "iptables -A output_rule -o ppp+ -j ACCEPT",
            "iptables -A forwarding_rule -i ppp+ -j ACCEPT"
        ]
        self.add_custom_firewall_rules(iptable_rules)
        self.service_manager.need_restart(SERVICE_FIREWALL)

    def restore_firewall_rules_for_pptp(self):
        """Restore firewall for vpn pptp server."""
        self.update_firewall_rules_list()
        if "pptpd" in self.firewall_rules_list:
            self.ssh.run("uci del firewall.@rule[%s]"
                         % self.firewall_rules_list.index("pptpd"))
        self.update_firewall_rules_list()
        if "GRP" in self.firewall_rules_list:
            self.ssh.run("uci del firewall.@rule[%s]"
                         % self.firewall_rules_list.index("GRP"))
        self.remove_custom_firewall_rules()
        self.service_manager.need_restart(SERVICE_FIREWALL)

    def add_custom_firewall_rules(self, rules):
        """Backup current custom rules and replace with arguments.

        Args:
            rules: A list of iptable rules to apply.
        """
        backup_file_path = FIREWALL_CUSTOM_OPTION_PATH+".backup"
        if not self.file_exists(backup_file_path):
            self.ssh.run("mv %s %s" % (FIREWALL_CUSTOM_OPTION_PATH,
                                       backup_file_path))
        for rule in rules:
            self.ssh.run("echo %s >> %s" % (rule, FIREWALL_CUSTOM_OPTION_PATH))

    def remove_custom_firewall_rules(self):
        """Clean up and recover custom firewall rules."""
        backup_file_path = FIREWALL_CUSTOM_OPTION_PATH+".backup"
        if self.file_exists(backup_file_path):
            self.ssh.run("mv %s %s" % (backup_file_path,
                                       FIREWALL_CUSTOM_OPTION_PATH))
        else:
            self.log.warning("Did not find %s" % backup_file_path)
            self.ssh.run("echo "" > %s" % FIREWALL_CUSTOM_OPTION_PATH)

    def disable_pptp_service(self):
        """Disable pptp service."""
        self.remove(PPTP_PACKAGE)

    def enable_ipv6(self):
        """Enable ipv6 on OpenWrt."""
        self.ssh.run("uci set network.lan.ipv6=1")
        self.ssh.run("uci set network.wan.ipv6=1")
        self.service_manager.enable("odhcpd")
        self.service_manager.reload(SERVICE_NETWORK)
        self.config.discard("disable_ipv6")
        self.commit_changes()

    def disable_ipv6(self):
        """Disable ipv6 on OpenWrt."""
        self.config.add("disable_ipv6")
        self.ssh.run("uci set network.lan.ipv6=0")
        self.ssh.run("uci set network.wan.ipv6=0")
        self.service_manager.disable("odhcpd")
        self.service_manager.reload(SERVICE_NETWORK)
        self.commit_changes()


class ServiceManager(object):
    """Class for service on OpenWrt.

        Attributes:
        ssh: ssh object for the AP.
        _need_restart: Record service need to restart.
    """

    def __init__(self, ssh):
        self.ssh = ssh
        self._need_restart = set()

    def enable(self, service_name):
        """Enable service auto start."""
        self.ssh.run("/etc/init.d/%s enable" % service_name)

    def disable(self, service_name):
        """Disable service auto start."""
        self.ssh.run("/etc/init.d/%s disable" % service_name)

    def restart(self, service_name):
        """Restart the service."""
        self.ssh.run("/etc/init.d/%s restart" % service_name)

    def reload(self, service_name):
        """Restart the service."""
        self.ssh.run("/etc/init.d/%s reload" % service_name)

    def restart_services(self):
        """Restart all services need to restart."""
        for service in self._need_restart:
            self.restart(service)
        self._need_restart = set()

    def stop(self, service_name):
        """Stop the service."""
        self.ssh.run("/etc/init.d/%s stop" % service_name)

    def need_restart(self, service_name):
        self._need_restart.add(service_name)
