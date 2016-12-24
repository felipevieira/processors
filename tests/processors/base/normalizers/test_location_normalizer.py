# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from processors.base.normalizers import get_normalized_form

# Tests

def test_location_normalizer():
    assert get_normalized_form(str("Brasil")) == "Brazil"
    assert get_normalized_form(str('Virgin Islands (U.S.)')) == 'Virgin Islands, U.S.'
    assert get_normalized_form(str('Chinese')) == 'China'
    assert get_normalized_form(str('thauland')) == 'Thailand'
    assert get_normalized_form(str('Lebano')) == 'Lebanon'
