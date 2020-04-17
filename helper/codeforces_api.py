
import requests
from discord.ext import commands
import json
from helper import TaggingDb
import os
import random
class CodeforcesApiError(commands.CommandError):
    """Base class for all API related errors."""
    def __init__(self, message=None):
        super().__init__(message or 'Codeforces API error')

class TrueApiError(CodeforcesApiError):
    """An error originating from a valid response of the API."""
    def __init__(self, comment, message=None):
        super().__init__(message)
        self.comment = comment


class HandleNotFoundError(TrueApiError):
    def __init__(self, comment, handle):
        super().__init__(comment, f'Không tìm thấy nick `{handle}` trên codeforces')


class HandleInvalidError(TrueApiError):
    def __init__(self, comment, handle):
        super().__init__(comment, f'`{handle}` không phải là một nick hợp lệ trên codeforces')


class CallLimitExceededError(TrueApiError):
    def __init__(self, comment):
        super().__init__(comment, 'Codeforces API call limit exceeded')



BASE_status = 'https://codeforces.com/api/user.status?handle={0}&lang=en'
DBPATH = 'database/save'
async def get_user_status(handle):
    url = BASE_status.format(handle)
    try:
        resp = requests.get(url, timeout=2)
        try:
            r = resp.json()
        except Exception as e:
            comment = f'CF API did not respond with JSON, status {resp.status}.'
            raise CodeforcesApiError(comment)
        if 'comment' in r:
            comment = r['comment']
        else:
            res = []
            for x in r['result']:
                if 'contestId' not in x:
                    continue
                contest_id = x['contestId']
                if contest_id > 10000:
                    continue
                if 'verdict' not in x or x['verdict'] != 'OK':
                    continue
                p = {}
                p['submission_id'] = x['id']
                p['short_link'] = str(contest_id) + '/' + str(x['problem']['index'])
                p['name'] = x['problem']['name']
                p['tags'] = x['problem']['tags']
                res.append(p)
            return res
    except Exception as e:
        print(e)
        raise TrueApiError(str(e))
    if 'limit exceeded' in comment:
        raise CallLimitExceededError(comment)
    if 'not found' in comment:
        raise HandleNotFoundError(comment, handle)
    if 'should contain' in e.comment:
        raise HandleInvalidError(comment, handle)
                
    raise TrueApiError(comment)

async def get_problem(handle, id):
    if os.path.exists(DBPATH + f'/{id}.json') is False:
        print("Getting data from codeforces")
        data = await get_user_status(handle)
        print("done")
    else:
        data = json.load(open(DBPATH + f'/{id}.json', encoding='utf-8'))
    tagged_table = TaggingDb.TaggingDb.get_data('tagged', limit=None)
    tagged = set()
    for problem, tag in tagged_table:
        if tag is None:
            continue
        tagged.add(problem)
    data = list(filter(lambda x: x['short_link'] not in tagged, data))
    json.dump(data, open(DBPATH + f'/{id}.json', 'w', encoding='utf-8'))
    if len(data) == 0:
        return None
    return random.choice(data)