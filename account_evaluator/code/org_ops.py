import boto3
import os
import logging
from code.boto_factory import BotoFactory

LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()

log = logging.getLogger('accountEvaluator')
log.setLevel(level=LOGLEVEL)


class OrgOps():

    def __init__(self, session):
        if os.environ.get('EXCLUDE_OUS'):
            self.blocklist = os.environ.get('EXCLUDE_OUS').split(',')
            log.info(f"Exclude OU:s: {self.blocklist}")
        else:
            log.warn(
                f"No EXCLUDE_OUS present in ENV, all OUs can be traversed"
            )
            self.blocklist = set()

        self.org = BotoFactory().get_capability(
            boto3.client, session, 'organizations'
        )

    def get_active_accounts(self):
        accounts = dict()
        paginator = self.org.get_paginator('list_accounts')
        itr = paginator.paginate()
        for i in itr:
            for account in i['Accounts']:
                if account['Status'] == 'ACTIVE':
                    accounts[account['Id']] = account
        return accounts

    def get_all_children_ou(self, parent_ou):
        ous = set()
        log.info(f"Getting children OU for {parent_ou}")
        pgnt = self.org.get_paginator('list_organizational_units_for_parent')
        itr = pgnt.paginate(
            ParentId=parent_ou
        )

        for i in itr:
            for ou in i['OrganizationalUnits']:
                if ou['Id'] not in self.blocklist:
                    ous.add(ou['Id'])

        if ous:
            for ou in ous.copy():
                ous.update(self.get_all_children_ou(ou))

        return ous

    def get_active_accounts_from_ous(self, ous):
        pgnt = self.org.get_paginator('list_accounts_for_parent')
        accounts = dict()
        for ou in ous:
            log.info(f"Getting accounts from {ou}")
            itr = pgnt.paginate(ParentId=ou)
            for i in itr:
                for account in i['Accounts']:
                    if account['Status'] == 'ACTIVE':
                        accounts[account['Id']] = account
        return accounts

    def get_accounts_from_root(self):
        root_ou = self.org.list_roots()['Roots'][0]['Id']
        return self.get_active_accounts_from_ous(
            self.get_all_children_ou(root_ou)
        )
