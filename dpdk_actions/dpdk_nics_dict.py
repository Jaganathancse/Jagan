class GetDpdkNicsNumaInfoAction(base.TripleOAction):
    """Gets the DPDK NICs with MTU for NUMA nodes.

    :param network_configs: For network config
    :param inspect_data: For introspection data

    :return: DPDK NICs NUMA nodes info
    """

    def __init__(self, network_configs, inspect_data, mtu_default=1500):
        super(GetDpdkNicsNumaInfoAction, self).__init__()
        self.network_configs = network_configs
        self.inspect_data = inspect_data
        self.mtu_default = mtu_default

    # TODO: Expose this utility from os-net-config to sort active nics
    def _natural_sort_key(self, s):
        nsre = re.compile('([0-9]+)')
        return [int(text) if text.isdigit() else text
                for text in re.split(nsre, s)]

    # TODO: Expose this utility from os-net-config to sort active nics
    def _is_embedded_nic(self, nic):
        if nic.startswith('em') or nic.startswith('eth') or nic.startswith('eno'):
            return True
        return False

    # TODO: Expose this utility from os-net-config to sort active nics
    def _ordered_nics(self, interfaces):
        embedded_nics = []
        nics = []
        for iface in interfaces:
            nic = iface.get('name', '')
            if self._is_embedded_nic(nic):
                embedded_nics.append(nic)
            else:
                nics.append(nic)
        active_nics = (sorted(embedded_nics, key=self._natural_sort_key) +
            sorted(nics, key=self._natural_sort_key))
        return active_nics

    def find_numa_node_id(self, numa_nics, nic_name):
         for nic_info in numa_nics:
             if nic_info.get('name', '') == nic_name:
                 return nic_info.get('numa_node', None)
         return None

    def get_physical_iface_name(self, ordered_nics, nic_name):
        if nic_name.startswith('nic'):
            # Nic numbering, find the actual interface name
            nic_number = int(nic_name.replace('nic', ''))
            if nic_number > 0:
                iface_name = ordered_nics[nic_number - 1]
                return iface_name
        return nic_name

    def get_dpdk_interfaces(self, dpdk_objs):
        mtu = self.mtu_default
        dpdk_ifaces = []
        for dpdk_obj in dpdk_objs:
            obj_type = dpdk_obj.get('type')
            mtu = dpdk_obj.get('mtu', self.mtu_default)
            if obj_type == 'ovs_dpdk_port':
                # Member interfaces of ovs_dpdk_port
                dpdk_ifaces.extend(dpdk_obj.get('members', []))
            elif obj_type == 'ovs_dpdk_bond':
                # ovs_dpdk_bond will have multiple ovs_dpdk_ports
                for bond_member in dpdk_obj.get('members', []):
                    if bond_member.get('type') == 'ovs_dpdk_port':
                        dpdk_ifaces.extend(bond_member.get('members', []))
        return (dpdk_ifaces, mtu)

    def run(self, context):
        interfaces = self.inspect_data.get('inventory',
            {}).get('interfaces', [])
        if not interfaces:
            msg = 'Introspection data does not have inventory.interfaces'
            return mistral_workflow_utils.Result(error=msg)

        numa_nics = self.inspect_data.get('numa_topology', {}).get('nics', [])
        if not numa_nics:
            msg = 'Introspection data does not have numa_topology.nics'
            return mistral_workflow_utils.Result(error=msg)

        active_interfaces = [iface for iface in interfaces
                             if iface.get('has_carrier', False)]
        if not active_interfaces:
            msg = 'Unable to determine active interfaces (has_carrier)'
            return mistral_workflow_utils.Result(error=msg)

        dpdk_nics_numa_info = []
        ordered_nics = self._ordered_nics(active_interfaces)
        for config in self.network_configs:
            if config.get('type', '') == 'ovs_user_bridge':
                members = config.get('members', [])
                dpdk_ifaces, mtu = self.get_dpdk_interfaces(members)
               for dpdk_iface in dpdk_ifaces:
                    name = dpdk_iface.get('name', '')
                    phy_name = self.get_physical_iface_name(
                        ordered_nics, name)
                    node = self.find_numa_node_id(numa_nics, phy_name)
                    if not node:
                        msg = ('Unable to determine NUMA node for '
                               'DPDK NIC: %s' % phy_name)
                        return mistral_workflow_utils.Result(error=msg)

                    dpdk_nic_info = {'name': phy_name,
                                     'numa_node': node,
                                     'mtu': mtu}
                    dpdk_nics_numa_info.append(dpdk_nic_info)
        return dpdk_nics_numa_info
