def get_profile_name(flavor_name, compute_client):
    profile_name = ''
    flavor = compute_client.flavors.find(name=flavor_name)
    if flavor:
        profile_name = flavor.get_keys().get('capabilities:profile')
    return profile_name

