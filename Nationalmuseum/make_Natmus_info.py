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

OUT_PATH = u'connections'
BATCH_CAT = u'Media contributed by Nationalmuseum Stockholm‎'
BATCH_DATE = u'2016-10'
BASE_NAME = u'artwork'
COLLECTION = u'Nationalmuseum'


class NatmusInfo(MakeBaseInfo):
    """Construct file descriptions and filenames for Natmus batch upload."""

    def __init__(self):
        """
        Initialise a make_info object.

        @param batch_cat: base_name for maintanance categories
        @param batch_label: label for this particular batch
        """
        # handle nsid connections
        self.nsid = {}

        # black-listed values
        self.bad_namn = tuple()  # Artist names which actually mean unknown
        self.bad_date = tuple()  # Date strings which actually mean unknown

        # log file to handle skipped files
        self.logger = []

        super(NatmusInfo, self).__init__(BATCH_CAT, BATCH_DATE)

    def log(self, text):
        """
        Add text to logger.

        @param text: text to log
        """
        self.logger.append(text)

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
                d[key] = NatmusItem.make_item_from_raw(
                    value, matches.pop(), self)

        self.data = d

    def make_info_template(self, item):
        """
        Make a filled in Artwork template for a single file.

        @param item: the metadata for the media file in question
        @return: str
        """
        pass

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
        pass

    def generate_meta_cats(self, item, content_cats):
        """
        Produce maintanance categories related to a media file.

        @param item: the metadata for the media file in question
        @param content_cats: any content categories for the file
        @return: list of categories (without "Category:" prefix)
        """
        pass

    def get_original_filename(self, item):
        """
        Return the original filename of a media file.

        This can either consist of returning a particular data field or require
        processing the metadata.

        @param item: the metadata for the media file in question
        @return: str
        """
        return item.image

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

        if named_creators: print named_creators
        return ' & '.join(named_creators)

    def generate_filename_descr(self):
        """
        Given an item generate an appropriate description for the filename.

        This is made with the title (according to language priority)
        and the named creator(s).
        """
        # determine title
        language_priority = ('_', 'en', 'sv')
        title = None
        for lang in language_priority:
            if lang in self.title.keys():
                title = self.title[lang]
                break

        # determine named creator
        named_creators = self.get_named_creator()

        if named_creators:
            return u'%s (%s)' % (title, named_creators)
        return title


if __name__ == "__main__":
    # run as
    # python Batches/Nationalmuseum/make_Natmus_info.py -lido_file:Batches/Nationalmuseum/processed_lido.json -image_files:Batches/Nationalmuseum/image_files.txt
    NatmusInfo.main()
    #NatmusInfo.test()
