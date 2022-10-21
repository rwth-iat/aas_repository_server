from typing import Dict, Set, Optional

from basyx.aas import model
from basyx.aas.backend import local_file
from basyx.aas.util import traversal


class RegistryObjectStore(local_file.LocalFileObjectStore):
    """
    This ObjectStore has the added functionality that it indexes all semanticIDs in the existing Identifiable objects.
    That way, it allows for searching the objects for occurrences of a semanticID.

    Note, that this is just a temporary solution, as it does not scale endlessly. But it slightly fancier than
    iterating over the whole ObjectStore every time we want a semanticId
    """
    def __init__(self, storage_directory: str):
        super().__init__(storage_directory)
        self.semantic_id_index: Dict[model.Key, Set[model.Identifier]] = {}
        # Todo: Check only for model.Key.value and id_type. The other two attributes are not well enough defined
        self._index_semantic_ids()

    def _add_semantic_id_to_index(self, semantic_id: model.Key, identifier: model.Identifier):
        """
        Adds a semanticID's Key to the index
        """
        if self.semantic_id_index.get(semantic_id) is None:
            self.semantic_id_index[semantic_id] = {identifier}
            return
        else:
            if identifier in self.semantic_id_index[semantic_id]:
                return   # Skip the (illogical) edge case, that a semanticID is already been used "up the tree"
                # in this identifiable (e.g. a submodel and a property inside that submodel have the same semanticID)
            self.semantic_id_index[semantic_id].add(identifier)

    def _index_semantic_ids_in_submodel(self, submodel: model.Submodel, identifier: Optional[model.Identifier] = None):
        if identifier is None:
            identifier = submodel.identification
        if submodel.semantic_id is not None:
            for key in submodel.semantic_id.key:  # type: ignore
                self._add_semantic_id_to_index(key, identifier)
        for submodel_element in traversal.walk_submodel(submodel):
            if submodel_element.semantic_id:
                for key in submodel_element.semantic_id.key:
                    self._add_semantic_id_to_index(key, identifier)

    def _add_identifiable_to_semantic_id_index(self, identifiable: model.Identifiable):
        # todo: I assume here that only submodels and submodel elements can have semanticIDs, but maybe
        #  someone should check this at some point?
        # Keep a reference of the identifiable's identifier, as we might need it later
        identifier: model.Identifier = identifiable.identification
        # The following types of Identifiable exist:
        #  - Asset
        #  - AssetAdministrationShell
        #  - Submodel
        #  - ConceptDescription
        # For simplicity, I omit ConceptDescriptions and Assets
        if isinstance(identifiable, model.AssetAdministrationShell):
            for submodel_reference in identifiable.submodel:
                self._index_semantic_ids_in_submodel(submodel_reference.resolve(self), identifier)
        elif isinstance(identifiable, model.Submodel):
            self._index_semantic_ids_in_submodel(identifiable)
        else:
            pass

    def _index_semantic_ids(self):
        """
        Iterate over all objects in the object store and build the `self.semantic_id_index`
        """
        self.semantic_id_index = {}
        for identifiable in self:
            self._add_identifiable_to_semantic_id_index(identifiable)
