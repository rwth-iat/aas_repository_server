import datetime
import os
import configparser
import json
import logging
from typing import Optional, List, Dict

import flask
import jwt
import werkzeug.security


from basyx.aas import model
from basyx.aas.adapter.json import json_serialization, json_deserialization


from aas_repository_server\
    import auth, storage
from aas_repository_server.accessControl import check_authorization, create_OPA_input
from flask import stream_with_context, abort, Response, request


# todo: Config anpassen, parsing anpassen , storage anpassen


APP = flask.Flask(__name__)
config = configparser.ConfigParser()
config.read([
    os.path.join(os.path.dirname(__file__), "config.ini"),
    os.path.join(os.path.dirname(__file__), "config.ini.default")
])


# Read config file
# JWT Expiration Time in minutes
JWT_EXPIRATION_TIME: int = int(config["AUTHENTICATION"]["TOKEN_EXPIRATION_TIME"])
PORT: int = int(config["GENERAL"]["PORT"])
AAS_STORAGE_DIR: str = os.path.abspath(config["STORAGE"]["AAS_STORAGE_DIR"])
FILE_STORAGE_DIR: str = os.path.abspath(config["STORAGE"]["FILE_STORAGE_DIR"])
# Create Storage dir, if not existing
if not os.path.exists(AAS_STORAGE_DIR):
    os.makedirs(AAS_STORAGE_DIR)
if not os.path.exists(FILE_STORAGE_DIR):
    os.makedirs(FILE_STORAGE_DIR)
OBJECT_STORE: storage.RepositoryObjectStore = storage.RepositoryObjectStore(AAS_STORAGE_DIR)

""""OPA config"""
OPA_URL=config.get("OPA", "OPA_URL", fallback="http://localhost:8181/v1/data/policy/allow")  #Load OPA URL
APP.logger.setLevel(logging.DEBUG) # Set the logging level to DEBUG


@APP.route("/login", methods=["GET", "POST"])
def login_user():
    """
    Login a user with basic authentication and respond with a new JWT, if the authentication was successful.
    """
    if not flask.request.authorization \
            or not flask.request.authorization.username \
            or not flask.request.authorization.password:
        return flask.make_response("Unauthorized", 401)
    username: str = flask.request.authorization.username
    if not auth.check_if_user_exists(username):
        print("Unknown user '{}'".format(username))
        return flask.make_response("Invalid User or Password", 401)
    if werkzeug.security.check_password_hash(auth.get_password_hash(username), flask.request.authorization.password):
        token = jwt.encode(
            {
                'name': username,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=JWT_EXPIRATION_TIME)
            },
            auth.SECRET_KEY,
            algorithm="HS256"
        )
        print("User '{}' successful login".format(username))
        return flask.json.dumps({"token": token})
    else:
        print("User '{}' invalid password".format(username))
        return flask.make_response("Invalid User or Password", 401)


@APP.route("/test_connection", methods=["GET"])
def test_connection():
    """
    Returns "success", if everything is fine
    """
    return flask.make_response("Success", 200)


@APP.route("/test_authorized", methods=["GET"])
@auth.token_required
def test_authorized(current_user: str):
    """
    Tests if the connection can be established and the user is authorized

    :return:
    """
    return flask.json.dumps({"Connection": "ok", "User": current_user}), 200


@APP.route("/add_identifiable", methods=["POST"])
@auth.token_required
def add_identifiable(current_user: str):
    """
    Request format is a json serialized :class:`basyx.aas.model.base.Identifiable`:

    Add an identifiable to the repository.

    :returns:

        - 200
        - 400, if the request cannot be parsed
        - 409, if the Identifiable already exists in the OBJECT_STORE
    """
    data = flask.request.get_data(as_text=True)
    try:
        identifiable: Optional[model.Identifiable] = json.loads(data, cls=json_deserialization.AASFromJsonDecoder)
    except json.decoder.JSONDecodeError:
        return flask.make_response("Could not parse request, not valid JSON", 400)
    # Todo: Check here if the given user has access rights to the Identifiable
    try:
        input = create_OPA_input(request, current_user)
        check_authorization(APP, input,OPA_URL)
    except Exception as e:
        APP.logger.exception("Unexpected error querying OPA.")
        abort(500)
    try:
        if isinstance(identifiable, model.AssetAdministrationShell):  # insert the security metamodel automatically for new added AAS
            generate_security_submodel_template(identifiable)
        OBJECT_STORE.add(identifiable)
    except KeyError:
        return flask.make_response("Identifiable already exists in OBJECT_STORE", 200)
    return flask.make_response("Success", 200)



