import requests
import json
import mf2py

from pytz import timezone
from urlparse import urlparse
from dateutil.tz import tzutc
from datetime import datetime
from slugify import slugify

from indie_helper import mention_from_url, mention_from_doc
from indie_helper.util import bleachify

# patch JSON encoder to handle datetime objects, see http://stackoverflow.com/questions/455580/json-datetime-between-python-and-javascript#3235787
json.JSONEncoder.default = lambda self,obj: (obj.isoformat() if hasattr(obj, 'isoformat') else None)

def isonow():
    utcnow = datetime.now(tzutc())
    return datetime(utcnow.year, utcnow.month, utcnow.day, utcnow.hour, utcnow.minute).isoformat()

def post_id_from_url(url):
    u = urlparse(url)
    return u.path.split('/')[-1]


def update_record(endpoint, data):
    now = isonow() #datetime.now(timezone('UTC'))
    r = requests.get(endpoint)
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
    r = requests.put(endpoint, json.dumps(data))
    return {
        'endpoint': endpoint,
        'response': r
    }
    
def publish(source, target, endpoint, **kwargs):
    data = kwargs.get('data', {})
    data['_id'] = slugify(u'mention-{0}'.format(source))

    verified = data['verified'].get('state', False)

    if isinstance(target, list):
        real_target = target[-1]['url']
    else:
        real_target = data.pop('real_target', target)
    post_id = post_id_from_url(real_target)

    if verified:
        content = kwargs.get('body', None)
        if content is not None:
            mfdata = mf2py.parse(doc=content, html_parser="html5lib")
            #mentions = mention_from_doc(content)
        else:
            mfdata = mf2py.parse(url=url, html_parser="html5lib")
            #mentions = mention_from_url(source)

    mfdata['items'] = [ bleachify(item) for item in mfdata['items'] ]
    
    data.update({
        'post_id': post_id,
        'type': 'mention',
        'format': 'mf2py'
    })

    data['data'] = mfdata

    res = update_record(endpoint.format(data['_id']), data)
    return res
