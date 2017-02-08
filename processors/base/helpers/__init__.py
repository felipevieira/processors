# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import re
import json
import uuid
import string
import logging
import datetime
import urlparse
import csv
import unidecode
import fuzzywuzzy.fuzz
import fuzzywuzzy.process
import iso3166
import dedupe

from . import pybossa_tasks_updater

logger = logging.getLogger(__name__)
PyBossaTasksUpdater = pybossa_tasks_updater.PyBossaTasksUpdater

# Module API


def get_variables(object, filter=None):
    """Exract variables from object to dict using name filter.
    """
    variables = {}
    for name, value in vars(object).items():
        if filter is not None:
            if not filter(name):
                continue
        variables[name] = value
    return variables


def slugify_string(string):
    """Slugify string
    """
    string = re.sub(r'[\W_]+', '_', string)
    string = string.strip('_')
    string = string.lower()
    return string


class JSONEncoder(json.JSONEncoder):
    """JSON encoder with datetime, date set support.
    """
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif isinstance(obj, datetime.date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)


def clean_list(raw_list):
    """Remove falsy values from list.
    """
    cleaned_list = []
    for value in raw_list:
        if value:
            cleaned_list.append(value)
    return cleaned_list


def clean_identifiers(identifiers):
    """Remove invalid identifiers.
    """
    PATTERNS = {
        'actrn': r'^ACTRN\d{14}p?$',
        'chictr': r'^ChiCTR',
        'drks': r'^DRKS',
        'euctr': r'^EUCTR\d{4}-\d{6}-\d{2}$',
        'gsk': r'^GSK',
        'irct': r'^IRCT',
        'isrctn': r'^ISRCTN\d{8}$',
        'jprn': r'^(JPRN-)?(C\d{9}|JapicCTI-\d{6}|JMA-IIA\d{5}|UMIN\d{9})$',
        'kct': r'^KCT',
        'nct': r'^NCT\d{8}$',
        'ntr': r'^NTR',
        'pactr': r'^PACTR',
        'per': r'^PER',
        'rbr': r'^RBR',
        'rpcec': r'^RPCEC',
        'takeda': r'^TAKEDA',
        'tctr': r'^TCTR',
        'who': r'^U\d{4}-\d{4}-\d{4}$',
    }
    result = {}
    for key, value in identifiers.items():
        try:
            new_value, num_changes = re.subn(
                r'^(\w+)\s+', r'\g<1>', value, re.IGNORECASE)
            if num_changes:
                logger.debug('Removed whitespaces from identifier "%s" to "%s"',
                             value, new_value)
                value = new_value
        except TypeError:
            pass
        if not validate_identifier(value):
            logger.warning('Ignoring invalid identifier %s:%s', key, value)
        elif key not in PATTERNS or not re.match(PATTERNS[key], value, re.IGNORECASE):
            message = 'Identifier "%s:%s" is not recognized'
            logger.warning(message, key, value)
        else:
            result[key] = value
    return result


def get_optimal_title(*titles):
    """Return first striped title with enough length or last striped title.
    """
    MIN_LENGTH = 10
    for title in titles:
        title = clean_string(title)
        if len(title) >= MIN_LENGTH:
            return title
    return title


def clean_string(value):
    """Cast falsy value to string and strip whitespeces and other unwanted chars.
    """
    if not value:
        value = ''
    value = value.strip(string.whitespace + '."')
    return value


def remove_string_punctuation(value):
    """Remove punctuation characters from unicode string
    """
    return re.sub(u"[^\w\d'\s]+", '', value).lower()


