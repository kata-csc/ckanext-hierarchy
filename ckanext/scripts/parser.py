'''
	A script that parses csv files and exports the rows as hierarchical ckan organizations.

	Usage: python parser.py parse
	Edit the settings in settings.ini before running.

	The first row in a csv file defines the keys that are used to parse the
	organizations.

	The following keys are accepted as row headers. Separate rows with semi-colons:
	year;org_name;org_code;unit_main_code;unit_sub_code;unit_name;;;;;;;;;;;;;;
	unit_main_code can be left blank, other fields are required.

	Requires the following Python packages ('pip install -r requirements.txt')
		- slugify
		- ckanapi
'''

import csv
import logging
import sys
import ConfigParser

from slugify import slugify
from ckanapi import RemoteCKAN, NotAuthorized, ValidationError, NotFound

# setup config
config = ConfigParser.RawConfigParser()
config.read('settings.ini')

# set up logging to both file and stdout
log = logging.getLogger()

# suppress some urllib3 warnings
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# setup basic logging
fmt = '[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s'
logging.basicConfig(filename=config.get('general', 'logfile'), level=logging.DEBUG, format=fmt)

# log info to stdout
log_stdout = logging.StreamHandler()
log_stdout.setFormatter(logging.Formatter(fmt))
log_stdout.setLevel(logging.INFO)
logging.getLogger().addHandler(log_stdout)


def parse_csv(ckan, input_files):
	root_orgs = {}

	# keep track of progress
	num_lines = (-1 * len(input_files)) # first row is always skipped
	line_counter = 0
	for csvfile in input_files:
		num_lines += sum(1 for line in open(csvfile))

	for csvfile in input_files:
		log.info('Now parsing file {}'.format(csvfile))
		try:
			with open(csvfile, 'rb') as csv_file:
				csv_reader = csv.DictReader(csv_file, delimiter=';')
				for row in csv_reader:
					# parse fields in a single row
					org_name = row.get('org_name', '')
					org_code = row.get('org_code', '')
					unit_main_code = row.get('unit_main_code', '')
					unit_sub_code = row.get('unit_sub_code', '')
					unit_name = row.get('unit_name', '')

					# progress counter
					line_counter += 1
					percentage = (float(line_counter)/float(num_lines)*100)
					log.info("[{}/{} {:.2g}%] {} - {}"
						.format(line_counter, num_lines, percentage, org_name, unit_name))

					if govern(row):
						# save parent ids to parent_organizations dict
						# and create a root level organization
						if not org_code in root_orgs:
							slug_str = "-".join([org_code, org_name])
							root_orgs[org_code] = create_organization(ckan, org_code, slug_str, org_name)

						# otherwise create an org and append it to existing root's hierarchy
						if unit_sub_code and unit_name:
							organization_code = '-'.join([org_code, unit_sub_code])		# Unique
							slug_str = '-'.join([organization_code, org_name, unit_name])
							parent = root_orgs.get(org_code, None)
							create_organization(ckan, organization_code, slug_str, unit_name, parent=parent)
		except IOError:
			log.warning('File {} could not be found.'.format(csvfile))


def govern(row):
	'''
		returns false, if the row does not contain necessary fields.
	'''

	# root-level organization only
	if all(row[i] for i in ['org_name', 'org_code']):
		# check if sub-unit fields are present
		if not all(row[i] for i in ['unit_sub_code', 'unit_name']):
			log.warning('Missing unit codes. Creating root organization only: {}'.format(row))
		return True
	else:
		log.warning('Missing root organization fields. Skipping row {}'.format(row))
		return False


