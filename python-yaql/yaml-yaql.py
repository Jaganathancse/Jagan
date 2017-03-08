import yaql
import yaml

data_source = yaml.load(open('input.yaml', 'r'))

engine = yaql.factory.YaqlFactory().create()

expression = engine(
    '$.customers.orders.selectMany($.where($.order_id = 4))')

order = expression.evaluate(data=data_source)

print order
