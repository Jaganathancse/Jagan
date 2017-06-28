class GetDpdkCoreListAction(base.TripleOAction):
    """Gets the DPDK Core List.

    :param inspect_data: For introspection data
    :param numa_nodes_threads_count For NUMA nodes threads count

    :return: DPDK Core List
    """

    def __init__(self, inspect_data, numa_nodes_threads_count):
        super(GetDpdkCoreListAction, self).__init__()
        self.inspect_data = inspect_data
        self.numa_nodes_threads_count = numa_nodes_threads_count

    def run(self, context):
        dpdk_core_list = []
        numa_cpus_info = self.inspect_data.get('numa_topology', {}).get('cpus', [])

        if not numa_cpus_info:
            msg = 'Introspection data does not have numa_topology.cpus'
            return mistral_workflow_utils.Result(error=msg)

        if not self.numa_nodes_threads_count:
            msg = 'Each NUMA nodes threads count is missing'
            return mistral_workflow_utils.Result(error=msg)

        numa_nodes_min = {}
        numa_nodes_threads = {}
        for cpu in numa_cpus_info:
            if not cpu['numa_node'] in numa_nodes_threads:
                numa_nodes_threads[cpu['numa_node']] = []
            numa_nodes_threads[cpu['numa_node']].extend(cpu['thread_siblings'])

        for numa_node in numa_nodes_threads.keys():
            numa_nodes_min[numa_node] = min(numa_nodes_threads[numa_node])

        for node_threads_count in self.numa_nodes_threads_count:
            node = self.numa_nodes_threads_count.index(node_threads_count)
            threads_count = node_threads_count
            for cpu in numa_cpus_info:
                if cpu['numa_node'] == node:
                    if not numa_nodes_min[node] in cpu['thread_siblings']:
                        #return cpu['thread_siblings'], threads_count, len(cpu['thread_siblings'])
                        dpdk_core_list.extend(cpu['thread_siblings'])
                        threads_count -= len(cpu['thread_siblings'])
                        if threads_count <= 0:
                            break
        return ','.join([str(thread) for thread in dpdk_core_list])
