from pylons.decorators.cache import beaker_cache


def _get_direct_hierarchy_string(org_obj):
    """
        Returns a hierarchy string for a single organization.
        i.e. 'Grandparent > Parent > Organization'
    """
    parent_hierarchy = org_obj.get_parent_group_hierarchy(type='organization')
    parent_hierarchy.append(org_obj)
    return ' > '.join([o.display_name for o in parent_hierarchy])


@beaker_cache(type="dbm", expire=86400)
def get_allowable_orgs(parent_objs):
    """
        Takes a list of parent objects as a parameter
        and retuns an object usable by select2 dropdown menu.
    """

    allowable_orgs = []
    for organization in parent_objs:
        result_dict = {}
        for k in ['id', 'name', 'title']:
            result_dict[k] = getattr(organization, k)

        result_dict['hierarchy'] = _get_direct_hierarchy_string(organization)
        allowable_orgs.append(result_dict)

    allowable_orgs.sort()

    return allowable_orgs
