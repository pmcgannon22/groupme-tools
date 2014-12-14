import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import requests
import time
import json
from concurrent import futures



def onRequestError(request):
    print(request.status_code)
    print(request.headers)
    print(request.text)
    sys.exit(2)


def main():
    """Usage: groupme-fetch.py groupId accessToken [oldest oldestId]|[newest newestId]

Writes out "transcript-groupId.json" with the history of the group
in chronological order.

If a file by that name is found, we'll go ahead and update that
scrape depending on the options you provide. It is assumed that the
file is in the correct format *and its messages are in chronological
order*.

Options for updating/continuing a scrape:

[If neither of these options is provided, we scrape from the present
until the job is finished (or interrupted in which case, use "oldest
oldestId" to continue fetching the past).]

 - If "oldest oldestId" is provided, oldestId is assumed to be the ID
   of the oldest (topmost) message in the existing transcript file.
   Messages older than it will be retrieved and added at the top of
   the file, in order.

 - If "newest newestId" is provided, newestId is assumed to be the ID
   of the newest (bottom-most) message in the existing transcript file.
   Messages newer than it will be retrieved and added at the bottom
   of the file, in order.
    """

    if len(sys.argv) is not 3 and len(sys.argv) is not 5:
        print(main.__doc__)
        sys.exit(1)

    beforeId = None
    stopId = None

    if len(sys.argv) is 5:
        if sys.argv[3] == 'oldest':
            beforeId = sys.argv[4]
        elif sys.argv[3] == 'newest':
            stopId = sys.argv[4]
        else:
            print(main.__doc__)
            sys.exit(1)

    #group = sys.argv[1]
    #accessToken = sys.argv[2]

    username = sys.argv[1]
    password = sys.argv[2]

    access_token = get_user_access(username, password, headers)[u'response'][u'access_token']
    groups = get_groups(access_token, headers)
    for group in groups:
        print "%s: %s" % (group[u'name'], group[u'id'])

    complete = False
    pageCount = 0

#Generator function (acts as iterable) for messages in a given group.
def messages(token, groupid, before_id=None, after_id=None):
    endpoint = 'https://api.groupme.com/v3/groups/%s/messages' % str(groupid)
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Accept-Language': 'en-US, en;q=0.8',
        'Origin': 'https://app.groupme.com',
        'Host':'api.groupme.com',
        'Referer': 'https://app.groupme.com/chats',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36',
        'X-Access-Token': token
        }

    completed = False
    while not completed:
        if before_id is not None:
            params = {'before_id':before_id}
        elif after_id is not None:
            params = {'after_id':after_id}
        else:
            params = {}
        r = requests.get(endpoint, params=params, headers=headers)
        if r.status_code is not 200:
            if r.status_code is 304:
                break
            elif r.status_code is 420:
                print "\n\n\nRATE LIMIT REACHED :(\n\n\n"
                break
            else:
                return
        response = r.json()
        messages = response[u'response'][u'messages']
        before_id = messages[-1][u'id']
        if len(messages) is not 20:
            completed = True
        for message in messages:
            if message[u'sender_id'] == u'system':
                message[u'sender_id'] = "0"
            if int(message[u'id']) < after_id:
                return
            yield message

def get_msgs(token, group_id, before_id, after_id):
    return [m for m in messages(token, group_id, before_id, after_id)]

def msg_concurrent(token, groupid, after_id=0, n_workers=15):
    first = messages(token, groupid, after_id=after_id).next()
    end = messages(token, groupid)

    last = end.next()
    last2 = end.next()
    if last2 and str(after_id) == str(last2[u'id']):
        return [last]

    futures_list = []
    msgs = []
    if first:
        worker_ids = []
        if len(first[u'id']) < 18:
            bchange_last = 1122523770
            bchange_range = bchange_last - int(first[u'id'])
            worker_ids += range(int(first[u'id']), bchange_last, bchange_range/n_workers)

        if len(last[u'id']) >= 18:
            start = 135572249042470445
            end = int(last[u'id'])
            diff = end - start
            worker_ids += range(start, end, diff/n_workers)

        with futures.ThreadPoolExecutor(max_workers=n_workers) as executor:
            for ind, n in enumerate(worker_ids):
                if ind > 0:
                    after = worker_ids[ind-1]
                else:
                    after = None
                futures_list.append(executor.submit(get_msgs, token, groupid, n, after))
        for future in futures.as_completed(futures_list):
            try:
                msgs += future.result()
            except ConnectionError:
                print "ConnectionError (caught): [{0}] {1}".format(e.errno, e.strerror)
    return msgs

def get_user_access(username, password):
    headers = {
        'Referer':'https://app.groupme.com/signin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36',
        'Accept':'application/json, text/plain, */*',
        'Origin':'https://app.groupme.com',
        'Host':'apigroupme.com',
        'Accept-Encoding':'gzip,deflate,sdch'
        }

    payload = {
        'username':username,
        'password':password,
        'app_id':'groupme=web',
        'grant_type':'password',
        }
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    headers['Host'] = 'v2.groupme.com'

    token_endpoint = 'https://v2.groupme.com/access_tokens'
    return requests.post(token_endpoint, data=payload, headers=headers).json()

def get_groups(access_token):
    headers = {
        'Referer':'https://app.groupme.com/signin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36',
        'Accept':'application/json, text/plain, */*',
        'Origin':'https://app.groupme.com',
        'Host':'api.groupme.com',
        'Accept-Encoding':'gzip,deflate,sdch'
        }
    endpoint = 'https://api.groupme.com/v3/groups'
    headers['X-Access-Token'] = access_token
    parameters = {'per_page':100,'page':1}
    r = requests.get(endpoint, params=parameters, headers=headers).json()
    return r[u'response']

def get_group(access_token, groupid):
    endpoint = "https://api.groupme.com/v3/groups/%s" % groupid
    headers = {
        'Referer':'https://app.groupme.com/signin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.116 Safari/537.36',
        'Accept':'application/json, text/plain, */*',
        'Origin':'https://app.groupme.com',
        'Host':'api.groupme.com',
        'Accept-Encoding':'gzip,deflate,sdch'
        }
    headers['X-Access-Token'] = access_token
    r  = requests.get(endpoint, headers=headers).json()
    return r[u'response']

if __name__ == '__main__':
    main()
    sys.exit(0)
