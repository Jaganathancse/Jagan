lass GetDpdkSocketMemoryAction(base.TripleOAction):
    """Gets the DPDK Socket Memory List.

    :param dpdk_nics_numa_info: For DPDK nics numa info
    :param numa_nodes: For list of numa nodes
    :param overhead: For overhead value
    :param packet_size_in_buffer: For packet size in buffer
    :param non_dpdk_node_socket_memory: For non dpdk nodes socket memory

    :return: DPDK Socket Memory List
    """
    def __init__(self, dpdk_nics_numa_info, numa_nodes,
                 overhead, packet_size_in_buffer,
                 non_dpdk_node_socket_memory=1024):
        super(GetDpdkSocketMemoryAction, self).__init__()
        self.dpdk_nics_numa_info = dpdk_nics_numa_info
        self.numa_nodes = numa_nodes
        self.overhead = overhead
        self.packet_size_in_buffer = packet_size_in_buffer
        self.non_dpdk_node_socket_memory = non_dpdk_node_socket_memory

    def calculate_node_socket_memory(self, numa_node,
        dpdk_nics_numa_info, overhead, packet_size_in_buffer,
            non_dpdk_node_socket_memory):
        distinct_mtu_per_node = []
        socket_memory = 0
        for nics_info in dpdk_nics_numa_info:
            if (numa_node == nics_info['numa_node'] and
                not nics_info['mtu'] in distinct_mtu_per_node):
                distinct_mtu_per_node.append(nics_info['mtu'])
                socket_memory += ((nics_info['mtu'] + overhead)
                                 * packet_size_in_buffer)/(1024*1024)
         # For Non DPDK numa node
        if socket_memory == 0:
            socket_memory = non_dpdk_node_socket_memory
        else:
            socket_memory += 500
        socket_memory_in_gb = (socket_memory/1024)
        if socket_memory % 1024 > 0:
            socket_memory_in_gb +=1
        return (socket_memory_in_gb * 1024)

    def run(self, context):
        dpdk_socket_memory_list = []
        for node in self.numa_nodes:
            sm = self.calculate_node_socket_memory(
                node, self.dpdk_nics_numa_info, self.overhead,
                self.packet_size_in_buffer,
                self.non_dpdk_node_socket_memory)
            dpdk_socket_memory_list.append(sm)

        return ','.join([str(sm) for sm in dpdk_socket_memory_list])
