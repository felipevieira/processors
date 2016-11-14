# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pytest
import uuid


@pytest.fixture(scope='function')
def file_fixture(conn):
    future_file_id = uuid.uuid1().hex
    file_record = {
        'sha1': uuid.uuid1().hex,
        'source_url': ('http://example.org/file_%s.pdf' % future_file_id),
        'id': future_file_id,
    }
    file_id = conn['database']['files'].insert(file_record)
    return file_id