def create_organization(ckan, id_str, slug_str, name, desc=None, parent=None):
	name_slug = slugify(slug_str.decode('utf-8')).lower()[:100]  # field max length is 100 characters
	id_slug = slugify(id_str.decode('utf-8')).lower()[:100]
	data_dict = {'name': name_slug, 'id': id_slug,  'title': name, 'state': 'active'}
	if desc:
		data_dict['description'] = desc

	log.info('>> Creating organization {} [ID: {}]'.format(name, id_slug))

	if parent:
		# Add to hierarchy, if a parent ID is given
		# This happens by adding a parent capacity to groups field
		log.info('Adding to hierarchy, under parent ID {}.'.format(parent))
		data_dict['groups'] = [{'capacity': 'public', 'name': parent}]
	
	try:
		# Try to create the organization, if it doesn't exist yet
		ckan.call_action('organization_create', data_dict, requests_kwargs={'verify': False})
		log.info('Organization created.')

	except ValidationError as e:
		# If it already exists, just patch the new data
		log.info('Organization with same ID was found from the database. Updating instead.'.format(name, name_slug, id_slug))
		try:
			ckan.call_action('organization_patch', data_dict, requests_kwargs={'verify': False})
		except NotFound:
			log.error("Could not patch organization {}, {}, {}".format(name, name_slug, id_slug))
		log.info('Organization updated.')

	except NotAuthorized:
		log.error('API NotAuhtorized - please give a valid admin API key')
		sys.exit(1)

	return id_str


def get_organizations(ckan, extra_dict=None):
	groups = ckan.call_action('organization_list', extra_dict, requests_kwargs={'verify': False})
	return groups


def delete_hierarchical(ckan, delete_nonempty=True, purge=False):
	def walk_and_delete(tree):
		for node in tree:
			walk_and_delete(node.get('children'))
			if (delete_nonempty) or (node.get('dataset_count')) == 0:
				ckan.call_action(action, {'id': node.get('name')}, requests_kwargs={'verify': False})
				log.info('Successfully deleted organization {}'.format(node.get('name')))
			else:
				log.warning('Associated datasets for hierarchy {} exist. Organization was not deleted.'.format(node.get('name')))

	action = 'organization_delete'
	if purge:
		action = 'organization_purge'

	hierarchy = ckan.call_action('group_tree', requests_kwargs={'verify': False})
	walk_and_delete(hierarchy)


def main():
	# read arguments and config
	ckan_host = config.get('general', 'ckan_host')
	api_key = config.get('general', 'api_key')
	input_files = map(str.strip, config.get('general', 'input_files').split(','))
	purge_on_delete = config.getboolean('general', 'purge_on_delete')
	delete_nonempty = config.getboolean('general', 'delete_nonempty')

	# initialize ckanapi instance
	ckan = RemoteCKAN(ckan_host, apikey=api_key)

	def print_help():
		print('Usage: python parser.py parse | list | delete')
		print('    parse    Creates an organization hierarchy')
		print('             based on parsed csv rows.')
		print('    list     List all organizations in ckan db')
		print('    delete   Delete all empty organizations from ckan db')
		print()
		print('The script settings can be modified in settings.ini')

	cmd = None
	if len(sys.argv) == 2:
		cmd = sys.argv[1]
	else:
		print_help()
	
	# command logic
	if cmd == 'delete':
		if purge_on_delete:
			print('>> Organizations will be purged from the database (settings.ini -> purge_on_delete = True)!')
		confirmation = raw_input('>> Are you sure you want to DELETE ALL EMPTY organizations? (y/n)\n>> ')
		if confirmation.lower() in ['y', 'yes']:
			print('Deleting organizations. This might take a few seconds.')
			delete_hierarchical(ckan, delete_nonempty, purge_on_delete)
		else:
			sys.exit(1)

	elif cmd == 'list':
		log.info('>> Fetching organizations. This might take a few seconds.')
		orgs = get_organizations(ckan)
		log.info('>> Organizations found in database:')
		for org in orgs:
			log.info(org)
		log.info('>> Found a total of {} organizations'.format(len(orgs)))

	elif cmd == 'parse':
		parse_csv(ckan, input_files)

	else:
		print_help()


if __name__ == '__main__':
	main()