@APP.route("/modify_identifiable", methods=["PUT"])
@auth.token_required
def modify_identifiable(current_user: str):
    """
    Request format is a json serialized :class:`basyx.aas.model.base.Identifiable`:

    Modify an existing Identifiable by overwriting it with the given one.

    :returns:

        - 200
        - 400, if the request cannot be parsed
        - 404, if no result is found
    """
    data = flask.request.get_data(as_text=True)
    try:
        identifiable_new: Optional[model.Identifiable] = json.loads(data, cls=json_deserialization.AASFromJsonDecoder)
    except json.decoder.JSONDecodeError:
        return flask.make_response("Could not parse request, not valid JSON", 400)
    identifier: Optional[model.Identifier] = identifiable_new.identification
    identifiable_stored: Optional[model.Identifiable] = OBJECT_STORE.get(identifier)
    # Todo: Check here if the given user has access rights to the Identifiable
    access_rules = extract_accessRights_from_submodelSecurity(identifiable_stored, request.path.lstrip('/'))
    try:
        input = create_OPA_input(request, current_user, access_rules)
        check_authorization(APP, input, OPA_URL)
    except Exception as e:
        APP.logger.exception("Unexpected error querying OPA.")
        abort(500)
    if identifiable_stored is None:
        return flask.make_response("Could not find Identifiable with id {} in repository".format(identifier.id), 404)
    identifiable_stored.update_from(identifiable_new)
    return flask.make_response("Success", 200)


@APP.route("/get_identifiable", methods=["GET"])
@auth.token_required
def get_identifiable(current_user: str):
    """
    Request format is a json serialized :class:`basyx.aas.model.base.Identifier`:

    .. code-block::

        {
            "id": "<Identifier.id string>",
            "idType": "<idType string>"
        }

    Returns a JSON serialized :class:`basyx.aas.model.base.Identifiable`.

    :returns:

        - 200, with the Identifiable
        - 400, if the request cannot be parsed
        - 404, if no result is found
        - 422, if a valid AAS object was given, but not an Identifiable
    """
    data = flask.request.get_data(as_text=True)
    # Load the JSON from the request
    try:
        identifier_dict: Dict[str, str] = json.loads(data)
    except json.decoder.JSONDecodeError:
        return flask.make_response("Could not parse request, not valid JSON", 400)
    # Check that the request JSON contained in fact an Identifier
    try:
        identifier: model.Identifier = model.Identifier(
            id_=identifier_dict["id"],
            id_type=json_deserialization.IDENTIFIER_TYPES_INVERSE[identifier_dict["idType"]]
        )
    except KeyError:
        return flask.make_response("Request does not contain an Identifier", 422)
    # Try to resolve the Identifier in the object store
    identifiable: Optional[model.Identifiable] = OBJECT_STORE.get(identifier)
    # Todo: Check here if the given user has access rights to the Identifiable
    access_rules = extract_accessRights_from_submodelSecurity(identifiable, request.path.lstrip('/'))
    try:
        input= create_OPA_input(request, current_user, access_rules)
        check_authorization(APP, input,OPA_URL)
    except Exception as e:
        APP.logger.exception("Unexpected error querying OPA.")
        abort(500)
    if identifiable is None:
        return flask.make_response("Could not find Identifiable with id {} in repository".format(identifier.id), 404)
    return flask.make_response(
        json.dumps(identifiable, cls=json_serialization.AASToJsonEncoder, indent=4),
            200)


@APP.route("/get_file", methods=["GET"])
@auth.token_required
def get_file(current_user: str):
    """
    Request format is a String IRI

    Returns a File from the FILE_STORAGE_DIR.

    :returns:

        - 200, with the File
        - 404, if no result is found
    """
    file_iri = flask.request.get_data(as_text=True)
    file_iri = file_iri.strip('"')
    file_path_iri = file_iri.removeprefix('file:/')
    file_path: str = FILE_STORAGE_DIR+"/"+file_path_iri
    if not os.path.isfile(file_path):
        return flask.make_response("Could not fetch File with IRI {}".format(file_iri), 404)

    def generate():
        with open(file_path, mode='rb', buffering=4096) as myFmu:
            for chunk in myFmu:
                yield chunk
    return Response(stream_with_context(generate()))


