import json
import subprocess
import sys
import yaml

def get_introspection_data(node_uuid):
    cmd = "openstack baremetal introspection data save " + node_uuid
    output = subprocess.check_output(cmd,shell=True)
    hw_data = json.loads(output)
    return hw_data


def get_dpdk_core_list(hw_data, dpdk_nics_numa_info, dpdk_nic_numa_cores_count=2):
    dpdk_core_list = []
    nics = hw_data.get('numa_topology', {}).get('nics', {})
    cpus = hw_data.get('numa_topology', {}).get('cpus', {})
    dpdk_nics_numa_nodes = [dpdk_nic['numa_node'] for dpdk_nic in dpdk_nics_numa_info]

    if not nics:
       raise Exception('Introspection data does not have numa_topology.nics')

    numa_cores = {}
    if not cpus:
       raise Exception('Introspection data does not have numa_topology.cpus')

    numa_nodes = get_numa_nodes(hw_data)
    for node in numa_nodes:
        if node in dpdk_nics_numa_nodes:
            numa_cores[node] = dpdk_nic_numa_cores_count
        else:
            numa_cores[node] = 1

    numa_nodes_threads = {};

    for cpu in cpus:
        if not cpu['numa_node'] in numa_nodes_threads:
            numa_nodes_threads[cpu['numa_node']] = []
        numa_nodes_threads[cpu['numa_node']].extend(cpu['thread_siblings'])

    for node, node_cores_count in numa_cores.items():
        numa_node_min = min(numa_nodes_threads[node])
        cores_count = node_cores_count
        for cpu in cpus:
            if cpu['numa_node'] == node:
                # Adds threads from core which is not having least thread
                if numa_node_min not in cpu['thread_siblings']:
                    dpdk_core_list.extend(cpu['thread_siblings'])
                    cores_count -= 1
                    if cores_count == 0:
                        break
    return ','.join([str(thread) for thread in dpdk_core_list])


def get_host_cpus_list(hw_data):
    host_cpus_list = []
    cpus = hw_data.get('numa_topology', {}).get('cpus', [])
    # Checks whether numa topology cpus information is not available
    # in introspection data.
    if not cpus:
        msg = 'Introspection data does not have numa_topology.cpus'
        raise Exception(msg)

    numa_nodes_threads = {}
    # Creates a list for all available threads in each NUMA nodes
    for cpu in cpus:
        if not cpu['numa_node'] in numa_nodes_threads:
            numa_nodes_threads[cpu['numa_node']] = []
        numa_nodes_threads[cpu['numa_node']].extend(
            cpu['thread_siblings'])

    for numa_node in sorted(numa_nodes_threads.keys()):
        node = int(numa_node)
        # Gets least thread in NUMA node
        numa_node_min = min(numa_nodes_threads[numa_node])
        for cpu in cpus:
            if cpu['numa_node'] == node:
                # Adds threads from core which is having least thread
                if numa_node_min in cpu['thread_siblings']:
                    host_cpus_list.extend(cpu['thread_siblings'])
                    break

    return ','.join([str(thread) for thread in host_cpus_list])


# Calculates socket memory for a NUMA node
def calculate_node_socket_memory(numa_node, dpdk_nics_numa_info,
                                 overhead, packet_size_in_buffer,
                                 minimum_socket_memory):
    distinct_mtu_per_node = []
    socket_memory = 0

    # For DPDK numa node
    for nics_info in dpdk_nics_numa_info:
        if (numa_node == nics_info['numa_node'] and
                not nics_info['mtu'] in distinct_mtu_per_node):
            distinct_mtu_per_node.append(nics_info['mtu'])
            socket_memory += (((nics_info['mtu'] + overhead)
                              * packet_size_in_buffer) /
                              (1024 * 1024))

    # For Non DPDK numa node
    if socket_memory == 0:
        socket_memory = minimum_socket_memory
    # For DPDK numa node
    else:
        socket_memory += 500

    socket_memory_in_gb = int(socket_memory / 1024)
    if socket_memory % 1024 > 0:
        socket_memory_in_gb += 1
    return (socket_memory_in_gb * 1024)

def get_dpdk_socket_memory(hw_data, dpdk_nics_numa_info, minimum_socket_memory=1500):
    dpdk_socket_memory_list = []
    overhead = 800
    packet_size_in_buffer = 4096 * 64
    numa_nodes = get_numa_nodes(hw_data)

    for node in numa_nodes:
        socket_mem = calculate_node_socket_memory(
            node, dpdk_nics_numa_info, overhead,
            packet_size_in_buffer,
            minimum_socket_memory)
        dpdk_socket_memory_list.append(socket_mem)

    return ','.join([str(sm) for sm in dpdk_socket_memory_list])


def get_nova_cpus_list(hw_data, dpdk_cpus, host_cpus):
    nova_cpus_list = []
    cpus = hw_data.get('numa_topology', {}).get('cpus', {})
    threads = []
    # Creates a list for all available threads in each NUMA nodes
    for cpu in cpus:
        threads.extend(cpu['thread_siblings'])
    exclude_cpus_list = dpdk_cpus.split(',')
    exclude_cpus_list.extend(host_cpus.split(','))
    for thread in threads:
        if not str(thread) in exclude_cpus_list:
            nova_cpus_list.append(thread)
    
    return ','.join([str(thread) for thread in nova_cpus_list])


