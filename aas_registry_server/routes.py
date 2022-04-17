import datetime
import os
import configparser
import json
from typing import Optional, List, Dict

import flask
import jwt
import werkzeug.security

from basyx.aas import model
from aas_registry_server import auth


APP = flask.Flask(__name__)
config = configparser.ConfigParser()
config.read([
    os.path.join(os.path.dirname(__file__), "config.ini"),
    os.path.join(os.path.dirname(__file__), "config.ini.default")
])

# Read config file
JWT_EXPIRATION_TIME: int = int(config["AUTHENTICATION"]["TOKEN_EXPIRATION_TIME"])  # JWT Expiration Time in minutes
PORT: int = int(config["GENERAL"]["PORT"])


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


# @APP.route("/query_object", methods=["GET"])
# @auth.token_required
# def query(current_user: str):
#     """
#     Executes an SQL statement with an MySQL user, that only has `SELECT`, `CREATE VIEW` and `INDEX` and `SHOW VIEW`
#
#     Request format:
#
#     .. code-block::
#
#         {
#             "OBJ_TYPE": "<object type>",
#             "attribute": "<attribute name>",
#             "value": "<attribute value>",
#             "multi_result": <True/False, Default: True>
#         }
#
#     Return format: If `multi_result`: List of objects in JSON Dicts, else: JSON object Dict:
#
#     .. code-block::
#
#         [
#             {
#                 "OBJ_TYPE": "<object type>",
#                 <Rest of the object.from_dict() dict>
#             },
#             {
#                 "OBJ_TYPE": "<object type>",
#                 <Rest of the object.from_dict() dict>
#             }
#         ]
#
#     :returns:
#
#         - 200, with the result of the query as list of objects, as well as the object type in JSON
#         - 400, if the SQL request is missing items
#         - 404, if no result is found
#         - 412, if the request wants only one result, but multiple results are found
#         - 415, If invalid object type is given
#     """
#     data = flask.request.get_json(force=True)
#     # Check if all needed parameters are given
#     object_type_string: Optional[str] = data.get("OBJ_TYPE")
#     if not object_type_string:
#         return flask.make_response("Missing object type", 400)
#     attribute_name: Optional[str] = data.get("attribute")
#     if not attribute_name:
#         return flask.make_response("Missing attribute name", 400)
#     query_value: Optional[str] = data.get("value")
#     if not query_value:
#         return flask.make_response("Missing attribute value", 400)
#     multi_result: bool = data.get("multi_result") if data.get("multi_result") is not None else True
#     # Check if the object type can be fetched by string
#     object_type: Optional[model.BASE_CLASS_UNION] = model.STRING_TO_OBJECT_TYPE_MAP.get(object_type_string)
#     if not object_type:
#         return flask.make_response("Invalid Object type '{}'".format(object_type_string), 415)
#     # Check if the given attribute is in the object
#     if not object_type.__dict__.get(attribute_name):
#         return flask.make_response(
#             "Invalid attribute '{}' for object of type '{}'".format(attribute_name, object_type_string), 415
#         )
#     # Check if the MYSQL-Adapter has been initialized
#     if not MYSQL_ADAPTER.model_created:
#         MYSQL_ADAPTER.create_model()
#     # Query the object from the database
#     qu = MYSQL_ADAPTER.session.query(object_type).where(object_type.__dict__[attribute_name] == query_value)
#     if multi_result:
#         obj_list: List[model.BASE_CLASS_UNION] = qu.all()
#         obj_dict_list = []
#         for obj in obj_list:
#             obj_dict = obj.to_dict()
#             obj_dict_list.append(obj_dict)
#         return flask.make_response(json.dumps(obj_dict_list), 200)
#     else:
#         try:
#             obj: model.BASE_CLASS_UNION = qu.one()
#             obj_dict = obj.to_dict()
#             return flask.make_response(json.dumps(obj_dict), 200)
#         except sqlalchemy.orm.exc.NoResultFound:
#             return flask.make_response(
#                 "Cannot find '{}' where '{}' is '{}'".format(object_type_string, attribute_name, query_value), 404
#             )
#         except sqlalchemy.orm.exc.MultipleResultsFound:
#             return flask.make_response("More than one result found", 412)


if __name__ == '__main__':
    print("Running with configuration: {}".format({s:dict(config.items(s)) for s in config.sections()}))
    print("Found {} Users".format(len(auth.USERS)))
    APP.run(port=PORT)
