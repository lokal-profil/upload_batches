#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Artwork template production

@todo: Comment on idiocyncrasies of the input json and theneed to look things
up on wikidata.
"""
import batchupload.helpers as helpers
import batchupload.common as common  # temp before this is merged with helper
import batchupload.listscraper as listscraper
import batchupload.csv_methods as csv_methods
from batchupload.make_info import MakeBaseInfo
import os
import pywikibot
import pywikibot.data.sparql as sparql

OUT_PATH = u'connections'
BATCH_CAT = u'Media contributed by Nationalmuseum Stockholm‎'
BATCH_DATE = u'2016-10'
BASE_NAME = u'artwork'
COLLECTION = u'Nationalmuseum'
LANGUAGE_PRIORITY = ('_', 'en', 'sv')


class NatmusInfo(MakeBaseInfo):
    """Construct file descriptions and filenames for Natmus batch upload."""

    def __init__(self):
        """
        Initialise a make_info object.

        @param batch_cat: base_name for maintanance categories
        @param batch_label: label for this particular batch
        """
        # load wikidata info
        self.wd_paintings = NatmusInfo.load_painting_items()

        # handle nsid connections
        self.nsid = {}
        self.uri_ids = {}
        self.load_place_mappings()

        # black-listed values
        self.bad_namn = tuple()  # Artist names which actually mean unknown
        self.bad_date = tuple()  # Date strings which actually mean unknown

        # log file to handle skipped files
        self.logger = []

        super(NatmusInfo, self).__init__(BATCH_CAT, BATCH_DATE)

    @staticmethod
    def test():
        #@todo: kill
        data = NatmusInfo.load_painting_items()
        i=0
        for k, v in data.iteritems():
            if i > 10:
                break
            i += 1
            print k, v

    def log(self, text):
        """
        Add text to logger.

        @param text: text to log
        """
        self.logger.append(text)

    def load_place_mappings(self):
        """Store hard coded list of place to wikidata mappings."""
        self.place_mappings = {
            u'Moskva': 'Q649',
            u'Kina': 'Q29520',
            u'Leiden': 'Q43631',
            u'Frankrike': 'Q142',
            u'Haarlem': 'Q9920',
            u'Danmark': 'Q35',
            u'München': 'Q1726',
            u'Paris': 'Q90',
            u'Italien': 'Q38',
            u'England': 'Q21',
            u'Sverige': 'Q34',
            u'Stockholm': 'Q1754',
            u'Jämtland': 'Q211661',
            u'Fontainebleau': 'Q182872',
            u'Florens': 'Q2044',
            u'Nederländerna': 'Q55',
            u'Rom': 'Q220',
            u'Antwerpen': 'Q12892',
        }

    @staticmethod
    def clean_sparql_output(data, key):
        """
        Takes the sparql output and outputs it as a dict with lists.

        Also converts any entity_urls to Qids.

        @param data: data to clean
        @param key: data value to use as key in the new dict
        @return: dict
        """
        entity_url = u'http://www.wikidata.org/entity/'
        if key not in data[0].keys():
            pywikibot.error(
                u"The expected key '%s' was not present in the sparql output "
                u"keys: %s" % (key, ', '.join(data[0].keys())))
        new_data = {}
        for d in data:
            k = d[key]
            new_data[k] = {}
            for kk, value in d.iteritems():
                value = value.split('|')
                for i, v in enumerate(value):
                    value[i] = v.replace(entity_url, '')
                new_data[k][kk] = value
        return new_data

    @staticmethod
    def load_painting_items():
        """Store all natmus paintings in Wikidata."""
        query = u'''\
# Nationalmuseum import
SELECT ?item ?obj_id (group_concat(distinct ?type;separator="|") as ?types) (group_concat(distinct ?creator;separator="|") as ?creators) (group_concat(distinct ?depicted_person;separator="|") as ?depicted_persons)
WHERE
{
  ?item wdt:P2539 ?obj_id .
  OPTIONAL {
    ?item wdt:P31 ?type .
  }
  OPTIONAL {
    ?item wdt:P170 ?creator .
  }
  OPTIONAL {
    ?item wdt:P180 ?depicted_person .
    ?depicted_person wdt:P31 wd:Q5 .
  }
}
group by ?item ?obj_id
'''
        s = sparql.SparqlQuery()
        data = s.select(query)
        return NatmusInfo.clean_sparql_output(data, 'obj_id')

    def load_data(self, in_file):
        """
        Load the provided data files.

        Outputs a tuple with lido data as a dict and image filenames as a list.

        @param in_file: the path to the metadata file
        @return: (dict, list)
        """
        lido_data = common.open_and_read_file(in_file[0], as_json=True)
        image_files = common.open_and_read_file(in_file[1]).split('\n')
        image_files = common.trim_list(image_files)

        return (lido_data, image_files)

    def load_mappings(self, update=True):
        """
        Load the mapping files and package them appropriately.

        The loaded mappings are stored as self.mappings

        @param update: whether to first download the latest mappings
        """
        # should this actually carry code
        # improve docstring
        pass

    def process_data(self, raw_data):
        """
        Take the loaded data and construct a NatmusItem for each.

        @param raw_data: output from load_data()
        """
        lido_data, image_files = raw_data
        d = {}
        for key, value in lido_data.iteritems():
            potential_images = value['images'].keys()
            matches = set(potential_images) & set(image_files)
            if not potential_images:
                self.log(
                    u"skip_1: "
                    u"%s did not have any associated images in LIDO" % key)
            elif not matches:
                self.log(
                    u"skip_2: "
                    u"%s did not have any associated images on disk" % key)
            elif len(matches) > 1:
                self.log(
                    u"skip_3: "
                    u"%s had multiple matching images: %s"
                    % (key, ', '.join(matches)))
            else:
                try:
                    d[key] = NatmusItem.make_item_from_raw(
                        value, matches.pop(), self)
                except common.MyError as e:
                    self.log(e)

        pywikibot.output(
            "Identified %d valid paintings of %d records" %
            (len(d), len(lido_data)))
        self.data = d

    @staticmethod
    def get_institution(item):
        """
        Identify institution and subcollection based on filename.

        @param item: the metadata for the media file in question
        @return: str
        """
        institution = u'{{Institution:Nationalmuseum Stockholm}}'
        sub_collection = item.get_subcollection()
        if sub_collection:
            institution += u'\n |department           = %s' % sub_collection['link']
        return institution

    def get_creation_place(self, item):
        """
        Return a formatted list of creation places.

        @param item: the metadata for the media file in question
        @return: str
        """
        places = item.get_creation_place()
        if not places:
            return ''

        # find the correctly formatted placenames
        city_links = []
        for p in places:
            p = p.split('(')[0].strip()  # input is "place (country)"
            qid = self.place_mappings.get(p)
            if qid:
                city_links.append(u'{{city|%s}}' % qid)

        return ', '.join(city_links)

    def get_depicted(self, item):
        """
        Return a formatted list of linked depicted people.

        @param item: the metadata for the media file in question
        @return: str
        """
        depicted = item.get_depicted()

        if not depicted:
            return ''

        # identify links related to names
        linked_objects = []
        #@todo
        # something to get links (wikidata or commons) from the returned list
        return u'{{depicted person|%s|style=information field}} ' % \
            '|'.join(linked_objects)

    @staticmethod
    def get_original_description(item):
        """
        Return the description wrapped in an original descriiption template.

        @param item: the metadata for the media file in question
        @return: str
        """
        descr = item.get_description()
        if descr:
            return u'{{Information field' \
                   u'|name={{original caption/i18n|header}}' \
                   u'|value=%s}}' % descr

    def get_qid(self, item):
        """
        Get the wikidata id for an item.

        @param item: the metadata for the media file in question
        @return: str
        """
        qid = ''
        wd_data = self.wd_paintings.get(item.get_obj_id())
        if wd_data:
            qid = wd_data.get('item')[0]
        return qid

    def get_type(self, item):
        """
        Get the object type of an item.

        @param item: the metadata for the media file in question
        @return: str
        """
        typ = ''
        mappings = {  # per Template:I18n/objects
            'Q132137': 'icon',
            'Q3305213': 'painting'
        }

        # get previous wikidata info
        wd_data = self.wd_paintings.get(item.get_obj_id())
        if wd_data:
            types = []
            for t in wd_data.get('types'):
                types.append(mappings.get(t))
            types = common.trim_list(types)
            if len(types) == 1:
                typ = types[0]
            elif len(types) > 1:
                pywikibot.warning(
                    "Found %d matching types for %s" %
                    (len(types), item.get_obj_id()))
        return typ

    def make_info_template(self, item):
        """
        Make a filled in Artwork template for a single file.

        @param item: the metadata for the media file in question
        @return: str
        """
        data = {
            'depicted': self.get_depicted(item),
            'artist': None,  #@todo
            'title': item.get_title(),
            'wikidata': self.get_qid(item),
            'type': self.get_type(item),
            'description': item.get_description(),
            'original_description': NatmusInfo.get_original_description(item),
            'date': None,  #@todo
            'medium': None,  #@todo
            'dimension': item.get_dimensions(),
            'institution': NatmusInfo.get_institution(item),
            'inscriptions': item.get_inscription(),
            'id_link': item.get_id_link(),
            'creation_place': self.get_creation_place(item),
            'source': item.get_source(),
            'permission': None,  #@todo
        }
        return u'''\
{{Artwork
 |other_fields_1       = {depicted}
 |artist               = {artist}
 |title                = {title}
 |wikidata             = {wikidata}
 |object_type          = {type}
 |description          = {description}
 |other_fields_2       = {original_description}
 |date                 = {date}
 |medium               = {medium}
 |dimensions           = {dimension}
 |institution          = {institution}
 |inscriptions         = {inscriptions}
 |accession number     = {id_link}
 |place of creation    = {creation_place}
 |source               = {source}
 |permission           = {permission}
 |other_versions       =
}}'''.format(**data)

    def generate_filename(self, item):
        """
        Produce a descriptive filename for a single media file.

        This method is responsible for identifying the components which
        should be passed through helpers.format_filename().

        @param item: the metadata for the media file in question
        @return: str
        """
        descr = item.generate_filename_descr()
        return helpers.format_filename(descr, COLLECTION, item.obj_id)

    def generate_content_cats(self, item):
        """
        Produce categories related to the media file contents.

        @param item: the metadata for the media file in question
        @return: list of categories (without "Category:" prefix)
        """
        #@todo
        pass

    def generate_meta_cats(self, item, content_cats):
        """
        Produce maintanance categories related to a media file.

        @param item: the metadata for the media file in question
        @param content_cats: any content categories for the file
        @return: list of categories (without "Category:" prefix)
        """
        cats = []
        # main cats
        cats.append(u'Paintings in the Nationalmuseum Stockholm')
        cats.append(self.batch_cat)

        # sub-collection cat
        sub_collection = item.get_subcollection()
        if sub_collection:
            cats.append(sub_collection['cat'])

        #@todo
        #something if depicted should be mapped
        pass

    def get_original_filename(self, item):
        """
        Return the original filename of a media file without file extension.

        @param item: the metadata for the media file in question
        @return: str
        """
        return os.path.splitext(item.image)[0]

    def run(self, in_file, base_name=None):
        """Overload run to add log outputting."""
        super(NatmusInfo, self).run(in_file, base_name)
        if base_name:
            logfile = u'%s.log' % base_name
            common.open_and_write_file(logfile, '\n'.join(self.logger))
            pywikibot.output("Created %s" % logfile)

    @staticmethod
    def handle_args(args):
        """Parse and load all of the basic arguments.

        Need to override the basic argument handler since we want two
        input files. Also construct a base_name option from these

        @param args: arguments to be handled
        @type args: list of strings
        @return: list of options
        @rtype: dict
        """
        options = {
            'in_file': None,
            'base_name': None,
        }
        natmus_options = {
            'lido_file': None,
            'image_files': None,
        }

        for arg in pywikibot.handle_args(args):
            option, sep, value = arg.partition(':')
            if option == '-lido_file':
                natmus_options['lido_file'] = \
                    helpers.convertFromCommandline(value)
            elif option == '-image_files':
                natmus_options['image_files'] = \
                    helpers.convertFromCommandline(value)

        if natmus_options['lido_file'] and natmus_options['image_files']:
            options['in_file'] = \
                (natmus_options['lido_file'], natmus_options['image_files'])
            options['base_name'] = os.path.join(
                os.path.split(natmus_options['lido_file'])[0],
                BASE_NAME)

        return options

    @classmethod
    def main(cls, *args):
        """Command line entry-point."""
        usage = \
            u'Usage:' \
            u'\tpython Batches/Nationalmuseum/make_Natmus_info.py -lido_file:PATH -image_files:PATH -dir:PATH\n' \
            u'\t-lido_file:PATH path to lido metadata file\n' \
            u'\t-image_files:PATH path to image filenames file\n' \
            u'\t-dir:PATH specifies the path to the directory containing a ' \
            u'user_config.py file (optional)\n' \
            u'\tExample:\n' \
            u'\tpython make_info.py -in_file:SMM/metadata.csv -dir:SMM\n'
        super(NatmusInfo, cls).main(usage=usage, *args)


class NatmusItem(object):
    """Store metadata and methods for a single media file."""

    def __init__(self, initial_data):
        """
        Create a NatmusItem item from a dict where each key is an attribute.

        @param initial_data: dict of data to set up item with
        """
        for key, value in initial_data.iteritems():
            setattr(self, key, value)

    @staticmethod
    def make_item_from_raw(entry, image_file, natmus_info):
        """
        Given the raw metadata for an item, construct an NatmusItem.

        @param entry: the raw metadata entry as a dict
        @param natmus_info: the parent NatmusInfo instance
        @return: NatmusItem
        """
        d = entry.copy()
        # skip paintings not in wikidata
        if d['obj_id'] not in natmus_info.wd_paintings.keys():
            raise common.MyError(
                u"skip_4: "
                u"%s did not have any associated wikidata entry" % d['obj_id'])

        # add specific image info
        d['image'] = image_file
        d['photographer'] = d['images'].get(image_file)

        # collect nsid entries
        for k in d['creator'].keys():
            helpers.addOrIncrement(natmus_info.nsid, k, key='freq')
        for s in d['subjects']:
            if s.get('nsid'):
                helpers.addOrIncrement(
                    natmus_info.nsid, s.get('nsid'), key='freq')

        # drop unneded fields
        del d['images']

        return NatmusItem(d)

    @staticmethod
    def language_wrapped_list(attribute):
        """
        Return a language wrapped list for a given attribute.

        @param attribute: the attribute to analyse
        @return: str
        """
        values = []
        for lang in LANGUAGE_PRIORITY:
            if lang in attribute.keys():
                value = attribute[lang]
                if lang != '_':
                    value = u'{{%s|%s}}' % (lang, value)
                values.append(value)
        return u' '.join(values)

    def get_named_creator(self):
        """
        Establish the named creator(s) for use in title.

        A named creator is:
        * Named
        * Not qualified or qualified with P1773
        @todo: Filter out anonymous but unidentified using an enriched anons
        """
        named_creators = []
        for k, v in self.creator.iteritems():
            if not v.get('name'):
                continue
            if 'qualifier' not in v.keys() or v.get('qualifier') == 'P1773':
                named_creators.append(v.get('name'))

        return ' & '.join(named_creators)

    def generate_filename_descr(self):
        """
        Given an item generate an appropriate description for the filename.

        This is made with the title (according to language priority)
        and the named creator(s).

        @return: str
        """
        # determine title
        title = None
        for lang in LANGUAGE_PRIORITY:
            if lang in self.title.keys():
                title = self.title[lang]
                break

        # determine named creator
        named_creators = self.get_named_creator()

        if named_creators:
            return u'%s (%s)' % (title, named_creators)
        return title

    def get_obj_id(self):
        """Return the obj_id."""
        return self.obj_id

    def get_title(self):
        """Return language wrapped titles."""
        return NatmusItem.language_wrapped_list(self.title)

    def get_description(self):
        """Return language wrapped descriptions."""
        return NatmusItem.language_wrapped_list(self.descriptions)

    def get_inscription(self):
        """Return language wrapped inscriptions."""
        return NatmusItem.language_wrapped_list(self.inscriptions)

    def get_depicted(self):
        """Return list of subjects on the image."""
        return self.subjects

    def get_source(self):
        """Given an item produce a source statement."""
        if self.photographer:
            return u'%s / %s' % (self.photographer, COLLECTION)
        else:
            return COLLECTION

    def get_dimensions(self):
        """Return formatted dimensions."""
        measures = []
        for k, v in self.measurements.iteritems():
            data = {
                'unit': v['unit'],
                'width': v['width'] or '',
                'height': v['height'] or '',
                'depth': v['depth'] or '',
            }
            measure = ''
            if k != '_':
                measure = u'{{en|%s}}: ' % k
            measure += u'{{Size|' + \
                u'unit={unit}|width={width}|height={height}|depth={depth}'.format(**data) + \
                u'}}'
            measures.append(measure)
        if not measures:
            return ''
        elif len(measures) == 1:
            return measures[0]
        else:
            return u'\n* %s' % '\n* '.join(measures)

    def get_creation_place(self):
        """Return a list of creation places in Swedish."""
        if not self.creation_place:
            return []
        elif self.creation_place.keys() != ['sv']:
            pywikibot.warning(
                "Found unexpected creation_place language: %s" %
                ', '.join(self.creation_place.keys()))
            return []
        else:
            return self.creation_place['sv'].split(', ')

    def get_id_link(self):
        """Format an accession number link."""
        return u'{{Nationalmuseum Stockholm link |1=%s |2=%s }}' % \
            (self.obj_id, self.inv_nr)

    def get_subcollection(self):
        """Identify subcollection based on filename."""
        mappings = {
            "TiP": {
                'link': u'{{Institution:Institut_Tessin}}',
                'cat': u'Centre culturel suédois'
            },
            "Grh": {
                'link': u'{{Institution:Gripsholm Castle}}',
                'cat': u'Art in Gripsholms slott'
            },
            "Drh": {
                'link': u'[[Drottningholms slott]]',
                'cat': u'Paintings_at_Royal_Domain_of_Drottningholm'
            },
        }
        for k, v in mappings.iteritems():
            if self.image.startswith(k):
                return v

if __name__ == "__main__":
    # run as
    # python Batches/Nationalmuseum/make_Natmus_info.py -lido_file:Batches/Nationalmuseum/processed_lido.json -image_files:Batches/Nationalmuseum/image_files.txt
    NatmusInfo.main()
    #NatmusInfo.test()
