import mf2py

try:
    # python 2
    from urlparse import urlparse
except ImportError:
    # python 3
    from urllib.parse import urlparse

def parse(url):
    return mf2py.parse(url=url, html_parser="html5lib")

def first_entry(p, htype='h-entry'):
    try:
        return filter(lambda i: htype in i['type'], p['items'])[0]
    except IndexError:
        return None

def first_card(p):
    card = first_entry(p, 'h-card')

    if card is None:
        return filter(lambda rel: rel[0] == 'me', p['rels'].items())
    return card

def url_from_entry(url_or_entry):
    if hasattr(url_or_entry, 'keys') and 'properties' in url_or_entry.keys():
        return url_or_entry['properties']['url'][0]
    else:
        return url_or_entry

def is_url(url):
    parts = urlparse(url)
    return parts.scheme in [ 'http', 'https' ]

def is_hcard(entry):
    return hasattr(entry, "get") and entry.get("type", "") == "h-card"

def entry_from_url(url):
    assert(is_url(url))
    entry = { u'properties': { u'url': [url] } }
    #properties = { 'url': url }
    e, rels = first_entry(url)
    if e is not None:
        entry['properties'].update(e['properties'])
    #if e is not None:
    #    properties.update(e['properties'])
    return entry, rels

def follow_url(prop):
    if type(prop) in [ str, unicode ]:
        return prop
    else:
        ## Will probably need to do exception handling
        return prop['properties']['url'][0]
    
def in_reply_to(mfdata):
    entry = first_entry(mfdata)

    reply_tos = []
    if entry is not None:
        reply_tos = list(set([ follow_url(p) for p in entry['properties'].get('in-reply-to', []) ]))

    if len(reply_tos) == 0:
        # get any reply-to in rel
        reply_tos = mfdata['rels'].get('in-reply-to', [])
        
    return reply_tos

def url_of_entry(entry):
    if entry is None:
        return None
    props = entry['properties']
    return props.get('uri', props.get('url', [None]))[0]
    
def author_of_entry(entry):
    if entry is None:
        return None
    try:
        return entry['properties']['author'][0]
    except KeyError:
        None    

def author_card(entry, rels):
        author = extract_author(entry, rels)
        # if author looks like a url, extract it to find an h_card

def mention_from_url(url):
    mfdata = parse(url)
    card = first_card(mfdata)
    entry = first_entry(mfdata)

    mention = {
        'mention': entry,
        'in-reply-to': in_reply_to(mfdata),
    }

    author = author_of_entry(entry)
    if author is None:
        mention['author'] = None
    elif is_hcard(author):
        mention['author'] = author
    elif is_url(author):
        mention['author-page'] = author

    return mention
        

if __name__ == '__main__':
    import sys

    url = sys.argv[1]

    mention = mention_from_url(url)
    print(mention)
