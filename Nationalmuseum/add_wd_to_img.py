import pywikibot
from pywikibot import pagegenerators as pg
import mwparserfromhell as parser
import wikidataStuff.wdqsLookup as lookup

site = pywikibot.Site("commons", 'commons')
catname = "Media contributed by Nationalmuseum Stockholm: connect to wikidata item"
ARTWORK_ID = "P2539"
cat = pywikibot.Category(site, catname)
gen = pg.CategorizedPageGenerator(cat)


def fetch_artworks():
    items = {}
    query = (
        "SELECT DISTINCT ?item ?value "
        "WHERE { ?item wdt:%s ?value }" % ARTWORK_ID
    )
    data = lookup.make_simple_wdqs_query(query, verbose=False)
    for x in data:
        key = lookup.sanitize_wdqs_result(x['item'])
        value = x['value']
        items[value] = key
    print("FOUND {} WD ITEMS WITH PROP {}".format(len(items), ARTWORK_ID))
    return items


def add_q(text, q):
    parsed = parser.parse(text)
    templates = parsed.filter_templates()
    for t in templates:
        if t.name.matches("Artwork"):
            t.add("wikidata", q)
            text = str(parsed).replace("[[Category:Media contributed by Nationalmuseum Stockholm‎: connect to wikidata item]]", "")
            return text


def main():
    on_wd = fetch_artworks()
    for page in gen:
        parsed = parser.parse(page.text)
        templates = parsed.filter_templates()
        for t in templates:
            if t.name.matches("Nationalmuseum Stockholm link"):
                artwork_id = str(t.get(1).value)
                if on_wd.get(artwork_id):
                    q = on_wd.get(artwork_id)
                    print("artwork_id: {}".format(artwork_id))
                    print(q)
                    page.text = add_q(page.text, q)
                    page.save("connecting to wd item {}.".format(q))


if __name__ == '__main__':
    main()
