import unittest
from typing import Set, Dict

from basyx.aas import model
from aas_repository_server import routes, storage


class RepositoryObjectStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        """
        Set up the following test case:

          - Submodel01
                - https://example.com/sm/test_submodel01
                - semanticID: https://example.com/semanticIDs/ONE
                - Property with semanticID: https://example.com/semanticIDs/ONE
          - Submodel02
                - https://example.com/sm/test_submodel02
                - semanticID: https://example.com/semanticIDs/TWO
          - Submodel03
                - https://example.com/sm/test_submodel03
                - semanticID: https://example.com/semanticIDs/ONE
        """
        self.object_store = routes.OBJECT_STORE
        identifier: model.Identifier = model.Identifier(
            id_="https://example.com/sm/test_submodel01",
            id_type=model.IdentifierType.IRI
        )
        self.semantic_id_1: model.Reference = model.Reference(
            key=tuple([
                model.Key(
                    type_=model.KeyElements.GLOBAL_REFERENCE,
                    local=False,
                    value="https://example.com/semanticIDs/ONE",
                    id_type=model.KeyType.IRI
                )
            ])
        )
        self.identifiable1: model.Submodel = model.Submodel(
            identification=identifier,
            id_short="exampleSM",
            semantic_id=self.semantic_id_1,
            submodel_element=[
                model.Property(
                    id_short="TestProperty",
                    value_type=model.datatypes.String,
                    value="TestValue",
                    semantic_id=self.semantic_id_1
                )
            ]
            )
        self.object_store.add(self.identifiable1)
        identifier: model.Identifier = model.Identifier(
            id_="https://example.com/sm/test_submodel02",
            id_type=model.IdentifierType.IRI
        )
        self.semantic_id_2: model.Reference = model.Reference(
            key=tuple([
                model.Key(
                    type_=model.KeyElements.GLOBAL_REFERENCE,
                    local=False,
                    value="https://example.com/semanticIDs/TWO",
                    id_type=model.KeyType.IRI
                )
            ])
        )
        self.identifiable2: model.Submodel = model.Submodel(
            identification=identifier,
            id_short="exampleSM",
            semantic_id=self.semantic_id_2
        )
        self.object_store.add(self.identifiable2)
        identifier: model.Identifier = model.Identifier(
            id_="https://example.com/sm/test_submodel03",
            id_type=model.IdentifierType.IRI
        )
        self.identifiable3: model.Submodel = model.Submodel(
            identification=identifier,
            id_short="exampleSM",
            semantic_id=self.semantic_id_1
        )
        self.object_store.add(self.identifiable3)

    def tearDown(self) -> None:
        self.object_store.clear()
        self.object_store.semantic_id_index = {}

    def test_index_semantic_ids(self):
        self.object_store._index_semantic_ids()
        query_1 = self.object_store.get_semantic_id(self.semantic_id_1.key[0])
        # Expected return: Submodel01 and Submodel03
        self.assertEqual(3, len(query_1))
        query_2 = self.object_store.get_semantic_id(self.semantic_id_2.key[0])
        # Expected return: Submodel02
        self.assertEqual(1, len(query_2))
