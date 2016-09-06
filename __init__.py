import mf2py
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

def first_entry(p, htype='h-entry'):
    try:
        return filter(lambda i: htype in i['type'], p['items'])[0]
    except IndexError:
        return None

def first_card(p):
    card = first_entry(p, 'h-card')

    if card is None:
        return filter(lambda rel: rel == 'me', p['rels'].items())
    return card

def url_from_entry(url_or_entry):
    if hasattr(url_or_entry, 'keys') and 'properties' in url_or_entry.keys():
        return url_or_entry['properties']['url']
    else:
        return url_or_entry

def is_hcard(entry):
    return hasattr(entry, "get") and 'h-card' in entry.get("type", "")

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
    if type(prop) in [ str, text_type ]:
        return prop
    else:
        ## Will probably need to do exception handling
        return prop['properties']['url']

def flatten(item):
    if type(item) in [ list, tuple ] and len(item) == 1:
        return item[0]
    else:
        return item
    
def in_reply_to(mfdata):
    entry = first_entry(mfdata)

    reply_tos = []
    if entry is not None:
        reply_tos = list(set([ flatten(follow_url(p)) for p in entry['properties'].get('in-reply-to', []) ]))

    if len(reply_tos) == 0:
        # get any reply-to in rel
        reply_tos = mfdata['rels'].get('in-reply-to', [])
        
    return reply_tos
    
def author_of_entry(entry):
    if entry is None:
        return None
    try:
        return entry['properties']['author']
    except KeyError:
        None    

def author_card(entry, rels):
    ## TODO: implement authorship algorithm from indieweb
    pass

#bleach.ALLOWED_TAGS + ['p']
ALLOWED_TAGS=bleach.ALLOWED_TAGS + ['p']

def clean(text):
    return bleach.clean(text, tags=ALLOWED_TAGS)

def bleachify(entry):
    ## todo for each property
    if hasattr(entry, 'items'):
        return dict([ (prop, bleachify(value)) for prop, value in entry.items() ])
    elif type(entry) is list:
        ## to flatten the list-of-one values that mf2py generates
        if len(entry) == 1:
            return bleachify(entry[0])
        else:
            return map(bleachify, entry)
    elif type(entry) in text_types:
        return clean(entry)
    else:
        print('unhandled type of entry: {0}'.format(type(entry)))
        return None
    
def mention_from_url(url):
    mfdata = mf2py.parse(url=url, html_parser="html5lib")
    return _mention(mfdata)

def mention_from_doc(doc):
    mfdata = mf2py.parse(doc=doc, html_parser="html5lib")
    return _mention(mfdata)

def _mention(mfdata):
    entry = bleachify(first_entry(mfdata))

    #if "content" in entry["properties"].keys():
    #    content = entry["properties"]["content"][0]["html"]
    #    entry["properties"]["content"] = [{ "html": bleach.clean(content) }]

    
    mention = {
        'mention': entry,
        'in-reply-to': in_reply_to(mfdata),
    }

    author = author_of_entry(entry)
    if author is None:
        mention['author'] = bleachify(first_card(mfdata))
    elif is_hcard(author):
        # TODO: does it make sense to duplicate content here, author
        # is already in the entry always putting it on the author
        # property makes client side easier. We could strip it from
        # the entry if found...?
        mention['mention']['properties']['author'] = author
    elif is_url(author):
        mention['mention']['properties']['author-page'] = author

    return mention
        

if __name__ == '__main__':
    import sys

    url = sys.argv[1]

    mention = mention_from_url(url)
    print(mention)
