import ckan.plugins as p
import ckanext.hierarchy.logic.action as action
from ckanext.hierarchy import helpers
from ckan.lib.plugins import DefaultOrganizationForm

# This plugin is designed to work only these versions of CKAN
p.toolkit.check_ckan_version(min_version='2.0')

import logging
log = logging.getLogger(__name__)

class HierarchyDisplay(p.SingletonPlugin):

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.IActions, inherit=True)
    p.implements(p.ITemplateHelpers, inherit=True)

    # IConfigurer

    def update_config(self, config):
        p.toolkit.add_template_directory(config, 'templates')
        p.toolkit.add_template_directory(config, 'public')
        p.toolkit.add_resource('public/scripts/vendor/jstree', 'jstree')
        p.toolkit.add_resource('public/scripts', 'hierarchy')

    # IActions

    def get_actions(self):
        return {
            'group_tree': action.group_tree,
            'group_tree_cached': action.group_tree_cached,
            'group_tree_section': action.group_tree_section,
        }

    def get_helpers(self):
        return {
            'get_allowable_orgs': helpers.get_allowable_orgs,
            'get_hierarchy_string_by_id': helpers.get_hierarchy_string_by_id
        }


class HierarchyForm(p.SingletonPlugin, DefaultOrganizationForm):

    p.implements(p.IGroupForm, inherit=True)

    # Plugin
    def group_controller(self):
        return 'organization'

    # IGroupForm

    def group_types(self):
        return ('organization',)

    def setup_template_variables(self, context, data_dict):
        from pylons import tmpl_context as c

        model = context['model']
        group_id = data_dict.get('id')
        if group_id:
            group = model.Group.get(group_id)
            c.allowable_parent_groups = \
                group.groups_allowed_to_be_its_parent(type='organization')
        else:
            c.allowable_parent_groups = model.Group.all(group_type='organization')
