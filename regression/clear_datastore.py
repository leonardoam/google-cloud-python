# Copyright 2014 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Script to populate datastore with regression test data."""


from gcloud import datastore
from gcloud.datastore import _implicit_environ
from gcloud.datastore.query import Query
from gcloud.datastore.transaction import Transaction
from six.moves import input


datastore._DATASET_ENV_VAR_NAME = 'GCLOUD_TESTS_DATASET_ID'
datastore.set_default_dataset_id()
datastore.set_default_connection()


FETCH_MAX = 20
ALL_KINDS = [
    'Character',
    'Company',
    'Kind',
    'Person',
    'Post',
]
TRANSACTION_MAX_GROUPS = 5


def fetch_keys(kind, fetch_max=FETCH_MAX, query=None, cursor=None):
    if query is None:
        query = Query(kind=kind, projection=['__key__'])

    iterator = query.fetch(limit=fetch_max, start_cursor=cursor)

    entities, _, cursor = iterator.next_page()
    return query, entities, cursor


def get_ancestors(entities):
    # NOTE: A key will always have at least one path element.
    key_roots = [entity.key.flat_path[:2] for entity in entities]
    # Return the unique roots.
    return list(set(key_roots))


def delete_entities(entities):
    if not entities:
        return

    dataset_ids = set(entity.key.dataset_id for entity in entities)
    if len(dataset_ids) != 1:
        raise ValueError('Expected a unique dataset ID.')

    dataset_id = dataset_ids.pop()
    key_pbs = [entity.key.to_protobuf() for entity in entities]
    _implicit_environ.CONNECTION.delete_entities(dataset_id, key_pbs)


def remove_kind(kind):
    results = []

    query, curr_results, cursor = fetch_keys(kind)
    results.extend(curr_results)
    while curr_results:
        query, curr_results, cursor = fetch_keys(kind, query=query,
                                                 cursor=cursor)
        results.extend(curr_results)

    if not results:
        return

    delete_outside_transaction = False
    with Transaction():
        # Now that we have all results, we seek to delete.
        print('Deleting keys:')
        print(results)

        ancestors = get_ancestors(results)
        if len(ancestors) > TRANSACTION_MAX_GROUPS:
            delete_outside_transaction = True
        else:
            delete_entities(results)

    if delete_outside_transaction:
        delete_entities(results)


def remove_all_entities():
    print('This command will remove all entities for the following kinds:')
    print('\n'.join(['- ' + val for val in ALL_KINDS]))
    response = input('Is this OK [y/n]? ')
    if response.lower() != 'y':
        print('Doing nothing.')
        return

    for kind in ALL_KINDS:
        remove_kind(kind)


if __name__ == '__main__':
    remove_all_entities()
