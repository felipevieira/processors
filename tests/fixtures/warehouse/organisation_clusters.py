# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pytest

@pytest.fixture
def organisation_cluster(conn):
    cluster_ghent = {
        'canonical': 'Ghent University Hospital',
        'variations': ['Ghent University Hospital', 'Ghent University']
    }

    cluster_justus = {
        'canonical': 'Justus Liebig University of Giessen',
        'variations': ['Justus Liebig University of Giessen', 'Justus Liebig']
    }

    conn['warehouse']['organisation_clusters'].insert(cluster_ghent)
    conn['warehouse']['organisation_clusters'].insert(cluster_justus)