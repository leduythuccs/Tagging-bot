import requests
from discord.ext import commands
import json
from helper import TaggingDb
import os
import random
import re

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
BASE_info = 'https://codeforces.com/api/user.info?handles={0}&lang=en'
DBPATH = 'database/save'
_IS_TAGGED = 0
_NOT_FOUND = 1
_RATING_TOO_LOW = 2
_LIM_RATING = 1700
contests = None
async def mapping_problem_rating(contest_id: str, index: str, current_rating: int)->int:
    global contests
    if contests is None:
        contests = await get_contests_info()
    contest_id = int(contest_id)
    contest_type = contests[contest_id]["div"] if contest_id in contests else "unk"
    if contest_type == "div2":
        if index == "D":
            return max(current_rating, 1900)
        if index == "E":
            return max(current_rating, 2300)
        if index == "F":
            return max(current_rating, 2500)
    if contest_type == "div1":
        if index == "C":
            return max(current_rating, 2300)
        if index == "D":
            return max(current_rating, 2500)
        if index == "E":
            return max(current_rating, 2700)
    if contest_type == "comb":
        if index == "H" or index == "G":
            return max(current_rating, 2700)
    return current_rating
async def get_contests_info():
    url = "https://codeforces.com/api/contest.list?lang=en"
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
            res = {}
            for contest in r["result"]:
                div1 = (len(re.findall(r"Div\.* *1", contest["name"])) != 0)
                div2 = (len(re.findall(r"Div\.* *2", contest["name"])) != 0)
                comb = (len(re.findall(r"Hello|Good bye|Global", contest["name"])) != 0)
                if (div1 and div2) or comb:
                    res[contest["id"]] = {"name": contest["name"], "div": "comb"}
                elif div1:
                    res[contest["id"]] = {"name": contest["name"], "div": "div1"}
                elif div2:
                    res[contest["id"]] = {"name": contest["name"], "div": "div2"}
                else:
                    res[contest["id"]] = {"name": contest["name"], "div": "unk"}
            return res
    except Exception as e:
        print(e)
        raise TrueApiError(str(e), 'Codeforces API error:\n' + str(e))
    if 'limit exceeded' in comment:
        raise CallLimitExceededError(comment)
    raise TrueApiError(comment, 'Codeforces API error:\n' + comment)

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
                if 'rating' not in x['problem']:
                    continue
                p['rating'] = await mapping_problem_rating(str(contest_id), str(x['problem']['index']), int(x['problem']['rating']))
                p['name'] = x['problem']['name']
                p['tags'] = x['problem']['tags']
                if '*special' in p['tags'] or 'special' in p['tags']:
                    continue
                res.append(p)
            return res
    except Exception as e:
        print(e)
        raise TrueApiError(str(e), 'Codeforces API error:\n' + str(e))
    if 'limit exceeded' in comment:
        raise CallLimitExceededError(comment)
    if 'not found' in comment:
        raise HandleNotFoundError(comment, handle)
    if 'should contain' in e.comment:
        raise HandleInvalidError(comment, handle)

    raise TrueApiError(comment, 'Codeforces API error:\n' + comment)


async def get_user_info(handle):
    url = BASE_info.format(handle)
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
            return {'max_rating': r['result'][0]['maxRating'] if 'maxRating' in r['result'][0] else 1500}
    except Exception as e:
        print(e)
        raise TrueApiError(str(e), 'Codeforces API error:\n' + str(e))
    if 'limit exceeded' in comment:
        raise CallLimitExceededError(comment)
    if 'not found' in comment:
        raise HandleNotFoundError(comment, handle)
    if 'should contain' in e.comment:
        raise HandleInvalidError(comment, handle)

    raise TrueApiError(comment, 'Codeforces API error:\n' + comment)

def get_skipped(id):
    if os.path.exists(DBPATH + f'/skip_{id}.json') is False:
        return []
    return json.load(open(DBPATH + f'/skip_{id}.json', encoding='utf-8'))

def skip_problem(id, problem):
    x = get_skipped(id)
    x.append(problem)
    json.dump(x, open(DBPATH + f'/skip_{id}.json', 'w', encoding='utf-8'))