@APP.route("/post_file", methods=["POST"])
@auth.token_required
def add_file(current_user: str):
    """
    Request format is a streamed File:

    Add an File to the FILE_STORAGE_DIR.

    :returns:

        - 200, and the IRI of the added FMU-File
        - 404, if the Path of the IRI does not exist
    """
    data = flask.request.get_data(cache=False)
    file_name = flask.request.headers.get("name")
    path_with_file = FILE_STORAGE_DIR+"/"+file_name
    print(path_with_file)
    with open(path_with_file, 'wb', buffering=4096) as myFmu:
        myFmu.write(data)
    file_iri: str = "file:"+file_name
    return flask.make_response(file_iri, 200)


@APP.route("/query_semantic_id", methods=["GET"])
@auth.token_required
def query_semantic_id(current_user: str):
    """
    Query the repository for a contained semanticID.

    Specify which attributes of the semanticID should be checked.
    Request format is a json serialized :class:`basyx.aas.model.base.Key` (from a Reference):

    .. code-block::

        {
            'semantic_id': {
                'type': 'GlobalReference',
                'idType': 'IRI',
                'value': 'https://example.com/semanticIDs/ONE',
                'local': False
            }
            'check_for_key_type': false,
            'check_for_key_local': false,
            'check_for_key_id_type': false,
        }

    Returns a list of Identifiers of the identifiable the semanticID is contained in
    and optionally, the Identifier of the parent AssetAdministrationShell, if it exists.

    .. code-block::

        [
            {
                'identifier': {
                    "id": "<Identifier.id string>",
                    "idType": "<idType string>"
                },
                'asset_administration_shell': {
                    "id": "<Identifier.id string>",
                    "idType": "<idType string>"
                }
            }
        ]

    :returns:

        - 200, with the above result
        - 400, if the request cannot be parsed
        - 422, if a valid AAS object was given, but not an Identifiable
    """
    data = flask.request.get_data(as_text=True)
    # Load the JSON from the request
    try:
        data_dict: Dict = json.loads(data)
    except json.decoder.JSONDecodeError:
        return flask.make_response("Could not parse request, not valid JSON", 400)
    # Check that the request has all the required fields
    try:
        check_for_key_type: bool = data_dict["check_for_key_type"]
        check_for_key_local: bool = data_dict["check_for_key_local"]
        check_for_key_id_type: bool = data_dict["check_for_key_id_type"]
        semantic_id: model.Key = model.Key(
            type_=json_deserialization.KEY_ELEMENTS_INVERSE[data_dict["semantic_id"]["type"]],
            local=True if data_dict["semantic_id"] else False,
            value=data_dict["semantic_id"]["value"],
            id_type=json_deserialization.KEY_TYPES_INVERSE[data_dict["semantic_id"]["idType"]]
        )
    except KeyError:
        return flask.make_response("Request does not have correct format", 422)
    # Get the list of identifiables that contain the semanticID
    result = OBJECT_STORE.get_semantic_id(
        semantic_id=semantic_id,
        check_for_key_type=check_for_key_type,
        check_for_key_local=check_for_key_local,
        check_for_key_id_type=check_for_key_id_type
    )
    # Todo: Check here if the given user has access rights to the Identifiable
    jsonable_result: List = []
    for semantic_index_element in result:
        print(semantic_index_element.semantically_identified_referable)
        identifiable: Optional[model.Identifiable] = OBJECT_STORE.get(semantic_index_element.parent_identifiable)
        access_rules = extract_accessRights_from_submodelSecurity(identifiable, request.path.lstrip('/'))
        try:
            input = create_OPA_input(request, current_user, access_rules)
            check_authorization(APP, input, OPA_URL)
        except Exception as e:
            APP.logger.exception("Unexpected error querying OPA.")
            abort(500)
        jsonable_result.append(
            {
                "identifier": semantic_index_element.parent_identifiable,
                "asset_administration_shell": semantic_index_element.parent_asset_administration_shell
            }
        )
    return flask.make_response(
        json.dumps(
            jsonable_result,
            cls=json_serialization.AASToJsonEncoder,
            indent=4
        ),
        200
    )


