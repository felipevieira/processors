# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import processors.base.helpers


# Module API

def process(conf, conn):
    """Update clusters used when normalizing trials entities
    """
    processors.base.helpers.update_organisation_clusters(conn)