def get_host_isolated_cpus_list(dpdk_cpus, nova_cpus):
    host_isolated_cpus_list = dpdk_cpus.split(',')
    host_isolated_cpus_list.extend(nova_cpus.split(','))
    return ','.join([str(thread) for thread in host_isolated_cpus_list])


def get_dpdk_nics_numa_info(hw_data, dpdk_nics_info):
    dpdk_nics_numa_info = []
    nics = hw_data.get('numa_topology', {}).get('nics', [])
    for dpdk_nic in dpdk_nics_info:
        valid_dpdk_nic = False
        for nic in nics:
            if dpdk_nic['nic'] == nic['name']:
                valid_dpdk_nic = True
                dpdk_nic_info = {'name': dpdk_nic['nic'],
                                 'numa_node': nic['numa_node'],
                                 'mtu': dpdk_nic['mtu']}
                dpdk_nics_numa_info.append(dpdk_nic_info);
        if not valid_dpdk_nic:
            raise Exception("Invalid DPDK NIC '%(nic)s'" % {'nic': dpdk_nic['nic']})
    return dpdk_nics_numa_info


def get_numa_nodes(hw_data):
    nics = hw_data.get('numa_topology', {}).get('nics', [])
    numa_nodes = []
    for nic in nics:
        if not nic['numa_node'] in numa_nodes:
            numa_nodes.append(nic['numa_node'])
    return sorted(numa_nodes)

def get_kernel_args(hw_data, hugepage_alloc_perc, isol_cpus):
    if not is_supported_default_hugepages(hw_data):
        raise Exception("default huge page size 1GB is not supported")

    total_memory = hw_data.get('inventory', {}).get('memory', {}).get('physical_mb', 0)
    hugepages = int(float((total_memory / 1024) - 4) * (float(hugepage_alloc_perc) / float(100)))
    iommu_info = ''
    cpu_model = hw_data.get('inventory', {}).get('model_name', '')
    if cpu_model.startswith('Intel'):
        iommu_info = 'intel_iommu=on iommu=pt'
    kernel_args = ('default_hugepagesz=1GB hugepagesz=1G '
                   'hugepages=%(hugepages)d %(iommu_info)s'
                   ' isolcpus=%(isol_cpus)s' %{'hugepages': hugepages,
                                              'iommu_info': iommu_info,
                                              'isol_cpus': isol_cpus})
    return kernel_args


def is_supported_default_hugepages(hw_data):
    flags = hw_data.get('inventory', {}).get('cpu', {}).get('flags', [])
    return ('pdpe1gb' in flags)


def convert_number_to_range_list(num_list):
    num_list = [int(num.strip(' '))
                for num in num_list.split(",")]
    num_list.sort()
    range_list = []
    range_min = num_list[0]
    for num in num_list:
        next_val = num + 1
        if next_val not in num_list:
            if range_min != num:
                range_list.append(str(range_min) + '-' + str(num))
            else:
                range_list.append(str(range_min))
            next_index = num_list.index(num) + 1
            if next_index < len(num_list):
                range_min = num_list[next_index]

    return ','.join(range_list)


def vaildate_user_input(user_input):
    print(user_input)
    if not 'node_uuid' in user_input.keys():
        raise Exception("node UUID is missing in user input!");
    if not 'dpdk_nics' in user_input.keys():
        raise Exception("DPDK NIC's and MTU info are missing in user input!");
    for key in user_input.keys():
        if not key in ['node_uuid', 'dpdk_nics']:
            raise Exception("Invalid user input '%(key)s'" % {'key': key})


if __name__ == '__main__':
    parameters = {}
    try:
        print("Validating user inputs..")
        user_input = json.loads(sys.argv[1])
        vaildate_user_input(user_input)
        print("Deriving DPDK parameters..")
        hw_data = get_introspection_data(user_input['node_uuid'])
        dpdk_nics_info = get_dpdk_nics_numa_info(hw_data, user_input['dpdk_nics'])
        dpdk_cpus = get_dpdk_core_list(hw_data, dpdk_nics_info) 
        host_cpus = get_host_cpus_list(hw_data)
        dpdk_socket_memory = get_dpdk_socket_memory(hw_data, dpdk_nics_info)
        nova_cpus = get_nova_cpus_list(hw_data, dpdk_cpus, host_cpus)
        isol_cpus = get_host_isolated_cpus_list(dpdk_cpus, nova_cpus)
        host_mem = 4096
        hugepage_alloc_perc = 50
        isol_cpus = convert_number_to_range_list(isol_cpus)
        kernel_args = get_kernel_args(hw_data, hugepage_alloc_perc, isol_cpus)

        parameters['DpdkCoreList'] = convert_number_to_range_list(dpdk_cpus)
        parameters['HostCpusList'] = convert_number_to_range_list(host_cpus)
        parameters['NeutronDpdkSocketMemory'] = dpdk_socket_memory
        parameters['NovaCpusList'] = convert_number_to_range_list(nova_cpus)
        parameters['HostIsolatedCpusList'] = isol_cpus
        parameters['kernal_args'] = kernel_args
    except Exception as exc:
        print("Error: %s", exc)

    print(yaml.safe_dump(parameters, default_flow_style=False))