def generate_security_submodel_template(aas: model.AssetAdministrationShell):
    """
      Generate a security submodel template and add it to the given Asset Administration Shell (AAS).

      This function creates a simplified version of security submodel template, which defines default access rights and security rules for the contain of
      corresponding AAS. It adds the generated security submodel to the given AAS.

      Parameters:
          aas (model.AssetAdministrationShell): The Asset Administration Shell to which the security submodel
                                                  will be added.

      Returns:
          None
"""
    # Create the Security Submodel
    securitySubmodel=model.Submodel(
        identification=model.Identifier(
            id_="https://acplt.org/Security_Submodel",
            id_type=model.IdentifierType.IRI
        ),
        id_short="SecuritySubmodel",
        semantic_id=model.Reference(tuple([
            model.Key(
                type_=model.KeyElements.GLOBAL_REFERENCE,
                local=False,
                value="http://acplt.org/Security_SubmodelSemanticID",
                id_type=model.KeyType.IRI
            )
        ])),
        # For simplicity, I assumed a simplified structure of the security submodel
        submodel_element={
            model.SubmodelElementCollectionOrdered(
                id_short= "Set_of_security_Rules_for_AAS",
                value=[model.ReferenceElement(
                    id_short='Resource_Reference',
                    value=model.Reference(
                        (model.Key(
                            type_=model.KeyElements.GLOBAL_REFERENCE,
                            local=False,
                            value=aas.identification.id,  # refer to the AAS
                            id_type=model.KeyType.IRI
                        ),)
                    ),
                ),
                    model.Property(
                        id_short="rules",
                        value_type=model.datatypes.String,
                        value=str(
                            ["get_identifiable", ['admin', 'rwthStudent', 'otherStudent'], "modify_identifiable",
                             ['admin'], "query_semantic_id", ['admin', 'rwthStudent', 'otherStudent']]),
                    ),]
               ),
        }
    )
    submodels = [reference.resolve(OBJECT_STORE)
                 for reference in aas.submodel]
    for submodel in submodels:
        if submodel.semantic_id != model.Reference(tuple([
            model.Key(
                type_=model.KeyElements.GLOBAL_REFERENCE,
                local=False,
                value="http://acplt.org/Security_SubmodelSemanticID",
                id_type=model.KeyType.IRI
            )])):
            AccessRules_otherSubs = model.SubmodelElementCollectionOrdered(
                # Access rules for submodels excluding the security submodel.
                id_short="Reference to '{}'".format(submodel.id_short),
                value=[model.ReferenceElement(
                    id_short='Resource_Reference',
                    value=model.Reference(
                        (model.Key(
                            type_=model.KeyElements.GLOBAL_REFERENCE,
                            local=False,
                            value=securitySubmodel.identification.id,  # refer to the AAS
                            id_type=model.KeyType.IRI
                        ),)
                    ),
                ),
                    model.Property(
                        id_short="AccessRules for '{}'".format(submodel.id_short),
                        value_type=model.datatypes.String,
                        value=str(["get_identifiable", ['admin', 'rwthStudent', 'otherStudent'], "modify_identifiable", ['admin', 'rwthStudent'],
                                  "query_semantic_id", ['admin', 'rwthStudent', 'otherStudent']]),
                    ), ]
            )
            securitySubmodel.submodel_element.add(AccessRules_otherSubs)


    AccessRules_Subsec=model.SubmodelElementCollectionOrdered( #Access Rules for Security Submodel
                id_short="Reference_to_Submodel_Security",
                value=[model.ReferenceElement(
                    id_short='Resource_Reference',
                    value=model.Reference(
                        (model.Key(
                            type_=model.KeyElements.GLOBAL_REFERENCE,
                            local=False,
                            value=securitySubmodel.identification.id,  # refer to the AAS
                            id_type=model.KeyType.IRI
                        ),)
                    ),
                ),
                    model.Property(
                        id_short='AccessRules_SubSec',
                        value_type=model.datatypes.String,
                        value=str(["get_identifiable", ['admin'], "modify_identifiable", ['admin'], "query_semantic_id", ['admin']]),
                    ), ]
            )
    securitySubmodel.submodel_element.add(AccessRules_Subsec) # Add the security rules for submodels security in Submodel security itself
    #add the security submodel to the given aas
    OBJECT_STORE.add(securitySubmodel)
    aas.submodel.add(model.AASReference.from_referable(securitySubmodel))



