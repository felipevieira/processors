# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pytest
import processors.base.helpers as helpers

class TestValidateIdentifier(object):
    @pytest.mark.parametrize('identifier', [
        'NCT00020500',
        'U2016-0100-0042',
        'ISRCTN02018090',
        'EUCTR2013-030180-02',
        'EUCTR2010-070109-20/IT',
        'TAKEDA-AD-4833_409 (PHARMO)',
    ])
    def test_valid_identifiers(self, identifier):
        assert helpers.validate_identifier(identifier)

    @pytest.mark.parametrize('identifier', [
        'NCT00000000',
        'U0000-0000-0000',
        'ISRCTN00000000',
        'EUCTR0000-000000-00',
        'EUCTR0000-000000-00/IT',
    ])
    def test_identifiers_with_only_zeros_are_invalid(self, identifier):
        assert not helpers.validate_identifier(identifier)

    def test_empty_identifiers_are_invalid(self):
        assert not helpers.validate_identifier('')


class TestFindListOfIdentifiers(object):
    @pytest.mark.parametrize('text,identifiers', [
        ('NCT00000000', []),
        ('NCT00020500', [{'nct': 'NCT00020500'}]),
        ('NCT00020500 ISRCTN00000000', [{'nct': 'NCT00020500'}]),
        ('NCT00020500 ISRCTN02018090', [{'nct': 'NCT00020500'}, {'isrctn': 'ISRCTN02018090'}]),
        ('Lorem ipsum NCT00020500 dolor sit amet', [{'nct': 'NCT00020500'}]),
    ])
    def test_returns_only_valid_identifiers(self, text, identifiers):
        assert sorted(helpers.find_list_of_identifiers(text)) == sorted(identifiers)

    @pytest.mark.parametrize('text,identifiers', [
        ('NCT 12345678', [{'nct': 'NCT12345678'}]),
        ('ISRCTN    12345678', [{'isrctn': 'ISRCTN12345678'}]),
        ('TAKEDA01-02-TL-375-033', [{'takeda': 'TAKEDA01-02-TL-375-033'}]),
    ])
    def test_allows_whitespace_in_identifiers(self, text, identifiers):
        assert sorted(helpers.find_list_of_identifiers(text)) == sorted(identifiers)


class TestGetCleanedIdentifiers(object):
    @pytest.mark.parametrize('identifiers', [
        {'actrn': 'ACTRN12615001075572p'},
        {'chictr': 'ChiCTR123'},
        {'drks': 'DRKS123'},
        {'euctr': 'EUCTR1234-123456-12'},
        {'gsk': 'GSK123'},
        {'irct': 'IRCT123'},
        {'isrctn': 'ISRCTN71203361'},
        {'jprn': 'JPRN-UMIN123456789'},
        {'jprn': 'UMIN123456789'},
        {'kct': 'KCT123'},
        {'nct': 'NCT12345678'},
        {'ntr': 'NTR123'},
        {'pactr': 'PACTR123'},
        {'per': 'PER123'},
        {'rbr': 'RBR123'},
        {'rpcec': 'RPCEC123'},
        {'takeda': 'TAKEDA123'},
        {'tctr': 'TCTR123'},
        {'who': 'U1111-1115-2414'},
    ])
    def test_good_identifiers(self, identifiers):
        assert helpers.clean_identifiers(identifiers) == identifiers

    @pytest.mark.parametrize('identifiers', [
        {'bad_source': 'U123'},
        {'nct': 'ACTRN123'},
        {'actrn': '123ACTRN'},
        {'takeda': False},
        {'jprn': None},
        {'isrctn': 'ISRCTN12345678, ISRCTN12345678'},
        {'nct': ''},
        {'nct': 'NCT00000000'},
        {'isrctn': 'ISRCTN00000000'},
    ])
    def test_bad_identifiers(self, identifiers):
        assert helpers.clean_identifiers(identifiers) == {}

    def test_ignores_case(self):
        identifiers = {'nct': 'nCt12345678'}
        assert helpers.clean_identifiers(identifiers) == identifiers


class TestValidateRemoteURL(object):
    @pytest.mark.parametrize('url', [
        'https://onlinelibrary.wiley.com/doi/10.1002/14651858.CD009005/full',
        'http://www.ncbi.nlm.nih.gov/pubmed/18502614',
        'ftp://ftp.funet.fi/pub/standards/RFC/rfc959.txt',
    ])
    def test_valid_url(self, url):
        assert helpers.validate_remote_url(url)

    @pytest.mark.parametrize('url', [
        'ncbi.nlm.nih.gov/pubmed/18502614',
        'somewhere',
        'somewhere.com',
        None,
        True,
    ])
    def test_invalid_url(self, url):
        assert not helpers.validate_remote_url(url)

class TestSafePrepend(object):
    @pytest.mark.parametrize('prepend_string, string, expected', [
        ('EUCTR', '123456', 'EUCTR123456'),
        ('EUCTR', 'EUCTR123456', 'EUCTR123456'),
        ('EUCTR', None, None),
    ])
    def test_safe_prepend(self, prepend_string, string, expected):
        assert helpers.safe_prepend(prepend_string, string) == expected

class TestLocationNormalizer(object):
    @pytest.mark.parametrize("test_input,expected", [
        # Locations normalized by ISO-3166 name standards
        ("Brazil", "Brazil"),
        ("United States of America", "United States"),

        # Locations normalized by ISO-3166 acronym standards
        ("US", "United States"),
        ("UK", "United Kingdom of Great Britain and Northern Ireland"),

        # Locations normalized by Levenshtein distance (name)
        ("Chnia", "China"),
        ("The Netherlands", "Netherlands"),
        ("thauland", "Thailand"),

        # Locations not normalized (corner cases)
        ("Asia(except Japan)", "Asia(except Japan)"),
        ("Outside", "Outside"),
        (None, None)])


    def test_location_normalizer(self, test_input, expected):
        assert helpers.get_canonical_location_name(test_input) == expected

class TestOrganisationNormalizer(object):
    def _create_organisation_cluster(self, conn, canonical_name, variations):
        cluster = {
            'canonical': canonical_name,
            'variations': [canonical_name] + [variations]
        }
        conn['warehouse']['organisation_clusters'].insert(cluster)

    @pytest.mark.parametrize("test_input,expected", [
        # Organisation normalized with a longer equivalent
        ("VERTEX PHARMS INC", "VERTEX PHARMS"),
        ("Alliance Pharmaceuticals", "Alliance Pharmaceuticals Ltd"),

        # Organisation normalized as it is (the longest available form)
        ("Justus Liebig University of Giessen",
         "Justus Liebig University of Giessen"),

         # New organisation non-normalized
        ("Federal University of Campina Grande",
         "Federal University of Campina Grande"),
    ])

    def test_organisation_normalizer(self, conn, test_input, expected):
        self._create_organisation_cluster(conn, expected, test_input)
        assert helpers.get_canonical_organisation_name(conn, test_input) == expected