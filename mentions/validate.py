import requests
from requests import ConnectionError

from urlparse import urlparse
from bs4 import BeautifulSoup
from exceptions import Exception

from dateutil.tz import tzutc
from datetime import datetime

from indie_helper.util import follow_redirects

text_types = [ 'text/html' ]

class TooManyRedirects(Exception):
    pass

class InvalidResource(Exception):
    pass

def isonow():
    utcnow = datetime.now(tzutc())
    return datetime(utcnow.year, utcnow.month, utcnow.day, utcnow.hour, utcnow.minute).isoformat()

def make_response(source, target, state, res, reason, extra={}):
    response = {
        'source': source,
        'target': target,
        'verified': {
            'state': bool(state),
            'status_code': getattr(res, 'status_code', None),
            'reason': reason,
            'last_checked': isonow()
            
        }
    }
    response.update(extra)
    return response

def _failure(update_state, source, target, res, reason):
    meta =  make_response(source, target, False, res, reason)
    update_state(state='FAILURE', meta=meta)
    return meta
        
def validate(source, target, **kwargs):
    # raise exception if a problem with the target, as there is no
    # reason to proceed return failure status for valid target but
    # invalid source, as this can be used to periodically update
    # existing webmentions

    managed_hosts = kwargs.get('managed_hosts', None)
    validate_target = kwargs.get('validate_target', True)
        
    def update_state(*args, **kwargs):
        pass
        
    if 'update_state' in kwargs.keys():
        fn = kwargs.get('update_state')
        if callable(fn):
            update_state = lambda state: fn(state=state, meta={'source': source, 'target': target})

    failure = lambda res, reason: _failure(update_state, source, target, res, reason)

    update_state('PROCESSING')
        
    #is target a valid resource belonging to me?
    real_target = None
    acc = []
    if validate_target:    
        update_state('CHECKING_TARGET')
        try:
            acc = follow_redirects(target, 10)
        except requests.ConnectionError:
            #return failure(res, 'Connection error')
            raise InvalidResource('invalid target resource')
        else:
            final_target = acc[-1]
            real_target = final_target['url']
            target = acc
            if final_target['status_code'] != 200:
                print('target "{0}" got [{1}]'.format(target, res.status_code))
                raise InvalidResource('Target not available')
            #does target belong to me?
        url_parts = urlparse(real_target)
        if managed_hosts is not None and url_parts.hostname not in managed_hosts:
            #print('{0} not in {1}'.format(url_parts.hostname, managed_hosts))
            raise InvalidResource('I do not manage {0}'.format(acc[0]['url']))
            #return failure(res, 'I do not manage this target')
        

    #does source exist
    update_state('RETREIVING_SOURCE')
    try:
        r = requests.get(source)
    except ConnectionError:
        return failure(None, 'unable to retreive source')
    else:
        if r.status_code != 200:
            return failure(r, 'unable to retreive source')

    #is source textual?
    if r.headers['content-type'].split(';')[0] not in text_types:
        return failure(r, 'source response must be textual, got "{0}"'.format(r.headers['content-type']))

    #does source actually link to target
    update_state('CHECKING_LINKBACK')
    # stole this bit from mf2py.Parser.__init__
    if 'charset' in r.headers.get('content-type', ''):
        content = r.text
    else:
        content = r.content

    soup = BeautifulSoup(content, "html5lib")

    tag = soup.find('a', attrs={'href': target[0]['url']})
    if not tag:
        return failure(r, 'source does not link to target')

    return make_response(source, target, True, r, '', { 'body': content })
