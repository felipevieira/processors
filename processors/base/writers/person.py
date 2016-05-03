# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import uuid
import logging
import datetime
from .. import readers
from .. import helpers
logger = logging.getLogger(__name__)


# Module API

def write_person(conn, person, source_id, trial_id=None):
    """Write person to database.

    Args:
        conn (object): connection object
        person (dict): normalized data
        source_id (str): data source id
        trial_id (str): related trial id

    Returns:
        str: person identifier

    """
    action = 'updated'
    timestamp = datetime.datetime.utcnow()

    # Get slug/facts
    slug = helpers.slugify_string(person['name'])
    facts = helpers.slugify_array([trial_id] + person['phones'])

    # Read
    object = readers.read_objects(conn, 'persons', single=True,
        slug=slug,
        facts=facts)

    # Create
    if not object:
        object = {}
        object['id'] = uuid.uuid4().hex
        object['created_at'] = timestamp
        object['slug'] = slug
        object['facts'] = []
        action = 'created'

    # Update
    object.update({
        'updated_at': timestamp,
        'source_id': source_id,
        'facts': helpers.slugify_array(object['facts'] + facts),
        # ---
        'name': person['name'],
        'type': person['type'],
        'data': person['data'],
    })

    # Write object
    conn['database']['persons'].upsert(object, ['id'], ensure=False)

    # Write relationship
    if trial_id:
        relathionship = {
            'trial_id': trial_id,
            'person_id': object['id'],
            # ---
            'role': person['role'],
            'context': person['context'],
        }
        conn['database']['trials_persons'].upsert(
            relathionship, ['trial_id', 'person_id'], ensure=False)

    # Log
    logger.debug('Person - %s: %s' % (action, person['name']))

    return object['id']