def find_list_of_identifiers(text):
    """Find list of valid trial identifier dicts in the given text.

    Example:
        [{'nct': 'NCT123345'}, {'euctr': 'EUCTR12345'}]

    It will only return identifiers that are valid according to
    validate_identifiers() function.
    """

    # Pattern could be improved based on a extended
    # clinical trial identifiers format analysis
    PATTERN = r'(%s\s*[\w\d-]{3,})'
    # In a form (source_id, pattern[])
    PREFIXES = [
        ('actrn', ['actrn']),
        ('euctr', ['euctr']),
        ('gsk', ['gsk']),
        ('isrctn', ['isrctn']),
        ('jprn', ['jprn', 'umin']),
        ('nct', ['nct']),
        ('takeda', ['takeda']),
    ]

    # Find identifiers
    list_of_identifiers = []
    for source_id, patterns in PREFIXES:
        for prefix in patterns:
            pattern = PATTERN % prefix
            matches = re.findall(pattern, text, re.IGNORECASE)

            for match in matches:
                clean_ids = clean_identifiers({source_id: match})
                if clean_ids:
                    list_of_identifiers.extend([clean_ids])

    return list_of_identifiers


def validate_identifier(identifier):
    """Empty or identifiers with only zeros are invalid."""
    if identifier:
        numbers = re.sub('[^\d]', '', identifier)
        if numbers:
            return int(numbers) != 0


def validate_remote_url(url):
    """"URLs without domain and scheme or with a file scheme are invalid"""
    is_valid_url = False
    try:
        parsed_url = urlparse.urlparse(url)
        if parsed_url.scheme and parsed_url.netloc:
            is_valid_url = (parsed_url.scheme != 'file')
    except AttributeError:
        pass

    return is_valid_url


def iter_rows(conn, dataset, table, orderby, bufsize=100, **filter):
    """Yield keyed rows from dataset table lazily and effective (using buffer).

    Args:
        conn (dict): connection dict
        dataset (str): dataset name (e.g. warehouse/database)
        table (str): table name
        order_by (str): how to order rows
        bufsize (int): how many rows to get per query
        filter (dict): additional field filter

    Yields:
        dict: the next row from table

    """
    offset = 0
    count = conn[dataset][table].count(**filter)
    # FIXME: This doesn't avoid changing the received filter param
    query = filter
    query['order_by'] = orderby
    while offset < count:
        query.update({
            '_offset': offset,
            '_limit': bufsize,
        })
        offset += bufsize
        for row in conn[dataset][table].find(**query):
            # Fixing hex representation
            for field in ['id', 'meta_id']:
                if field in row:
                    try:
                        row[field] = uuid.UUID(row[field]).hex
                    except ValueError:
                        # Ignore errors if ID fields aren't UUIDs
                        pass
            yield row


def find_trial_by_identifiers(conn, identifiers, ignore_record_id=None):
    """Find first trial matched by one of passed identifiers.

    Args:
        conn (dict): connection dict
        identifiers (dict): identifiers dict (nct: <id>, euct: <id>, ...)
        ignore_record_id (str): skip record with this id (for better dedup)

    Returns:
        dict: trial

    """
    trial = None
    # See https://github.com/opentrials/processors/pull/46/files/f5e8403072bf6ed93b82d0c45bd3877e42e435c4#r76836368
    QUERY = "SELECT * FROM records WHERE identifiers @> '%s'"
    for source, identifier in identifiers.items():
        query = QUERY % json.dumps({source: identifier})
        records = list(conn['database'].query(query))
        for record in records:
            if (ignore_record_id and record['id'].hex == uuid.UUID(ignore_record_id).hex):
                continue
            trial = conn['database']['trials'].find_one(
                id=record['trial_id'].hex)
            if trial:
                break
        if trial:
            break
    return trial


def safe_prepend(prepend_string, string):
    """Prepend to string non-destructively
    Ex: safe_prepend('EUCTR', 'EUCTR12345678') => 'EUCTR12345678'

    Args:
        prepend_string: string to prepend
        string: string to prepend to
    """
    if string is None:
        return None
    if not string.startswith(prepend_string):
        string = '%s%s' % (prepend_string, string)

    return string


