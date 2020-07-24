import boto3
import logging
import json
import os
from code.boto_factory import BotoFactory


logging.basicConfig(level=logging.INFO)
log = logging.getLogger('accountEvaluator')
whitelisted_roles = set(str(os.environ.get('WHITELISTED_ROLES')).split(','))


class IAMOps():

    def __init__(self, account_id):
        self.session = boto3.Session()
        self.iam = BotoFactory().get_capability(
            boto3.resource, self.session, 'iam', account_id=account_id
        )
        self.interesting_roles = None
        self.users_w_used_passwords = None

    def get_interesting_roles(self):
        # returns all Roles as iam.Role resource
        #  .all() method Roles don't include role_last_used attribute!!
        roles = self.iam.roles.all()
        interesting_roles = list()
        for r in roles:
            if '/aws-service-role/' in r.arn or r.name in whitelisted_roles:
                pass
            else:
                for p in r.assume_role_policy_document.get('Statement'):
                    if p.get('Principal').get('Service'):
                        pass
                    else:
                        log.debug(f"Appending to interesting roles: {r.arn}")
                        interesting_roles.append(r)
        self.interesting_roles = interesting_roles
        return interesting_roles

    def get_timestamped_roles(self):
        if not self.interesting_roles:
            self.interesting_roles = self.get_interesting_roles()
        timestamped_roles = list()
        for r in self.interesting_roles:
            role = self.iam.Role(r.name)
            if role.role_last_used:
                timestamped_roles.append(role)
        return timestamped_roles

    def get_iam_users_w_used_password(self):
        # returns all users as iam.User resource
        self.users_w_used_passwords = [user for user in self.iam.users.all()
                                       if user.password_last_used]
        return self.users_w_used_passwords

