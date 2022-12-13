import datetime
import os
import configparser
import json
from typing import Optional, Set, Dict

import flask
import jwt
import werkzeug.security

from basyx.aas import model
from basyx.aas.adapter.json import json_serialization, json_deserialization
#from aas_repository_server import auth, storage
import auth, storage
from flask import stream_with_context, Response
import zipfile

# todo: Config anpassen, parsing anpassen , storage anpassen
APP = flask.Flask(__name__)
config = configparser.ConfigParser()
config.read([
    os.path.join(os.path.dirname(__file__), "config.ini"),
    os.path.join(os.path.dirname(__file__), "config.ini.default")
])

# Read config file
JWT_EXPIRATION_TIME: int = int(config["AUTHENTICATION"]["TOKEN_EXPIRATION_TIME"])  # JWT Expiration Time in minutes
PORT: int = int(config["GENERAL"]["PORT"])
#anpassen (Name)
AAS_STORAGE_DIR: str = os.path.abspath(config["STORAGE"]["AAS_STORAGE_DIR"])
#OBJECT Store mit AAS_ initialisieren
OBJECT_STORE: storage.RegistryObjectStore = storage.RegistryObjectStore(AAS_STORAGE_DIR)
# todo: Create storage dir, if not existing
# todo: Add Second FMU storage (Datei liegt im Ordner und rausholen(wie Datei laden), get_fmu())



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
        OBJECT_STORE.add(identifiable)
    except KeyError:
        return flask.make_response("Identifiable already exists in OBJECT_STORE", 200)
    return flask.make_response("OK", 200)

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
    if identifiable_stored is None:
        return flask.make_response("Could not find Identifiable with id {} in repository".format(identifier.id), 404)
    identifiable_stored.update_from(identifiable_new)
    return flask.make_response("OK", 200)

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
    if identifiable is None:
        return flask.make_response("Could not find Identifiable with id {} in repository".format(identifier.id), 404)
    return flask.make_response(
        json.dumps(identifiable, cls=json_serialization.AASToJsonEncoder, indent=4),
        200
    )

@APP.route("/get_fmu", methods=["GET"])
@auth.token_required
def get_fmu(current_user: str):
    """
    Request format is a String IRI

    Returns a compressed FMU-File.

    :returns:

        - 200, with the FMU-File
        - 404, if no result is found
    """
    fmu_IRI = flask.request.get_data(as_text=True)
    fmu_storage_dir: str = os.path.abspath(config["STORAGE"]["FMU_STORAGE_DIR"])
    fmu_IRI = fmu_IRI.strip('"')
    file_path_IRI = fmu_IRI.removeprefix('file:/')
    file_path: str = fmu_storage_dir+"\\"+file_path_IRI
    if not os.path.isfile(file_path):
        return flask.make_response("Could not fetch FMU-File with IRI {}".format(fmu_IRI), 404)
    def generate():
        with open(file_path, mode='rb', buffering=4096) as myzip:
            for chunk in myzip:
                yield chunk
    return Response(stream_with_context(generate()))

@APP.route("/add_fmu", methods=["POST"])
@auth.token_required
def add_fmu(current_user: str):
    """
    Request format is a streamed FMU-File:

    Add an FMU-File to the repository.

    :returns:

        - 200
        - 404, if the PAth of the IRI does not exist
    """
    data = flask.request.get_data(cache=False)
    fmu_IRI = flask.request.headers.get("IRI")
    fmu_storage_dir: str = os.path.abspath(config["STORAGE"]["FMU_STORAGE_DIR"])
    path_with_fmu = fmu_storage_dir+(fmu_IRI.removeprefix("file:"))
    path_without_fmu = '/'.join(path_with_fmu.split('/')[:-1])
    if not os.path.isdir(path_without_fmu):
        return flask.make_response("Path of IRI: {} does not exist".format(fmu_IRI), 404)
    #!wird FMU ueberschrieben!?
    with open(path_with_fmu, 'wb', buffering=4096) as myzip:
        myzip.write(data)
    return flask.make_response("FMU with IRI: {} was added to the Server".format(fmu_IRI), 200)

@APP.route("/query_semantic_id", methods=["GET"])
@auth.token_required
def query_semantic_id(current_user: str):
    """
    Query all Identifiable objects that either have a semanticID or contain a child having that semanticID.

    Request format is a json serialized :class:`basyx.aas.model.base.Key` (from a Reference):

    .. code-block::

        {
            'type': 'GlobalReference',
            'idType': 'IRI',
            'value': 'https://example.com/semanticIDs/ONE',
            'local': False
        }

    Returns a list of identifiers (in no particular order) that contain that semanticID

    :returns:

        - 200, with the List of Identifiers
        - 400, if the request cannot be parsed
        - 422, if a valid AAS object was given, but not an Identifiable
    """
    data = flask.request.get_data(as_text=True)
    # Load the JSON from the request
    try:
        key_dict: Dict[str, str] = json.loads(data)
    except json.decoder.JSONDecodeError:
        return flask.make_response("Could not parse request, not valid JSON", 400)
    # Check that the request JSON contained in fact an Identifier
    try:
        semantic_id_key: model.Key = model.Key(
            type_=json_deserialization.KEY_ELEMENTS_INVERSE[key_dict["type"]],
            local=True if key_dict["local"] else False,
            value=key_dict["value"],
            id_type=json_deserialization.KEY_TYPES_INVERSE[key_dict["idType"]]
        )
    except KeyError:
        return flask.make_response("Request does not contain a Key", 422)
    # Get the list of identifiables that contain the semanticID
    identifiers: Optional[Set[model.Identifier]] = OBJECT_STORE.semantic_id_index.get(semantic_id_key)
    # Todo: Check here if the given user has access rights to the Identifiable
    if identifiers is None:
        identifiables = set([])  # Set the identifiables to an empty set
    return flask.make_response(
        json.dumps(list(identifiers), cls=json_serialization.AASToJsonEncoder, indent=4),
        200
    )


if __name__ == '__main__':
    print("Running with configuration: {}".format({s: dict(config.items(s)) for s in config.sections()}))
    print("Found {} Users".format(len(auth.USERS)))
    APP.run(port=PORT)
