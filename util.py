import requests
import bleach
import sys

if sys.version < '3':
    from urlparse import urlparse
    text_type = unicode
    text_types = [ str, unicode ]
    binary_type = str
else:
    from urllib.parse import urlparse
    text_type = str
    text_types = [ str ]
    binary_type = bytes


def is_url(url):
    try:
        parts = urlparse(url)
    except TypeError:
        return False
    return parts.scheme in [ 'http', 'https' ]

def flatten(item):
    if type(item) in [ list, tuple ] and len(item) == 1:
        return item[0]
    else:
        return item

#bleach.ALLOWED_TAGS + ['p']
ALLOWED_TAGS=bleach.ALLOWED_TAGS + ['p', 'span']

def clean(text):
    return bleach.clean(text, tags=ALLOWED_TAGS)

def clean_url(url):
    if url.startswith('javascript:'):
        return '';
    return url

def bleachify(entry, key=None):
    ## todo for each property
    if key == 'url':
        bleached = bleachify(entry)
        return [ clean_url(u) for u in bleached ]
    
    if hasattr(entry, 'items'):
        return dict([ (prop, bleachify(value, prop)) for prop, value in entry.items() ])
    elif type(entry) is list:
        ## to flatten the list-of-one values that mf2py generates
        ## I have revisited this and decided to keep single element lists as this seems to be part of the mf2 defined format
        #if len(entry) == 1:
        #    return bleachify(entry[0])
        #else:
        return map(bleachify, entry)
    elif type(entry) in text_types:
        return clean(entry)
    else:
        print('unhandled type of entry: {0}'.format(type(entry)))
        return None

def follow_redirects(url, max_depth):
    """perform http GET url, following any redirects up to max_depth.
    return resolved url. 
    Raises TooManyRedirects exception if max_depth is exceeded"""
    
    def _wrapped(url, depth, acc):
        if depth > max_depth:
            raise TooManyRedirects('following redirects on {0} exceeded maximum depth of {1}'.format(url, max_depth))
        
        r = requests.head(url)
        acc.append( { 'url': url, 'status_code': r.status_code} )
        if r.status_code in [ 301, 302 ]:
            return _wrapped(r.headers['Location'], depth+1, acc)
        else:
            return acc

    return _wrapped(url, 0, [])
