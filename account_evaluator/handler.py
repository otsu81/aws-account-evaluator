import os
import json
import boto3
import logging
from datetime import datetime
from dateutil.tz import tzutc
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from code.cost_ops import CostOps
from code.org_ops import OrgOps
from code.iam_ops import IAMOps
from code.teams_broadcaster import TeamsBroadcaster

MAX_THREADS = int(os.environ['MAX_THREADS'])
NBR_MONTHS = int(os.environ['NBR_MONTHS'])
LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()

logging.basicConfig(level=LOGLEVEL)
log = logging.getLogger('accountEvaluator')
accounts = dict()
results = dict()


def avg_growth(account_id):
    global results
    cost_ops = CostOps(account_id)
    avg_grow = cost_ops.get_mean_growth_over_months(NBR_MONTHS)
    tot_cost = sum(cost_ops.get_total_cost_for_past_months(NBR_MONTHS))
    results[account_id]['AvgGrowthPercent'] = round(avg_grow, 2)
    results[account_id]['TotalCostForPeriod'] = round(tot_cost, 2)


def account_last_used(account_id):
    global results
    iam = IAMOps(account_id)
    ts_roles = iam.get_timestamped_roles()
    ts_users = iam.get_iam_users_w_used_password()

    ts = [ts.role_last_used.get('LastUsedDate') for ts in ts_roles] + \
        [ts.password_last_used for ts in ts_users]

    if len(ts) == 0:
        oldest = datetime.min
        oldest = oldest.replace(tzinfo=tzutc())
        ts.append(oldest)
    else:
        ts.sort(reverse=False)

    results[account_id]['LastLogin'] = str(ts.pop())


def account_report(account_id):
    global results
    global accounts

    results[account_id] = dict()
    avg_growth(account_id)
    account_last_used(account_id)
    results[account_id]['JoinedTimestamp'] = \
        str(accounts[account_id]['JoinedTimestamp'])
    results[account_id]['Name'] = \
        accounts[account_id]['Name']


def get_oldest_accounts(results_dict, nbr=''):
    """
    returns a sorted dictionary by oldest. expects account_result_dict  with
    following structure:
    {
        (string):
          "AvgGrowthPercent": (string),
          "TotalCostForPeriod": (string),
          "LastLogin": (string),
          "JoinedTimestamp": (string),
          "Name": (string)
    }

    if nbr is not set, default to 10
    """

    if nbr == '':
        nbr = 10 if len(results_dict) > 10 else len(results_dict)

    try:
        sorted_d = OrderedDict(
            {
                k: v for k, v in sorted(
                    results_dict.items(),
                    key=lambda item: item[1]['LastLogin']
                )
            })
    except Exception as e:
        log.warn(e)
        return results_dict

    keys = list(sorted_d.keys())
    nbr_oldest_accounts = OrderedDict()
    for i in range(nbr):
        nbr_oldest_accounts[keys[i]] = sorted_d.get(keys[i])
    return nbr_oldest_accounts


def handler(event, context):
    global accounts
    global results

    # if there is an accountslist in event, only scan those accounts
    if event.get('AccountsList'):
        org = boto3.client('organizations')
        for a in event['AccountsList']:
            accounts[a] = org.describe_account(
                AccountId=a
            ).get('Account')
    # else get all active accounts, consider EXCLUDE_OU in .env
    else:
        accounts = OrgOps(boto3.Session()).get_accounts_from_root()

    # remove out of scope accounts
    if os.environ.get('EXCLUDE_ACCOUNT_IDS'):
        for account in os.environ['EXCLUDE_ACCOUNT_IDS'].split(','):
            try:
                accounts.pop(account.strip())
            except KeyError:
                log.info(f"{account} not in list of accounts")

    futures = dict()
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for account in accounts.keys():
            futures[account] = (
                executor.submit(account_report, account)
            )

    exceptions = dict()
    for f in futures:
        try:
            futures[f].result()
        except Exception as e:
            exceptions[f"{f}"] = str(e)

    body = {
        "result": json.dumps(results, indent=4, default=str),
        "input": event,
        "exceptions": exceptions
    }

    log.info(json.dumps(body, indent=4, default=str))

    if event.get('SendToTeams') == 'True':
        msg = get_oldest_accounts(results)
        msg['Exceptions'] = exceptions
        TeamsBroadcaster().send_message(msg, title='Top 10 oldest accounts')

    response = {
        "statusCode": 200,
        "body": body
    }

    return response
