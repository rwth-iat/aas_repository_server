from typing import Dict, Set, Optional
import dataclasses

from basyx.aas import model
from basyx.aas.backend import local_file
from basyx.aas.util import traversal


@dataclasses.dataclass
class SemanticIndexElement:
    """
    A Semantic Index Element

    :attr: semantically_identified_referable: The Referable that the semanticID is
        attached to
    :attr: parent_identifiable: The Identifiable that is the parent of the Referable.
        Typically a Submodel. If the semantic ID is attached to the Submodel itsself,
        `semantically_identified_referable` and `parent_identifiable` will both point
        to the Submodel
    :attr: parent_asset_administration_shell: The Asset Administration Shell that
        contains the Identifiable that contains the Referable the semanticID is
        attached to, if it exists
    """
    semantically_identified_referable: model.Referable
    parent_identifiable: model.Identifier
    parent_asset_administration_shell: Optional[model.Identifier] = None

    def __hash__(self):
        return hash((self.semantically_identified_referable, self.parent_identifiable))


class RepositoryObjectStore(local_file.LocalFileObjectStore):
    """
    This ObjectStore has the added functionality that it indexes all semanticIDs in the existing Identifiable objects.
    That way, it allows for searching the objects for occurrences of a semanticID.

    Note, that this is just a temporary solution, as it does not scale endlessly. But it slightly fancier than
    iterating over the whole ObjectStore every time we want a semanticId
    """
    def __init__(self, storage_directory: str):
        super().__init__(storage_directory)
        self.semantic_id_index: Dict[model.Key, Set[SemanticIndexElement]] = {}
        self._index_semantic_ids()

    def get_semantic_id(self,
                        semantic_id: model.Key,
                        check_for_key_type: bool = False,
                        check_for_key_local: bool = False,
                        check_for_key_id_type: bool = False) -> Set[SemanticIndexElement]:
        # Get suiting semantic_ids for the configured search
        possible_semantic_ids: Set[model.Key] = set()
        for possible_semantic_id in self.semantic_id_index.keys():
            if possible_semantic_id.value != semantic_id.value:
                continue
            if check_for_key_type and possible_semantic_id.key_type != semantic_id.key_type:
                continue
            if check_for_key_local and possible_semantic_id.local != semantic_id.local:
                continue
            if check_for_key_id_type and possible_semantic_id.id_type != semantic_id.id_type:
                continue
            possible_semantic_ids.add(possible_semantic_id)
        # Return the results
        results: Set[SemanticIndexElement] = set()
        for result_semantic_id in possible_semantic_ids:
            if self.semantic_id_index.get(result_semantic_id) is not None:
                results.update(self.semantic_id_index[result_semantic_id])
        return results

    def _add_semantic_id_to_index(
            self,
            semantic_id: model.Key,
            referable: model.Referable,
            parent_identifiable: model.Identifier,
            parent_aas: Optional[model.Identifier] = None
    ):
        """
        Adds a semanticID's Key to the index
        """
        if self.semantic_id_index.get(semantic_id) is None:
            self.semantic_id_index[semantic_id] = {
                SemanticIndexElement(
                    referable,
                    parent_identifiable,
                    parent_aas
                )
            }
            return
        else:
            self.semantic_id_index[semantic_id].add(
                SemanticIndexElement(
                    referable,
                    parent_identifiable,
                    parent_aas
                )
            )

    def _index_semantic_ids_in_submodel(
            self,
            submodel: model.Submodel,
            submodel_identifier: model.Identifier,
            aas_identifier: Optional[model.Identifier] = None
    ):
        if submodel.semantic_id is not None:
            for key in submodel.semantic_id.key:
                self._add_semantic_id_to_index(
                    semantic_id=key,
                    referable=submodel,
                    parent_identifiable=submodel_identifier,
                    parent_aas=aas_identifier
                )
        for submodel_element in traversal.walk_submodel(submodel):
            if submodel_element.semantic_id:
                for key in submodel_element.semantic_id.key:
                    self._add_semantic_id_to_index(
                        semantic_id=key,
                        referable=submodel_element,
                        parent_identifiable=submodel_identifier,
                        parent_aas=aas_identifier
                    )

    def _add_identifiable_to_semantic_id_index(self, identifiable: model.Identifiable):
        # The following types of Identifiable exist:
        #  - Asset
        #  - AssetAdministrationShell
        #  - Submodel
        #  - ConceptDescription
        # For simplicity, I omit ConceptDescriptions and Assets
        if isinstance(identifiable, model.AssetAdministrationShell):
            aas_identifier: model.Identifier = identifiable.identification
            for submodel_reference in identifiable.submodel:
                submodel: model.Submodel = submodel_reference.resolve(self)
                submodel_identifier: model.Identifier = submodel.identification
                self._index_semantic_ids_in_submodel(
                    submodel=submodel,
                    submodel_identifier=submodel_identifier,
                    aas_identifier=aas_identifier
                )
        elif isinstance(identifiable, model.Submodel):
            submodel: model.Submodel = identifiable
            submodel_identifier: model.Identifier = identifiable.identification
            self._index_semantic_ids_in_submodel(
                submodel=submodel,
                submodel_identifier=submodel_identifier,
                aas_identifier=None
            )
        else:
            pass

    def _index_semantic_ids(self):
        """
        Iterate over all objects in the object store and build the `self.semantic_id_index`
        """
        self.semantic_id_index = {}
        for identifiable in self:
            self._add_identifiable_to_semantic_id_index(identifiable)
