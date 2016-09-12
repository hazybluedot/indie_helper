import requests
import json
import mf2py

from pytz import timezone
from urlparse import urlparse
from dateutil.tz import tzutc
from datetime import datetime
from slugify import slugify

from indie_helper import mention_from_url, mention_from_doc

# patch JSON encoder to handle datetime objects, see http://stackoverflow.com/questions/455580/json-datetime-between-python-and-javascript#3235787
json.JSONEncoder.default = lambda self,obj: (obj.isoformat() if hasattr(obj, 'isoformat') else None)

def isonow():
    utcnow = datetime.now(tzutc())
    return datetime(utcnow.year, utcnow.month, utcnow.day, utcnow.hour, utcnow.minute).isoformat()

def post_id_from_url(url):
    u = urlparse(url)
    return u.path.split('/')[-1]

def publish(source, target, endpoint, **kwargs):
    now = isonow() #datetime.now(timezone('UTC'))
    post_id = post_id_from_url(target)

    data = kwargs.get('data', {})
    verified = data['verified'].get('state', False)
    
    _id = slugify(u'mention-{0}'.format(source))
    
    _endpoint = endpoint.format(_id)

    mentions = {}
    if verified:
        content = kwargs.get('body', None)
        if content is not None:
            mentions = mention_from_doc(content)
        else:
            mentions = mention_from_url(source)
        
    data.update({
        '_id': _id, 
        'post_id': post_id,
        'type': 'mention',
        'format': 'mf2py'
    })

    data.update(mentions)
    
    r = requests.get(_endpoint)
    if r.status_code == 200:
        current = r.json()

        unchanged_since = None
        if all([ 'verified' in d.keys() for d in [ data, current ]]):
            if data['verified']['state'] == current['verified']['state']:
                last_checked = current['verified']['last_checked']
                unchanged_since = current['verified'].get('unchanged_since', last_checked)
                print('setting unchanged_since to {0}'.format(unchanged_since))
            else:
                unchanged_since = now
                
        current.update(data)
        if unchanged_since is not None:
            current['verified']['unchanged_since'] = unchanged_since
        current['updated_at'] = now
        data = current
    else:
        data['created_at'] = now
            
    #print('PUT {0}'.format(endpoint))
    #print('data: {0}'.format(json.dumps(data)))
    r = requests.put(_endpoint, json.dumps(data))
    if r.status_code not in [ 201, 202 ]:
        print('PUT {0} [{1}] ({2})'.format(_endpoint, r.status_code, r.text))
