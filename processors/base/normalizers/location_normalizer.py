# -*- coding: utf-8 -*-
import os
import csv
import logging
import jellyfish
import numpy
import pycountry
import scipy.cluster.hierarchy

MAX_CLUSTER_DISTANCE = 0.9
MIN_CLUSTER_DISTANCE = 0.01

DISTANCE_THRESHOLD = 0.15

logger = logging.getLogger(__name__)


def build_country_clusters():
    """Generate country cluster according to the training data

    Yields:
        cluster: country cluster used for normalization suggestion
    """

    # also respecting cannot-link and must-link rules
    def _cluster_distance(coord):
        """An inner function that computs the Jaro distance between two countries

        Args:
            coord(tuple): two clusters
        Yields:
            cluster: the distance between the two cluster
        """
        def cannot_link(coord):
            """A simple cannot-link relantionship that prevents canonical clusters
                form being merged even if they share a small string edition distance
            Args:
                coord(tuple): two clusters elements
            Yields:
                ans: True if elements clusters cannot be merged, False otherwise
            """
            i, j = coord
            ans = False
            if (countries[i] in canonical_names and countries[j] in canonical_names):
                ans = True
            return ans

        # A simple must-link relationship that forces merges between canonical
        # forms and abbreviations
        def must_link(coord):
            """A simple must-link relationship that forces merges between canonical
                forms and their abbreviations
            Args:
                coord(tuple): two clusters elements
            Yields:
                cluster: True if elements clusters must be merged, False otherwise
            """
            i, j = coord
            ans = False
            if countries[i] in acronyms:
                if len(countries[i]) == 2:
                    ans = pycountry.countries.get\
                              (alpha_2=countries[i]).name == countries[j]
                else:
                    ans = pycountry.countries.get\
                              (alpha_3=countries[i]).name == countries[j]
            elif countries[j] in acronyms:
                if len(countries[j]) == 2:
                    ans = pycountry.countries.get\
                              (alpha_2=countries[j]).name == countries[i]
                else:
                    ans = pycountry.countries.get\
                              (alpha_3=countries[j]).name == countries[i]
            return ans

        # Setting the clustering distances according to must-link
        # and cannot-link relationships
        if not (cannot_link(coord) or must_link(coord)):
            i, j = coord
            cluster_distance = 1 - jellyfish.jaro_distance\
                (countries[i].lower(), countries[j].lower())
        elif cannot_link(coord):
            cluster_distance = MAX_CLUSTER_DISTANCE
        elif must_link(coord):
            cluster_distance = MIN_CLUSTER_DISTANCE
        return cluster_distance

    # Read an normalize country names
    with open(os.path.join(os.path.dirname(__file__),
                           'training_sets/location_training_test.csv'), 'r') \
            as csv_file:
        reader = csv.DictReader(csv_file)
        countries = [unicode(country['country'].strip(),
                             encoding="utf-8") for country in reader]

    canonical_names = [c.name for c in pycountry.countries]
    acronyms = [c.alpha_2 for c in pycountry.countries] + [c.alpha_3 for c in pycountry.countries]

    # Compute the triangle matrix used by the hierarchical clustering
    indexes_triangle_matrix = numpy.triu_indices(len(countries), 1)
    distances_triangle_matrix = numpy.apply_along_axis\
        (_cluster_distance, 0, indexes_triangle_matrix)

    # Compute the country linkage and extract the clusters
    country_linkage_matrix = scipy.cluster.hierarchy.\
        linkage(distances_triangle_matrix, method='complete')
    flat_clusters = scipy.cluster.hierarchy.fcluster\
        (country_linkage_matrix, DISTANCE_THRESHOLD, criterion='distance')

    clusters = {}
    for i in range(len(flat_clusters)):
        clusters[flat_clusters[i]] = clusters.get(flat_clusters[i], []) + [countries[i]]

    return clusters

COUNTRY_CLUSTER = build_country_clusters()


def get_normalized_form(country, cluster=COUNTRY_CLUSTER):
    """Suggests a normalized version for a country variation
    according to the country clusters

     Args:
        country (str): country variation
        cluster (dict): the country clusters dict

    Yields:
        suggested_normalization (str): a suggested canonical name to country
    """

    # Search for the country on the pre-built clusters
    for cluster_id, cluster_items in cluster.iteritems():
        if country.strip() in cluster_items:
            try:
                # Country found in complete cluster. Return its canonical
                # equivalent and log the successful normalization
                suggested_normalization = list(set(cluster_items) & set([c.name for c in pycountry.countries]))[0]
                logger.debug(
                    'Location "%s" successfully normalized to "%s"',
                    country, suggested_normalization)
                return suggested_normalization
            except IndexError:
                logger.debug(
                    'Unsuccessfully location normalization of "%s"',
                    country)
                # Country found in a single cluster
                # Return itself and log the unsuccessful normalization
                return country.strip()

    # Country not found. Add new location to training base before
    # retrain the model
    with open(os.path.join(os.path.dirname(__file__),
                           'training_sets/location_training_test.csv'), 'a')\
            as csv_file:
        csv_file.write("%s\n" % country)
    return get_normalized_form(country, cluster=build_country_clusters())