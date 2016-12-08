'''
	A script that parses csv files and exports the rows as hierarchical ckan organizations.

	Usage: python parser.py -k 12345678-b123-a123-12345-abc1235asd -i example.csv -c https://10.10.10.10 parse
	For multiple files, repeate -i parameter. i.e. '...asd -i file1.csv -i file2.csv ...'

	The csv rows are required to have at least 5 fields in the following order:
	vuosi; korkeakoulu; korkeakoulu_koodi; (paayksikko_koodi); alayksikko_koodi; alayksikko_nimi
	field 'paayksikko_koodi' is currently ignored and can be left blank.

	First csv row is assumed to be the header and is always ignored.
	Requires the following Python packages ('pip install -r requirements.txt')
		- slugify
		- ckanapi
'''

# import unicodecsv as csv
import csv
import logging
import sys
import argparse

from slugify import slugify
from ckanapi import RemoteCKAN, NotAuthorized, ValidationError

# set up logging to both file and stdout
log = logging.getLogger()

# Suppress some urllib3 warnings
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

# setup basic logging
fmt = '[%(asctime)s] %(message)s'
logging.basicConfig(filename='orgparser.log', level=logging.DEBUG, format=fmt)

# log info to stdout
log_stdout = logging.StreamHandler()
log_stdout.setFormatter(logging.Formatter(fmt))
logging.getLogger().addHandler(log_stdout)

FIELDS = ['year', 'name', 'code', 'unit_code', 'sub_code', 'sub_name']

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
				csv_reader = csv.DictReader(csv_file, delimiter=';', fieldnames=FIELDS)
				d = next(csv_reader, None)	# skip the 1st row
				for row in csv_reader:
					# progress counter
					line_counter += 1
					percentage = (float(line_counter)/float(num_lines)*100)
					log.info("[{}/{} {:.2g}%] {}"
						.format(line_counter, num_lines, percentage, row['name']))

					if govern(row):
						# save parent ids to parent_organizations dict
						if not row['code'] in root_orgs:
							root_orgs[row['code']] = create_organization(
								ckan, row['code'], row['name'], row['name'], "A Root-level organization")

						# otherwise append to hierarchy
						organization_code = '-'.join([row['code'], row['sub_code']])
						description = '{} - {} Organization code: '.format(row['name'], row['sub_name']) + organization_code
						slug_str = row['name'] + '-' + row['sub_name']
						parent = root_orgs.get(row['code'], None)
						create_organization(ckan, organization_code, slug_str, row['sub_name'], description, parent=parent)
		except IOError:
			log.debug('File {} could not be found.'.format(csvfile))

def govern(row):
	'''
		returns false, if the row does not contain necessary fields.
	'''
	required_keys = ['name', 'code', 'sub_code', 'sub_name']
	if all(row[i] for i in required_keys):
		return True
	else:
		log.debug('Missing fields. Skipping row {}'.format(row))
		return False

def create_organization(ckan, id_str, slug_str, name, desc, parent=None):
	slug = slugify(id_str).lower()[:100]  # field max length is 100 characters
	data_dict = {'name': slug, 'id': slug,  'title': name, 'description': desc, 'state': 'active'}
	log.debug('>> Creating organization {} [ID: {}]'.format(name, id_str))
	try:
		ckan.call_action('organization_create', data_dict, requests_kwargs={'verify': False})
		log.debug('Organization created.')
	except ValidationError as e:
		log.debug('Organization with same ID was found from the database. Updating instead.'.format(name, slug, id_str))
		ckan.call_action('organization_patch', data_dict, requests_kwargs={'verify': False})
		log.debug('Organization updated.')
	except NotAuthorized:
		log.error('API NotAuhtorized - please give a valid admin API key')
		sys.exit(1)

	if parent:
		log.debug('Adding to hierarchy. Parent ID: {}'.format(parent))
		data_dict = {'id': slug, 'groups':[{'capacity': 'public', 'name': parent}]}
		groups = ckan.call_action('organization_patch', data_dict, requests_kwargs={'verify': False})
		log.debug('Organization added to hierarchy.'.format(parent, slug))

	return id_str

def get_organizations(ckan, extra_dict=None):
	groups = ckan.call_action('organization_list', extra_dict, requests_kwargs={'verify': False})
	return groups

def delete_organizations(ckan):
	orgs = get_organizations(ckan, {'all_fields':True})
	log.info('Deleting {} organizations.'.format(len(orgs)))
	for org in orgs:
		if org['package_count'] == 0:
			# organization_purge purges data from database
			# organization_delete only hides the organizations (state: deleted)
			ckan.call_action('organization_delete', {'id': org['name']}, requests_kwargs={'verify': False})
			log.info('Successfully deleted organization {}'.format(org['name']))
		else:
			log.info('Organization {} is not deleted - associated datasets exist'.format(org))

def main():

	parser = argparse.ArgumentParser()
	parser.add_argument('command', choices=['parse', 'list', 'delete'],
		help='[parse] create an organization hierarchy from csv(s). \
		[list] list all organizations. [delete] delete all organizations.')
	parser.add_argument('-k', '--api-key',
		required=True, help='Admin API key for CKAN')
	parser.add_argument('-i', '--input', action='append',
		required=True, help='Input file(s) in CSV format. Add multiple files by repeating the argument (-i)')
	parser.add_argument('-c', '--ckan-host', default="https://10.10.10.42",
		help='CKAN host (i.e. https://10.10.10.10)')

	args = parser.parse_args()
	ckan = RemoteCKAN(args.ckan_host, apikey=args.api_key)

	if args.command == 'delete':
		confirmation = raw_input('>> Are you sure you want to DELETE ALL EMPTY organizations? (y/n)\n>> ')
		if confirmation.lower() in ['y', 'yes']:
			print('Deleting organizations. This might take a few seconds.')
			delete_organizations(ckan)
		else:
			sys.exit(1)
	if args.command == 'list':
		log.info('>> Fetching organizations. This might take a few seconds.')
		orgs = get_organizations(ckan)
		log.info('>> Organizations found in database:')
		for org in orgs:
			log.info(org)
		log.info('>> Found a total of {} organizations'.format(len(orgs)))
	if args.command == 'parse':
		parse_csv(ckan, args.input)

if __name__ == '__main__':
	main()