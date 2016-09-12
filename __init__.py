import mf2py
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


from indie_helper.util import is_url, flatten, bleachify

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
    return hasattr(entry, "get") and 'h-card' in entry.get("type", [])

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

def closest_url(prop):
    if hasattr(prop, 'get') and prop.get('type', None) == 'h-cite':
        return prop['properties']['url']
    elif type(prop) in [ str, text_type ] and is_url(prop):
        return prop
    else:
        ## Will probably need to do exception handling
        return None
    
def in_reply_to(mfdata):
    entry = first_entry(mfdata)
    
    reply_tos = []
    if entry is not None:
        reply_tos = list(set([ flatten(closest_url(p)) for p in entry['properties'].get('in-reply-to', []) ]))

    if len(reply_tos) == 0:
        # get any reply-to in rel
        reply_tos = mfdata['rels'].get('in-reply-to', [])
        
    return reply_tos

author_by_type = {
    'h-card' : lambda card: { },
    'h-cite' : lambda card: { }
}

def author_of_url(url):
    mfdata = mf2py.parse(url=url, html_parser="html5lib")
    return first_card(mfdata) # TODO: filter for rel=me

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
