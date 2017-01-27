echo 'Please type in the organization id, whose datasets you would like to migrate to a new organization:'
read old_org_id
echo "Please type in the organization id, to which you would like to migrate the old organizations datasets to:"
read new_org_id
curl https://INSERT_HERE_ETSIN_HOST_NAME/api/3/action/organization_show -d "{\"id\": \"$old_org_id\", \"include_datasets\": \"True\", \"include_dataset_count\": \"False\", \"include_extras\": \"False\", \"include_users\": \"False\", \"include_groups\": \"False\", \"include_tags\": \"False\", \"include_followers\": \"False\"}" -H "Authorization: INSERT_HERE_SYSADMIN_AUTHORIZATION" -k > org_packages.txt
sed 's/^.*\"packages\": \[(.*)\], \"num/\1/' org_packages.txt > org_packages_packages.txt
grep -oE '\"id\": \".*?\"' org_packages_packages.txt > all_ids.txt
sed "/$old_org_id/d" all_ids.txt > package_ids.txt
sed "s/(.*)/curl 'https:\/\/INSERT_HERE_ETSIN_HOST_NAME_WITH_DOTS_REPLACED_BY_BACKSLASH_AND_DOT\/api\/3\/action\/package_owner_org_update' -d '{\1, \"organization_id\": \"$new_org_id\"}' -H 'Authorization: INSERT_HERE_SYSADMIN_AUTHORIZATION' -k/" package_ids.txt > org_update_script.txt
chmod u+x org_update_script.txt
rm all_ids.txt org_packages.txt org_packages_packages.txt package_ids.txt
echo "After this script is run, manually go through the org_update_script.txt file and check that there isn't anything that does not belong there and save it. After this, run the file. Make sure package_owner_org_update API works in the target CKAN instance"
$old_org_id >> old_orgs.txt