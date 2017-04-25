
class GetProfileNameAction(base.TripleOAction):
    """Gets the profile name for a given flavor name."""

    def __init__(self, flavor_name):
        super(GetProfileNameAction, self).__init__()
        self.flavor_name = flavor_name

    def run(self):
        compute_client = self.get_compute_client()
        return parameters.get_profile_name(self.flavor_name, compute_client)