def extract_accessRights_from_submodelSecurity(identifiable: model.Identifiable, endpoint: str):
    """
    Extract access rights for a specific endpoint and a specific ressource from the security submodel of an Identifiable.

    This function retrieves access rights from the security submodel associated with the provided Identifiable.
    If the provided Identifiable is not an AAS, the function will attempt to locate the corresponding AAS.
    It searches for the security submodel within the Identifiable and returns the extracted access rights as a dictionary.

    Parameters:
        identifiable (model.Identifiable): The Identifiable from which to extract access rights.

    Returns:
        dict: A dictionary containing the extracted access rights.

    Example Output: {'get_identifiable': ['admin', 'rwthStudent', 'otherStudent']}

    Note:
        - This function assumes a specific structure of the security submodel for access rights extraction.
        - The Identifiable should be either a Submodel or an AAS
    """
    submodelSecurity: model.Submodel
    access_rights = {}  # Dictionary to store security rules from submodel security
    aas: model.AssetAdministrationShell

    if isinstance(identifiable, model.Submodel): # if the identifiable is a submodel, retrieve the corresponding AAS
        aas=OBJECT_STORE.find_aas_containing_submodel(identifiable)
    elif isinstance(identifiable, model.AssetAdministrationShell):
        aas=identifiable

    # Let's create a list of all submodels, to which the AAS has references, by resolving each of the submodel references:
    submodels = [reference.resolve(OBJECT_STORE)
                 for reference in aas.submodel]
    # retrieve the submodel security by its semantic ID
    for submodel in submodels:
        if submodel.semantic_id == model.Reference(tuple([
    model.Key(
        type_=model.KeyElements.GLOBAL_REFERENCE,
        local=False,
        value="http://acplt.org/Security_SubmodelSemanticID",
        id_type=model.KeyType.IRI
    )])):
            submodelSecurity = submodel
            break  # Exit the loop after finding the security submodel
    else:
        raise ValueError("No security submodel could be associated with the provided ressource")

    for submodel_element in submodelSecurity.submodel_element :
        if isinstance(submodel_element, model.SubmodelElementCollectionOrdered):
            for element in submodel_element.value:
                if isinstance(element, model.ReferenceElement):
                    if element.value== model.Reference(tuple([
                                        model.Key(
                                        type_=model.KeyElements.GLOBAL_REFERENCE,
                                        local=False,
                                        id_type=model.KeyType.IRI,
                                        value=identifiable.identification.id)])):  # Check if the ReferenceElement, refer to the identifiable
                        for prop in submodel_element.value:
                            if isinstance(prop, model.Property):
                                value_list = eval(prop.value)
                                # Iterate through the list to extract access rules
                                i = 0
                                while i < len(value_list):
                                    operation = value_list[i]
                                    roles = value_list[i + 1]
                                    if operation==endpoint:
                                        access_rights[operation] = roles
                                        break
                                    i += 2
                    break
    print("rules:",access_rights)
    return access_rights

#configure the logging
logger = logging.getLogger('audit')
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='audit.log',  # Specify the file to store audit logs
    filemode='a'  # Append mode
)

# Create a FileHandler for the audit logger
file_handler = logging.FileHandler('audit.log')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)


@APP.after_request
def after_request(response):
    """ execute this after each request to extract relevant information from the request and response to create an audit log. """

    logger.info({
                          "time": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                          "user_ip": request.remote_addr,
                          #"user_name": g.user,
                          "method": request.method,
                          "request_url": request.path,
                          "response_status": response.status}
    )
    return response


if __name__ == '__main__':
    print("Running with configuration: {}".format({s: dict(config.items(s)) for s in config.sections()}))
    print("Found {} Users".format(len(auth.USERS)))
    APP.run(port=PORT)


