# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pytest
import dataset
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
import processors.base.config as config

# Make fixtures available to all tests

from tests.fixtures.files import file_fixture
from tests.fixtures.trials import trial
from tests.fixtures.sources import nct_source, fda_source
from tests.fixtures.fda_approvals import fda_approval
from tests.fixtures.fda_applications import fda_application
from tests.fixtures.organizations import organization


def teardown_database(engine):
    metadata = MetaData(bind=engine)
    metadata.reflect()
    metadata.drop_all()


def create_test_database(source_database_url, test_database_url):
    engine = create_engine(source_database_url)
    test_engine = create_engine(test_database_url)
    metadata = MetaData()
    metadata.reflect(engine)
    metadata.create_all(test_engine)
    return test_engine


@pytest.fixture(scope='session')
def setup_test_databases(request):
    """Create test databases from the schema of source databases.
        The databases are created when the first test uses them and are dropped
         at the end of each test session.

    Returns:
        a tuple of SQLAlchemy engines for the test databases
    """

    test_warehouse = create_test_database(config.WAREHOUSE_URL, config.TEST_WAREHOUSE_URL)
    test_api = create_test_database(config.DATABASE_URL, config.TEST_DATABASE_URL)
    def teardown():
        teardown_database(test_warehouse)
        teardown_database(test_api)

    request.addfinalizer(teardown)
    return (test_warehouse, test_api)


@pytest.fixture(scope='function')
def conn(request, setup_test_databases):
    """Create connection dict for the test databases.
        New sessions are created for each test and are closed at the end of the test.

    Returns:
        a connection dict where each key is a database name and each value
         a `dataset.Database()` instance
    """

    test_warehouse, test_api = setup_test_databases
    conn = {}
    conn['database'] = dataset.connect(config.TEST_DATABASE_URL)
    conn['warehouse'] = dataset.connect(config.TEST_WAREHOUSE_URL)

    APISession = sessionmaker(bind=conn['database'].engine)
    api_session = APISession()
    WarehouseSession = sessionmaker(bind=conn['warehouse'].engine)
    warehouse_session = WarehouseSession()
    def teardown():
        api_session.close()
        warehouse_session.close()

    request.addfinalizer(teardown)
    return conn
