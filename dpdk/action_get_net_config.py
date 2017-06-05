class GetNetworkConfigAction(templates.ProcessTemplatesAction):
    """Gets network configuration dteails available heat parameters."""

    def __init__(self, role_name, container=constants.DEFAULT_CONTAINER_NAME):
        super(GetNetworkConfigAction, self).__init__(container=container)
        self.role_name = role_name

    def run(self, context):

        cached = self.cache_get(context,
                                self.container,
                                "tripleo.parameters.get_network_config")

        if cached is not None:
            return cached

        processed_data = super(GetNetworkConfigAction, self).run(context)

        # If we receive a 'Result' instance it is because the parent action
        # had an error.
        if isinstance(processed_data, mistral_workflow_utils.Result):
            return processed_data

        fields = {
            'template': processed_data['template'],
            'files': processed_data['files'],
            'environment': processed_data['environment'],
            'stack_name': self.container,
        }
        orc = self.get_orchestration_client(context)
        preview_data = orc.stacks.preview(**fields)
        result = self.getNetworkConfig(preview_data, self.container,
                                       self.role_name)
        self.cache_set(context,
                       self.container,
                       "tripleo.parameters.get_network_config",
                       result)
        return result

    def getNetworkConfig(self, preview_data, stack_name, role_name):
        result = None
        if preview_data:
            for res in preview_data.resources:
                net_script = self.processPreviewList(res,
                                                     stack_name,
                                                     role_name)
                if net_script:
                    ns_len = len(net_script)
                    start_index = (net_script.find(
                        "echo '{\"network_config\"", 0, ns_len) + 6)
                    end_index = net_script.find("'", start_index, ns_len)
                    if (end_index > start_index):
                        net_config = net_script[start_index:end_index]
                        if net_config:
                            result = json.loads(net_config)
                    break
        return result

    def processPreviewList(self, res, stack_name, role_name):
        if type(res) == list:
            for item in res:
                out = self.processPreviewList(item, stack_name, role_name)
                if out:
                    return out
        elif type(res) == dict:
            res_stack_name = stack_name + '-' + role_name
            if res['resource_name'] == "OsNetConfigImpl" and \
                res['resource_identity'] and \
                res_stack_name in res['resource_identity']['stack_name']:
                return res['properties']['config']
        return None