async def pick(handle, id, short_link):
    # all_tag = TaggingDb.TaggingDb.get_all_problem_tag(short_link)
    # cnt_set = set()
    # for tag, discord_id in all_tag:
    #     cnt_set.add(discord_id)

    # if str(id) not in cnt_set and len(cnt_set) >= 2:
    #     return _IS_TAGGED

    if os.path.exists(DBPATH + f'/info_{id}.json') is False:
        print("Getting user info")
        user_info = {'done': 0}
        user_info['info'] = await get_user_info(handle)
        print("Done")
        json.dump(user_info, open(DBPATH + f'/info_{id}.json', 'w', encoding='utf-8'))
    else:
        user_info = json.load(open(DBPATH + f'/info_{id}.json', encoding='utf-8'))

    print("Getting data from codeforces", handle)
    data = await get_user_status(handle)
    print("Done")
    json.dump(data, open(DBPATH + f'/{id}.json', 'w', encoding='utf-8'))

    for x in data:
        if x['short_link'] == short_link:
            if x['rating'] < _LIM_RATING:
                return _RATING_TOO_LOW
            return x
    return _NOT_FOUND

async def force_pick(handle, id, short_link, submission_link):
    p = {}
    p['short_link'] = short_link
    p['submission_id'] = "null"
    p['submission_link'] = submission_link
    p['rating'] = "unknown"
    p['name'] = short_link
    p['tags'] = "unknown"
    return p

async def get_problem(handle, id):
    if os.path.exists(DBPATH + f'/{id}.json') is False:
        print(id, "Getting data from codeforces")
        data = await get_user_status(handle)
        print("Done")
        json.dump(data, open(DBPATH + f'/{id}.json', 'w', encoding='utf-8'))
    else:
        data = json.load(open(DBPATH + f'/{id}.json', encoding='utf-8'))
    if os.path.exists(DBPATH + f'/info_{id}.json') is False:
        print("Getting user info")
        user_info = {'done': 0}
        user_info['info'] = await get_user_info(handle)
        print("Done")
    else:
        user_info = json.load(open(DBPATH + f'/info_{id}.json', encoding='utf-8'))
    L_rating = max(_LIM_RATING, user_info['info']['max_rating'] - 200)
    R_rating = max(user_info['info']['max_rating'] + 500, 2000)
    if user_info['info']['max_rating'] >= 2200:
        R_rating = 10000
        L_rating = max(_LIM_RATING, user_info['info']['max_rating'] - 300)
    if str(id) == "182882392787255297": #Tò mò cực mạnh ko cần max rating
        R_rating = 10000
    if str(id) == "557515828270989333": #Vì sự sống của project
        R_rating = 1800
    if str(id) == "507060246959882251": #bjn orz
        R_rating = 2700
        L_rating = 1700
    if str(id) == "343242804492763138": #bach orz
        R_rating = 2700
    if str(id) == "170857535962611712": #Mofk dirty farm 
        L_rating = min(L_rating, 2200)
    tagged_table = TaggingDb.TaggingDb.get_data('tagged', limit=None)
    tagged = {}
    for problem, tag, discord_id in tagged_table:
        if tag is None:
            continue
        if problem not in tagged:
            tagged[problem] = set()
        tagged[problem].add(int(discord_id))

    data = list(
        filter(
            lambda x: (x['short_link'] not in tagged
                       or (len(tagged[x['short_link']]) < 2 and id not in tagged[x['short_link']]))
            and L_rating <= x['rating']
            and x['rating'] <= R_rating,
            data
        )
    )
    skipped = get_skipped(id)
    data = list(filter(lambda x: x not in skipped, data))
    user_info['done'] += 1
    json.dump(user_info, open(DBPATH + f'/info_{id}.json', 'w', encoding='utf-8'))
    if len(data) == 0:
        return None
    if user_info['done'] % 5 != 0:
        return random.choice(data)
    # get hardest
    max_r = 0
    for x in data:
        max_r = max(max_r, x['rating'])
    for x in data:
        if max_r == x['rating']:
            return x
    return random.choice(data)


def get_current_problem(id):
    if os.path.exists(DBPATH + f'/info_{id}.json') is False:
        return None
    user_info = json.load(open(DBPATH + f'/info_{id}.json', encoding='utf-8'))
    if 'doing' not in user_info:
        return None
    return user_info['doing']


def set_current_problem(id, problem, skip=True):
    user_info = json.load(open(DBPATH + f'/info_{id}.json', encoding='utf-8'))
    previous_problem = None if 'doing' not in user_info else user_info['doing']
    if previous_problem is not None:
        if skip:
            skip_problem(id, previous_problem)

    user_info['doing'] = problem
    if problem is None:
        user_info.pop('doing')
    json.dump(user_info, open(DBPATH + f'/info_{id}.json', 'w', encoding='utf-8'))
