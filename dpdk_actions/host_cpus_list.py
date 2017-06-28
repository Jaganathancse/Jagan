class GetHostCpusListAction(base.TripleOAction):
    """Gets the Host CPUs List.

    :param inspect_data: For introspection data

    :return: Host CPUs List
    """

    def __init__(self, inspect_data):
        super(GetHostCpusListAction, self).__init__()
        self.inspect_data = inspect_data

    def run(self, context):
        host_cpus_list = []
        numa_cpus_info = self.inspect_data.get('numa_topology', {}).get('cpus', [])

        if not numa_cpus_info:
            msg = 'Introspection data does not have numa_topology.cpus'
            return mistral_workflow_utils.Result(error=msg)

        numa_nodes_min = {}
        numa_nodes_threads = {}
        for cpu in numa_cpus_info:
            if not cpu['numa_node'] in numa_nodes_threads:
                numa_nodes_threads[cpu['numa_node']] = []
            numa_nodes_threads[cpu['numa_node']].extend(cpu['thread_siblings'])

        for numa_node in numa_nodes_threads.keys():
            numa_nodes_min[numa_node] = min(numa_nodes_threads[numa_node])

        for numa_node in numa_nodes_threads.keys():
            node = int(numa_node)
            for cpu in numa_cpus_info:
                if cpu['numa_node'] == node:
                    if  numa_nodes_min[node] in cpu['thread_siblings']:
                        host_cpus_list.extend(cpu['thread_siblings'])
                        break

        return ','.join([str(thread) for thread in host_cpus_list])
