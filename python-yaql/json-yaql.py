import yaql
import json

data_source = json.load(open('input.json', 'r'))

engine = yaql.factory.YaqlFactory().create()

expression = engine('$.introspection_data.numa_topology.cpus.groupBy($.numa_node).toDict($[0],list($[1].thread_siblings))')

data = expression.evaluate(data=data_source)

print data
