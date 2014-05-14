import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import requests
import time
import json



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

    access_token = get_access_token(username, password, headers)
    groups = get_groups(access_token, headers)
    for group in groups:
        print "%s: %s" % (group[u'name'], group[u'id'])

    complete = False
    pageCount = 0


#Generator function (acts as iterable) for messages in a given group.
def messages(token, groupid, before_id=None):
    endpoint = 'https://api.groupme.com/v3/groups/%s/messages' % str(groupid)
    completed = False
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
    while not completed:
        if before_id is not None:
            params = {'before_id':before_id}
        else:
            params = {}
        r = requests.get(endpoint, params=params, headers=headers)

        if r.status_code is not 200:
            raise LookupError("Received response %s" % r.response_code)
        response = r.json()
        messages = response[u'response'][u'messages']
        before_id = messages[-1][u'id']
        if len(messages) is not 20:
            completed = True
        for message in messages:
            if message[u'sender_id'] == u'system':
                message[u'sender_id'] = "0"
            yield message

def get_access_token(username, password):
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

    resp = requests.post(token_endpoint, data=payload, headers=headers).json()
    return resp[u'response'][u'access_token']

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