def get_canonical_location_name(location):
    """Find the canonical location name according to the
    passed entry

    Args:
        location (str): the location to be normalized
    """

    if location is None:
        return None

    # Extracted from: https://github.com/datasets/country-codes/blob/master/data/country-codes.csv
    CSV_PATH = os.path.join(os.path.dirname(__file__), 'data/countries.csv')
    DISTANCE_SCORER = fuzzywuzzy.fuzz.token_sort_ratio
    EDIT_DISTANCE_THRESHOLD = 75

    cleaned_location = remove_string_punctuation(location)
    current_match = location

    try:
        current_match = iso3166.countries.get(cleaned_location).name
    except KeyError:
        with open(CSV_PATH, 'r') as csv_file:
            reader = csv.DictReader(csv_file)
            current_score = float('-inf')
            for country in reader:
                relevant_info = [unicode(country[field], encoding='utf-8')
                                 for field in reader.fieldnames[0:5]]

                location_info = [remove_string_punctuation(location_info)
                                 for location_info in relevant_info]
                _, score = fuzzywuzzy.process.extractOne(
                    cleaned_location, location_info, scorer=DISTANCE_SCORER)

                if score > current_score:
                    current_match = iso3166.countries.get(country['ISO3166-1-Alpha-3']).name
                    current_score = score

            if current_score < EDIT_DISTANCE_THRESHOLD:
                logger.debug('Location "%s" not normalized', location)
                return location

    logger.debug('Location "%s" normalized as "%s"', cleaned_location, current_match)

    return current_match


def get_canonical_organisation_name(conn, organisation):
    """Find a canonical organisation name according to
    a pre-built set of clusters

    Args:
        conn (dict): connection dict
        organisation (str): the organisation to be normalized
    """
    CLUSTER_QUERY = "SELECT canonical " + \
                    "FROM organisation_clusters " + \
                    "WHERE '%s'=ANY(variations)"

    normalized_form = organisation

    # Try to find the organisation in some cluster
    try:
        normalized_form = conn['warehouse'].query(query).next()['canonical']
        logger.debug('Organisation "%s" normalized as "%s"', organisation, normalized_form)
    except StopIteration:
        logger.debug('Organisation "%s" not normalized', organisation)
        pass

    return normalized_form


def _dedup_cluster(cluster_entries):
    """Sample, train and build organisation clusters

    Args:
        cluster_entries (list): a list of candidates to
        be grouped in equivalent sets
    """
    SAMPLE_SIZE = 10000
    MATCH_THRESHOLD = 0.75
    TRAINING_FILE = os.path.join(os.path.dirname(__file__),
                                 'data/organisation_training_data.json')

    fields = [{'field': 'name', 'type': 'String'}]
    deduper = dedupe.Dedupe(fields)
    deduper.sample(cluster_entries, SAMPLE_SIZE)

    with open(TRAINING_FILE) as training_file:
        deduper.readTraining(training_file)

    deduper.train()

    return deduper.match(cluster_entries, MATCH_THRESHOLD)


def update_organisation_clusters(conn):
    """Build a readable list of organisation clusters to be used
    when normalizing new entries

    Args:
        conn (dict): connection dict
    """
    logger.debug('Recomputing organisations cluster data for further access')

    conn['warehouse'].begin()
    conn['warehouse']['organisation_clusters'].delete()

    stored_organisations = list(conn['database']['organisations'].all())

    cluster_members = {entry['id']: {'name': unidecode.unidecode(entry['name'])}
                       for entry in stored_organisations}

    clustered_dupes = _dedup_cluster(cluster_members)

    for (_, cluster) in enumerate(clustered_dupes):
        id_set, _ = cluster
        cluster_membership = [str(cluster_members[c]['name']) for c in id_set]

        cluster = {
            'canonical': max(cluster_membership, key=len).replace("'", "''"),
            'variations': cluster_membership
        }

        conn['warehouse']['organisation_clusters'].insert(cluster)

    conn['warehouse'].commit()
