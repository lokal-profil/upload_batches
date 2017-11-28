#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Isolate relevant information from Lido XML files and dump to local json

Any unrecognized LIDO tags are flagged so that they can be processed later.

run as python Batches/Nationalmuseum/pre_process.py
"""
import argparse

import batchupload.common as common  # temp before this is merged with helper
import batchupload.prepUpload as prep
import os
import sys
import pywikibot
import xmltodict
from collections import OrderedDict

MAIN_DIR = '.'
XML_DIR = 'data/'

REPOSITORY_VIAF = "http://viaf.org/viaf/147742988"


def load_xml(filename):
    """
    Load the data from an xml file.

    @param filename: the path to the file to open
    @return: dict
    """
    # Given the path to a xml file
    # open and load as xml before returning data
    data = xmltodict.parse(common.open_and_read_file(filename))
    data['source_file'] = os.path.split(filename)[-1]
    return data


def process_all_files(base_dir=MAIN_DIR, xml_dir=XML_DIR):
    """Identify all xml files in a directory, load the data and process."""
    # Check categories
    xml_dir = os.path.join(base_dir, xml_dir)
    for dr in (base_dir, xml_dir):
        if not os.path.isdir(dr):
            raise common.MyError(
                'The provided directory is not a valid directory: {}'.format(dr))

    # Find candidate files
    found_files = prep.find_files(
        path=xml_dir, file_exts=('.xml', ), subdir=False)
    pywikibot.output("Found {} .xml files".format(len(found_files)))
    data = {}
    for xml_file in found_files:
        test = InfoEntry(load_xml(xml_file))
        # try:
        #     test = InfoEntry(load_xml(xml_file))
        # except Exception as e:
        #     message = os.path.split(xml_file)[-1]
        #     pywikibot.output(
        #         "Encountered error while processing {} : {}".format(message,
        #                                                             e))
        #     continue
        if test.obj_id in data.keys():
            pywikibot.output(
                "Multiple files for same object: %s, %s, %s" % (
                    test.obj_id, test.source_file,
                    data[test.obj_id]['source_file']))
            continue
        data[test.obj_id] = test.output()

    out_file = os.path.join(base_dir, 'processed_lido_2.json')
    common.open_and_write_file(out_file, data, as_json=True)
    pywikibot.output("Created {} with {} entries".format(out_file, len(data)))


def get_lang_values_from_set(value_list, subtags=None):
    """
    Given a listified result return any non-empty language fields.

    If no language can be identified '_' is used.

    @param value_list: list of values to analyse
    @param subtags: the subtag(s) under the value where the data is expected
        must be a tuple if provided with each subsequent tag being one level
        deeper
    @return: dict
    """
    unknown = '_'
    result = {}
    for value_entry in value_list:
        if subtags:
            for tag in subtags:
                if list(value_entry.keys()) != [tag]:  # expect no other subtag
                    pywikibot.output(
                        "Found unexpected tags: %s"
                        % ', '.join(value_entry.keys()))
                    exit()
                value_entry = value_entry[tag]

        # skip empty entries
        if not value_entry:
            continue
        if isinstance(value_entry, str):
            # some values are not language tagged
            result[unknown] = value_entry
        else:
            value = value_entry.get('#text')
            if value:
                lang = value_entry.get('@xml:lang') or unknown
                if lang in result.keys() and value != result[lang]:
                    pywikibot.warning(
                        "Found double entries for the same language: %s <-> %s"
                        % (value, result[lang]))
                result[lang] = value
    return result


def flag_missed_tags(data, level, handled, skipped):
    """Highlight any tags which have not been considered."""
    missed = list(set(data.keys()) - set(handled + skipped))
    if missed:
        pywikibot.output(u"Missed the following tags on level '%s': %s" % (
                         level, u', '.join(missed)))


def handle_actor(actor):
    """Handle an entry on lido:actor level."""
    unknowns = ('Okänd', )
    result = {}
    if actor['lido:actorID']['@lido:type'] == 'Nationalmuseum Sweden artist ID; NSID':
        result['nsid'] = actor['lido:actorID']['#text']
    else:
        result['other_id'] = actor['lido:actorID'][u'#text']
    name = actor['lido:nameActorSet']['lido:appellationValue']
    if name in unknowns:
        name = None
    result['name'] = name
    return result


class InfoEntry(object):
    """A store for the data extracted from a single xml file."""

    def __init__(self, xml_data, debug=False):
        """Construct an info object from the loaded xml data."""
        # define any internals
        self.source_file = xml_data['source_file']
        self.raw_data = xml_data
        self.debug = debug

        # for debugging
        self._debug(self.source_file)

        # populate data
        self.process_lido_xml(xml_data['lido:lidoWrap']['lido:lido'])

    def _debug(self, text):
        """Output if debug flag is set."""
        if self.debug:
            pywikibot.output(text)

    def output(self):
        return {
            'source_file': self.source_file,
            'inv_nr': self.inv_nr,
            'obj_id': self.obj_id,
            'image_license': self.image_license,
            'images': self.images,
            'title': self.titles,
            'inscriptions': self.inscriptions,
            'descriptions': self.descriptions,
            'measurements': self.measurements,
            'techniques': self.techniques,
            'creation_place': self.creation_place,
            'creation_date': self.creation_date,
            'creator': self.creator,
            'subjects': self.subjects,
        }

    def process_lido_xml(self, data):
        """Populate entry data given the loaded xml at lido:lido level."""
        handled_tags = list()
        skipped_tags = ['lido:lidoRecID', ]

        # add inv_nr
        handled_tags.append('lido:repositoryWrap')

        handled_tags.append('lido:administrativeMetadata')
        self.add_admin_data(data['lido:administrativeMetadata'])

        # # handle descriptive metadata
        handled_tags.append(u'lido:descriptiveMetadata')
        self.add_descriptive_data(data[u'lido:descriptiveMetadata'])

        # flag_missed_tags(data, '', handled_tags, skipped_tags)

    def add_admin_data(self, data):
        handled_tags = list()
        skipped_tags = ['lido:rightsWorkWrap', '@xml:lang']
        tag = 'lido:administrativeMetadata'

        # set obj_id
        handled_tags.append('lido:recordWrap')
        recordID = data['lido:recordWrap']['lido:recordID']
        self.obj_id = recordID['#text']

        # # add image data
        handled_tags.append('lido:resourceWrap')
        self.add_image_data(data['lido:resourceWrap']['lido:resourceSet'])

        # flag_missed_tags(data, tag, handled_tags, skipped_tags)

    def add_image_data(self, data):
        handled_tags = list()
        skipped_tags = ['', ]
        tag = 'lido:resourceWrap/lido:resourceSet'

        # identify filenames
        handled_tags.append('lido:resourceRepresentation')
        self.images = {}
        images = []
        # identify local images
        links = data['lido:resourceRepresentation']
        for link in links:
            if isinstance(link['lido:linkResource'], str) and link['lido:linkResource'].startswith('http'):
                continue
            if link['lido:linkResource'].get('@lido:formatResource'):
                if link['lido:linkResource']['@lido:formatResource'] == "tiff" or link['lido:linkResource']['@lido:formatResource'] == "tif":
                    filename = link['lido:linkResource']['#text']
                    images.append(filename)

        # match image to attributions
        handled_tags.append('lido:rightsResource')
        attributions = common.listify(
            data['lido:rightsResource'].get('lido:rightsHolder'))
        if attributions:
            if len(attributions) != len(images):
                pywikibot.warning(
                    "image-attribution missmatch in %s" % self.source_file)
            for i, attribution in enumerate(attributions):
                self.images[images[i]] = attribution[
                    'lido:legalBodyName']['lido:appellationValue']
            # nån logik som ser till att det inte blir fel ibland
        else:
            # there aren't always photographers
            for i, image in enumerate(images):
                self.images[images[i]] = None

        # add license, just in case
        self.image_license = data['lido:rightsResource'][
            'lido:rightsType']['lido:term']['#text']

        # flag_missed_tags(data, tag, handled_tags, skipped_tags)

    def add_descriptive_data(self, data):
        handled_tags = list()
        skipped_tags = ['lido:objectClassificationWrap', '@xml:lang']
        tag = 'lido:descriptiveMetadata'

        # add identification data
        handled_tags.append('lido:objectIdentificationWrap')
        self.add_identification_data(data['lido:objectIdentificationWrap'])

        # add event data
        handled_tags.append('lido:eventWrap')
        self.add_event_data(
            common.listify(data['lido:eventWrap']['lido:eventSet']))

        # add relation data
        handled_tags.append('lido:objectRelationWrap')
        self.add_relation_data(data['lido:objectRelationWrap'])

        # flag_missed_tags(data, tag, handled_tags, skipped_tags)

    def add_identification_data(self, data):
        handled_tags = list()
        skipped_tags = ['', ]
        tag = 'lido:objectIdentificationWrap'

        # add title
        handled_tags.append('lido:titleWrap')
        titles = common.listify(data['lido:titleWrap']['lido:titleSet'])
        self.titles = get_lang_values_from_set(
            titles, ('lido:appellationValue', ))

        # add incription
        handled_tags.append('lido:inscriptionsWrap')
        inscriptions = common.listify(
            data['lido:inscriptionsWrap']['lido:inscriptions'])
        self.inscriptions = get_lang_values_from_set(
            inscriptions, ('lido:inscriptionTranscription', ))

        # add decription
        handled_tags.append('lido:objectDescriptionWrap')
        description_set = data['lido:objectDescriptionWrap'][
            'lido:objectDescriptionSet']
        if not isinstance(description_set, OrderedDict):
            pywikibot.warning(
                "Weird things are happening in description field for {}:\n{}".format(self.source_file, description_set))
        descriptions = common.listify(
            description_set['lido:descriptiveNoteValue'])
        self.descriptions = get_lang_values_from_set(descriptions)

        # add measurements
        handled_tags.append('lido:objectMeasurementsWrap')
        measurement_set = data['lido:objectMeasurementsWrap'][
            'lido:objectMeasurementsSet']
        if set(measurement_set.keys()) - set(['lido:displayObjectMeasurements', 'lido:objectMeasurements']):
            pywikibot.warning(
                "Weird things are happening in measurement field for {}:\n{}".format(self.source_file, measurement_set))
        self._debug(measurement_set.get('lido:displayObjectMeasurements'))
        measurements = common.trim_list(common.listify(
            measurement_set.get('lido:displayObjectMeasurements')))
        self._debug(measurements)
        self.add_measurements(measurements)

        # ensure location is always Nationalmuesum
        handled_tags.append('lido:repositoryWrap')
        rep_sets = data['lido:repositoryWrap']['lido:repositorySet']
        for rep in rep_sets:
            if rep.get('lido:workID'): # set inventarienummer
                self.inv_nr = rep['lido:workID']['#text']
            if rep.get('@lido:type') and rep['@lido:type'] == "current":
                viaf = rep["lido:repositoryName"]["lido:legalBodyID"]["#text"]
                if viaf != REPOSITORY_VIAF:
                    pywikibot.warning(
                        "Unexpected repository in {} : {}".format(self.source_file, repository_viaf))
        # flag_missed_tags(data, tag, handled_tags, skipped_tags)

    def add_measurements(self, measurements):
        recognised_units = ('cm', 'mm')
        recognied_prefixes = {
            '_': '_',
            'Mått': '_',
            'Ram': 'Framed',
        }
        skipped_prefixes = (
            'Vikt', 'Trpram', 'Spännram', 'Montering', 'Yttermått',
            'Rymd', 'Passepartout')
        self.measurements = {}
        if not measurements:
            return

        for measurement in measurements:
            parts = measurement.split(' ')
            # interpret numeric first part as there being no prefix
            if parts[0].strip('0123456789,') == '':
                parts.insert(0, '_')

            # handle prefix
            if parts[0] not in recognied_prefixes.keys():
                if parts[0] not in skipped_prefixes:
                    pywikibot.warning(
                        "Unrecognized prefix in measurement for {} : \n{}".format(self.source_file, measurement))
                continue
            if parts[0] in self.measurements.keys():
                pywikibot.warning(
                    "Reused prefix in measurement for {} :\n{}".format(self.source_file, measurement))
                continue

            # handle units
            if parts[-1] not in recognised_units:
                # try an inteligent guess for unit placement
                if len(parts) > 2 and parts[2] in recognised_units:
                    # one values (normally indicates a comment)
                    continue
                elif len(parts) > 4 and parts[4] in recognised_units:
                    # two values
                    parts = parts[:5]
                elif len(parts) > 6 and parts[6] in recognised_units:
                    # three values
                    parts = parts[:7]
                else:
                    pywikibot.warning(
                        "Unrecognized unit in measurement for %s:\n%s"
                        % (self.source_file, measurement))
                    continue

            # rejoin numbers and use english decimal sign
            values = ''.join(parts[1:-1]).replace(',', '.')
            values = values.split('x')
            if len(values) not in (1, 2, 3):
                pywikibot.warning(
                    "Unexpected formating of measurement for %s:\n%s"
                    % (self.source_file, measurement))
            else:
                key = recognied_prefixes[parts[0]]
                self.measurements[key] = {
                    'unit': parts[-1],
                    'height': values[0],
                    'width': None,
                    'depth': None
                }
                if len(values) >= 2:
                    self.measurements[key]['width'] = values[1]
                if len(values) == 3:
                    self.measurements[key]['depth'] = values[2]

    def add_event_data(self, events):
        # print("adding event data")
        creation_concept = 'http://terminology.lido-schema.org/lido00012'
        recognised_concepts = {
            'creation': creation_concept,
            'acquisition': 'http://terminology.lido-schema.org/lido00001'
        }

        found_creation = False
        for event in events:
            concept = event['lido:event'][
                'lido:eventType']['lido:conceptID']['#text']
            if concept not in recognised_concepts.values():
                pywikibot.warning(
                    "Unrecognized event concept for %s: %s"
                    % (self.source_file, concept))
            elif concept == creation_concept:
                if found_creation:
                    pywikibot.warning(
                        "Multiple creation events for %s" % self.source_file)
                found_creation = True
                self.add_creation(event['lido:event'])

        if not found_creation:
            pywikibot.warning(
                "No creation event for %s" % self.source_file)

    def add_creation(self, event):
        handled_tags = list()
        skipped_tags = ['lido:eventName', 'lido:eventType']
        tag = 'lido:event'
        # print("adding creation....")

        # add creator(s)
        handled_tags.append('lido:eventActor')
        self.creator = {}
        self.handle_creators(
            common.trim_list(common.listify(event['lido:eventActor'])))
        # print(self.creator)


        # add creation_date
        # print("adding creation date")
        handled_tags.append('lido:eventDate')
        self.creation_date = {}
        if event.get('lido:eventDate'):
            try:
                self.creation_date['earliest'] = event['lido:eventDate'][
                    'lido:date'].get('lido:earliestDate')
                self.creation_date['latest'] = event['lido:eventDate'][
                    'lido:date'].get('lido:latestDate')
                self.creation_date['text'] = get_lang_values_from_set(
                    common.listify(event['lido:eventDate']['lido:displayDate']))
            except TypeError:
                print("")

        # print("added creation date")

        # add creation place
        handled_tags.append('lido:eventPlace')
        try:
            self.creation_place = get_lang_values_from_set(
                common.listify(
                    event['lido:eventPlace']['lido:place']['lido:namePlaceSet']),
                ('lido:appellationValue', ))
        except:
            self.creation_place = ""

        # print("added creation place")

        # add materialtech
        handled_tags.append('lido:eventMaterialsTech')
        self.techniques = get_lang_values_from_set(
            common.listify(event['lido:eventMaterialsTech']),
            ('lido:materialsTech', 'lido:termMaterialsTech', 'lido:term'))

        flag_missed_tags(event, tag, handled_tags, skipped_tags)

    def handle_creators(self, actors):
        # print("handling creators")
        creator_roles = ('Konstnär', 'Utförd av', 'Komp. och utförd av')
        skipped_roles = (
            'Tidigare attribution', 'Medarbetare',
            'Alternativ tillskrivning', 'Beställare')
        qualified_roles = ('Attribuerad till', 'Kopia efter',
                           'Fri kopia efter', 'Efter')
        all_roles = (creator_roles + skipped_roles + qualified_roles)
        qualifiers = {
            'Tillskriven': 'P1773',
            'Attribuerad till': 'P1773',
            'Hennes ateljé': 'P1774',
            'Hans ateljé': 'P1774',
            'Hennes skola': 'P1780',
            'Hans skola': 'P1780',
            'Hennes art': 'P1777',
            'Hans art': 'P1777',
            'Kopia efter': 'P1877',
            'Fri kopia efter': 'P1877',
            'Efter': 'P1877',
            'Osäker attribution': None,
            'Alternativ attribution': None,
        }

        for actor in actors:
            if list(actor.keys()) != ['lido:actorInRole', ]:
                pywikibot.warning(
                    "Unexpected actor tag for {}:\n{}".format(self.source_file,
                                                              actor))
                continue


            # check role
            actor_role = actor['lido:actorInRole'][
                'lido:roleActor']['lido:term'].get('#text')

            if not actor_role:
                continue  # empty entry
            elif actor_role not in all_roles:
                warn_cont = actor['lido:actorInRole']['lido:roleActor']
                pywikibot.warning(
                    "Unexpected actor role for {} :\n{}".format(self.source_file,
                                                         warn_cont))
                continue
            elif actor_role in skipped_roles:
                continue



            # check qualifier
            qualifier = actor['lido:actorInRole'].get(
                    'lido:attributionQualifierActor')
            if qualifier and qualifier not in qualifiers:
                pywikibot.warning(
                    "Unhandled actor qualifier for {}:\n{}".format(self.source_file,
                                                                   qualifier))
                continue


            actor_info = handle_actor(
                actor['lido:actorInRole']['lido:actor'])


            # handle any direct or inidrect qualifies
            if actor_role in qualified_roles:
                qualifier = actor_role
            if qualifier:
                actor_info['qualifier'] = qualifiers[qualifier]

            # crash if no nsid
            nsid = actor_info['nsid']
            self.creator[nsid] = actor_info
            # print(self.creator)
            # print("added creator!!!!!!!!!!!!!!!!!!")

    def add_relation_data(self, data):
        handled_tags = list()
        skipped_tags = ['', ]
        tag = u'lido:objectRelationWrap'

        # handle subjects
        handled_tags.append(u'lido:subjectWrap')
        self.subjects = list()
        subjects = data[u'lido:subjectWrap'][
            u'lido:subjectSet'][u'lido:subject']
        if subjects:
            subjects = common.listify(subjects[u'lido:subjectActor'])
            for subject in subjects:
                self.subjects.append(
                    handle_actor(subject[u'lido:actor']))

        flag_missed_tags(data, tag, handled_tags, skipped_tags)


def main(args):
    process_all_files(xml_dir=args.datadir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--datadir", default="test_data")
    args = parser.parse_args()
    main(args)
