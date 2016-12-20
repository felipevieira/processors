# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster

import uuid
import logging
import datetime
import jellyfish
import numpy
import distance
# from .. import helpers
logger = logging.getLogger(__name__)


# Module API

def write_location(conn, location, source_id, trial_id=None):
    """Write location to database.

    Args:
        conn (dict): connection dict
        location (dict): normalized data
        source_id (str): data source id
        trial_id (str): related trial id

    Raises:
        KeyError: if data structure is not valid

    Returns:
        str/None: object identifier/if not written (skipped)

    """
    create = False
    timestamp = datetime.datetime.utcnow()

    # Get name
    name = helpers.clean_string(location['name'])
    if len(name) <= 1:
        return None

    # Get slug/find object
    slug = helpers.slugify_string(name)
    object = conn['database']['locations'].find_one(slug=slug)

    # Create object
    if not object:
        object = {}
        object['id'] = uuid.uuid1().hex
        object['created_at'] = timestamp
        object['slug'] = slug
        create = True

    # Write object only for high priority source
    if create or source_id:  # for now do it for any source

        # Update object
        object.update({
            'updated_at': timestamp,
            'source_id': source_id,
            # ---
            'name': name,
            'type': location.get('type', None),
        })

        # Write object
        conn['database']['locations'].upsert(object, ['id'], ensure=False)

        # Log debug
        logger.debug('Location - %s: %s',
            'created' if create else 'updated', name)

    return object['id']

def build_country_clusters():
    # An inner function that computs the Jaro distance between two countries
    def _d(coord):
        i, j = coord
        return 1 - jellyfish.jaro_distance(countries[i], countries[j])

    # Read an normalize country names
    training_data = open('/home/felipevieira/Área de Trabalho/data for training.txt', 'r')
    countries = [unicode(country.strip(), encoding="utf-8") for country in training_data.readlines()]
    
    # Compute the triangle matrix used by the hierarchical clustering
    indexes_triangle_matrix = numpy.triu_indices(len(countries), 1)
    distances_triangle_matrix = numpy.apply_along_axis(_d, 0, indexes_triangle_matrix)

    # Compute the country likage and extract the clusters (249 is the number of acknowledged countries according to 3166-1)
    country_linkage_matrix = linkage(distances_triangle_matrix, method="single")
    flat_custers = fcluster(country_linkage_matrix, 0.15, criterion='distance')

    clusters = {}
    for i in range(len(flat_custers)):
        clusters[flat_custers[i]] = clusters.get(flat_custers[i], []) + [countries[i]] 

    for cluster, cluster_items in clusters.iteritems():
        print(cluster_items)

    return clusters

def predict_canonical_country_name(country):
    # Search for the country on the pre-built clusters
    for cluster_id, cluster_items in build_country_clusters().iteritems():
        if country in cluster_items:
            # Contry found. Return it and log the successful normalization
            return
    # Contry not found. Add new location to database before retrain the model
    predict_canonical_country_name(country)

# if __name__ == '__main__':
#     predict_canonical_country_name("Cina")