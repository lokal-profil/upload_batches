#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Isolate relevant information from Lido XML files and dump to local json

Any unrecognized LIDO tags are flagged so that they can be processed later.

run as python Batches/Nationalmuseum/pre_process.py
"""
import batchupload.common as common  # temp before this is merged with helper
import batchupload.prepUpload as prep
import os
import pywikibot
import xmltodict
from collections import OrderedDict

MAIN_DIR = u'Batches/Nationalmuseum/'
XML_DIR = u'LIDO XML/valid_items_transform_1618/16-09-07_14_46_28/'


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
    for directory in (base_dir, xml_dir):
        if not os.path.isdir(directory):
            raise common.MyError(
                u'The provided directory was not a valid directory: %s'
                % directory)

    # Find candidate files
    found_files = prep.find_files(
        path=xml_dir, file_exts=('.xml', ), subdir=False)
    pywikibot.output("Found %d .xml files" % len(found_files))

    data = {}
    for xml_file in found_files:
        try:
            test = InfoEntry(load_xml(xml_file))
        except Exception as e:
            pywikibot.output(
                u"Encountered error while processing %s: %s" %
                (os.path.split(xml_file)[-1], e))
            continue
        if test.obj_id in data.keys():
            pywikibot.output(
                u"Multiple files for same object: %s, %s, %s" % (
                    test.obj_id, test.source_file,
                    data[test.obj_id]['source_file']))
            continue
        data[test.obj_id] = test.output()

    out_file = os.path.join(base_dir, u'processed_lido.json')
    common.open_and_write_file(out_file, data, as_json=True)
    pywikibot.output("Created %s with %d entries" % (out_file, len(data)))


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
                if value_entry.keys() != [tag]:  # expect no other subtag
                    pywikibot.output(
                        "Found unexpected tags: %s"
                        % ', '.join(value_entry.keys()))
                    exit()
                value_entry = value_entry[tag]

        # skip empty entries
        if not value_entry:
            continue

        if isinstance(value_entry, unicode):
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
    unknowns = (u'Okänd', )
    result = {}
    if actor[u'lido:actorID'][u'@lido:type'] == u'Nationalmuseum Sweden artist ID; NSID':
        result['nsid'] = actor[u'lido:actorID'][u'#text']
    else:
        result['other_id'] = u'%s: %s' % (
            actor[u'lido:actorID'][u'@lido:type'],
            actor[u'lido:actorID'][u'#text'])
    name = actor[u'lido:nameActorSet'][u'lido:appellationValue']
    if name in unknowns:
        name = None
    result['name'] = name
    return result


class InfoEntry(object):
    """A store for the data extracted from a single xml file."""

    def __init__(self, xml_data, debug=False):
        """Construct an info object from the loaded xml data."""
        # definie any internals
        self.source_file = xml_data['source_file']
        self.raw_data = xml_data
        self.debug = debug

        # for debugging
        self._debug(self.source_file)

        # populate data
        self.process_lido_xml(xml_data[u'lido:lidoWrap']['lido:lido'])

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
        skipped_tags = [u'lido:lidoRecID', ]

        # add inv_nr
        handled_tags.append(u'lido:objectPublishedID')
        for publihed_id in data[u'lido:objectPublishedID']:
            if publihed_id[u'@lido:type'] == u'local':
                self.inv_nr = publihed_id[u'#text']

        # handle administrative metadata
        handled_tags.append(u'lido:administrativeMetadata')
        self.add_admin_data(data[u'lido:administrativeMetadata'])

        # handle descriptive metadata
        handled_tags.append(u'lido:descriptiveMetadata')
        self.add_descriptive_data(data[u'lido:descriptiveMetadata'])

        flag_missed_tags(data, '', handled_tags, skipped_tags)

    def add_admin_data(self, data):
        handled_tags = list()
        skipped_tags = [u'lido:rightsWorkWrap', u'@xml:lang']
        tag = u'lido:administrativeMetadata'

        # set obj_id
        handled_tags.append(u'lido:recordWrap')
        recordID = data[u'lido:recordWrap'][u'lido:recordID']
        if recordID['@lido:type'] == 'local':
            self.obj_id = recordID['#text']

        # add image data
        handled_tags.append(u'lido:resourceWrap')
        self.add_image_data(data[u'lido:resourceWrap'][u'lido:resourceSet'])

        flag_missed_tags(data, tag, handled_tags, skipped_tags)

    def add_image_data(self, data):
        handled_tags = list()
        skipped_tags = ['', ]
        tag = u'lido:resourceWrap/lido:resourceSet'

        # identify filenames
        handled_tags.append(u'lido:resourceRepresentation')
        self.images = {}
        images = []
        # identify local images
        links = data[u'lido:resourceRepresentation']
        for link in links:
            if link[u'lido:linkResource'].startswith('http'):
                continue
            images.append(link[u'lido:linkResource'])

        # match image to attributions
        handled_tags.append(u'lido:rightsResource')
        attributions = common.listify(
            data[u'lido:rightsResource'].get(u'lido:rightsHolder'))
        if attributions:
            if len(attributions) != len(images):
                pywikibot.warning(
                    "image-attribution missmatch in %s" % self.source_file)
            for i, attribution in enumerate(attributions):
                self.images[images[i]] = attribution[u'lido:legalBodyName'][u'lido:appellationValue']
            #nån logik som ser till att det inte blir fel ibland
        else:
            # there aren't always photographers
            for i, image in enumerate(images):
                self.images[images[i]] = None

        # add license, just in case
        self.image_license = data[u'lido:rightsResource'][u'lido:rightsType'][u'lido:term']['#text']

        flag_missed_tags(data, tag, handled_tags, skipped_tags)

    def add_descriptive_data(self, data):
        handled_tags = list()
        skipped_tags = ['lido:objectClassificationWrap', u'@xml:lang']
        tag = u'lido:descriptiveMetadata'

        # add identification data
        handled_tags.append(u'lido:objectIdentificationWrap')
        self.add_identification_data(data[u'lido:objectIdentificationWrap'])

        # add event data
        handled_tags.append(u'lido:eventWrap')
        self.add_event_data(
            common.listify(data[u'lido:eventWrap']['lido:eventSet']))

        # add relation data
        handled_tags.append(u'lido:objectRelationWrap')
        self.add_relation_data(data[u'lido:objectRelationWrap'])

        flag_missed_tags(data, tag, handled_tags, skipped_tags)

    def add_identification_data(self, data):
        handled_tags = list()
        skipped_tags = ['', ]
        tag = u'lido:objectIdentificationWrap'

        # add title
        handled_tags.append(u'lido:titleWrap')
        titles = common.listify(data[u'lido:titleWrap'][u'lido:titleSet'])
        self.titles = get_lang_values_from_set(
            titles, (u'lido:appellationValue', ))

        # add incription
        handled_tags.append(u'lido:inscriptionsWrap')
        inscriptions = common.listify(
            data[u'lido:inscriptionsWrap'][u'lido:inscriptions'])
        self.inscriptions = get_lang_values_from_set(
            inscriptions, (u'lido:inscriptionTranscription', ))

        # add decription
        handled_tags.append(u'lido:objectDescriptionWrap')
        description_set = data[u'lido:objectDescriptionWrap'][u'lido:objectDescriptionSet']
        if not isinstance(description_set, OrderedDict):
            pywikibot.warning(
                "Weird things are happening in description field for %s:\n%s"
                % (self.source_file, description_set))
        descriptions = common.listify(
            description_set[u'lido:descriptiveNoteValue'])
        self.descriptions = get_lang_values_from_set(descriptions)

        # add measurements
        handled_tags.append(u'lido:objectMeasurementsWrap')
        measurement_set = data[u'lido:objectMeasurementsWrap'][u'lido:objectMeasurementsSet']
        if set(measurement_set.keys()) - set([u'lido:displayObjectMeasurements', u'lido:objectMeasurements']):
            pywikibot.warning(
                "Weird things are happening in measurement field for %s:\n%s"
                % (self.source_file, measurement_set))
        self._debug(measurement_set.get(u'lido:displayObjectMeasurements'))
        measurements = common.trim_list(common.listify(
            measurement_set.get(u'lido:displayObjectMeasurements')))
        self._debug(measurements)
        self.add_meaurements(measurements)

        # ensure location is always Nationalmuesum
        handled_tags.append(u'lido:repositoryWrap')
        repository_viaf = data[u'lido:repositoryWrap']['lido:repositorySet']['lido:repositoryName']['lido:legalBodyID']['#text']
        if repository_viaf != u'http://viaf.org/viaf/147742988':
            pywikibot.warning(
                "Unexpected repoitory in %s: %s"
                % (self.source_file, repository_viaf))

        flag_missed_tags(data, tag, handled_tags, skipped_tags)

    def add_meaurements(self, measurements):
        recognised_units = ('cm', 'mm')
        recognied_prefixes = {
            u'_': u'_',
            u'Mått': u'_',
            u'Ram': u'Framed',
        }
        skipped_prefixes = (
            u'Vikt', u'Trpram', u'Spännram', u'Montering', u'Yttermått',
            u'Rymd', u'Passepartout')
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
                        "Unrecognized prefix in measurement for %s:\n%s"
                        % (self.source_file, measurement))
                continue
            if parts[0] in self.measurements.keys():
                pywikibot.warning(
                    "Reused prefix in measurement for %s:\n%s"
                    % (self.source_file, measurement))
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
        creation_concept = 'http://terminology.lido-schema.org/lido00012'
        recognised_concepts = {
            'creation': creation_concept,
            'acquisition': 'http://terminology.lido-schema.org/lido00001'
        }

        found_creation = False
        for event in events:
            concept = event[u'lido:event'][u'lido:eventType']['lido:conceptID'][u'#text']
            if concept not in recognised_concepts.values():
                pywikibot.warning(
                    "Unrecognized event concept for %s: %s"
                    % (self.source_file, concept))
            elif concept == creation_concept:
                if found_creation:
                    pywikibot.warning(
                        "Multiple creation events for %s" % self.source_file)
                found_creation = True
                self.add_creation(event[u'lido:event'])

        if not found_creation:
            pywikibot.warning(
                "No creation event for %s" % self.source_file)

    def add_creation(self, event):
        handled_tags = list()
        skipped_tags = ['lido:eventName', u'lido:eventType']
        tag = u'lido:event'

        # add creator(s)
        handled_tags.append(u'lido:eventActor')
        self.creator = {}
        self.handle_creators(
            common.trim_list(common.listify(event[u'lido:eventActor'])))

        # add creation_date
        handled_tags.append(u'lido:eventDate')
        self.creation_date = {}
        if event.get(u'lido:eventDate'):
            self.creation_date['earliest'] = event[u'lido:eventDate'][u'lido:date'].get(u'lido:earliestDate')
            self.creation_date['latest'] = event[u'lido:eventDate'][u'lido:date'].get(u'lido:latestDate')
            self.creation_date['text'] = get_lang_values_from_set(
                common.listify(event[u'lido:eventDate'][u'lido:displayDate']))

        # add creation place
        handled_tags.append(u'lido:eventPlace')
        self.creation_place = get_lang_values_from_set(
            common.listify(
                event[u'lido:eventPlace'][u'lido:place'][u'lido:namePlaceSet']),
            (u'lido:appellationValue', ))

        # add materialtech
        handled_tags.append(u'lido:eventMaterialsTech')
        self.techniques = get_lang_values_from_set(
            common.listify(event[u'lido:eventMaterialsTech']),
            (u'lido:materialsTech', u'lido:termMaterialsTech', u'lido:term'))

        flag_missed_tags(event, tag, handled_tags, skipped_tags)

    def handle_creators(self, actors):
        creator_roles = (u'Konstnär', u'Utförd av', u'Komp. och utförd av')
        skipped_roles = (
            u'Tidigare attribution', u'Medarbetare',
            u'Alternativ tillskrivning', u'Beställare')
        qualified_roles = (u'Attribuerad till', u'Kopia efter', u'Fri kopia efter', u'Efter')
        all_roles = (creator_roles + skipped_roles + qualified_roles)
        qualifiers = {
            u'Tillskriven': 'P1773',
            u'Attribuerad till': 'P1773',
            u'Hennes ateljé': 'P1774',
            u'Hans ateljé': 'P1774',
            u'Hennes skola': 'P1780',
            u'Hans skola': 'P1780',
            u'Hennes art': 'P1777',
            u'Hans art': 'P1777',
            u'Kopia efter': 'P1877',
            u'Fri kopia efter': 'P1877',
            u'Efter': 'P1877',
            u'Osäker attribution': None,
            u'Alternativ attribution': None,
        }

        for actor in actors:
            if actor.keys() != [u'lido:actorInRole', ]:
                pywikibot.warning(
                    "Unexpected actor tag for %s:\n%s"
                    % (self.source_file, actor))
                continue

            # check role
            actor_role = actor[u'lido:actorInRole'][u'lido:roleActor'][u'lido:term'].get(u'#text')
            if not actor_role:
                continue  # empty entry
            elif actor_role not in all_roles:
                pywikibot.warning(
                    "Unexpected actor role for %s:\n%s"
                    % (self.source_file, actor[u'lido:actorInRole'][u'lido:roleActor']))
                continue
            elif actor_role in skipped_roles:
                continue

            # check qualifier
            qualifier = actor[u'lido:actorInRole'].get(u'lido:attributionQualifierActor')
            if qualifier and qualifier not in qualifiers:
                pywikibot.warning(
                    "Unhandled actor qualifier for %s:\n%s"
                    % (self.source_file, qualifier))
                continue

            actor_info = handle_actor(actor[u'lido:actorInRole'][u'lido:actor'])

            # handle any direct or inidrect qualifies
            if actor_role in qualified_roles:
                qualifier = actor_role
            if qualifier:
                actor_info['qualifier'] = qualifiers[qualifier]

            # crash if no nsid
            self.creator[actor_info['nsid']] = actor_info

    def add_relation_data(self, data):
        handled_tags = list()
        skipped_tags = ['', ]
        tag = u'lido:objectRelationWrap'

        # handle subjects
        handled_tags.append(u'lido:subjectWrap')
        self.subjects = list()
        subjects = data[u'lido:subjectWrap'][u'lido:subjectSet'][u'lido:subject']
        if subjects:
            subjects = common.listify(subjects[u'lido:subjectActor'])
            for subject in subjects:
                self.subjects.append(
                    handle_actor(subject[u'lido:actor']))

        flag_missed_tags(data, tag, handled_tags, skipped_tags)


def test():
    """Temporary entry point for tests."""
    xml_dir = os.path.join(MAIN_DIR, XML_DIR)
    filenames = [
        u'Item_7012482.xml', u'Item_7015842.xml', u'Item_7015788.xml', u'Item_7015002.xml', u'Item_7016287.xml', u'Item_7016251.xml', u'Item_7016257.xml', u'Item_7012945.xml'
    ]
    for filename in filenames:
        data = load_xml(os.path.join(xml_dir, filename))
        test = InfoEntry(data, debug=True)
        print test.source_file, test.obj_id

if __name__ == "__main__":
    process_all_files()
    #test()
