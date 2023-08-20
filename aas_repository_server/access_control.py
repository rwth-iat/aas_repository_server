import flask
import requests, json
from basyx.aas.model import Identifiable

from flask import abort
from basyx.aas import model


def create_OPA_input(request: flask.Request, user: str, ressource: str = None,
                 type: str = None):
    """
       Creates an input dictionary formatted for Open Policy Agent (OPA) evaluation based on the provided parameters.

       This function takes a Flask request object, user identifier, optional resource identifier, and optional type identifier
       and constructs an input dictionary suitable for use in OPA policy evaluations. The constructed input includes information
       about the HTTP method, path, user, resource, and type.

       Parameters:
       - request (flask.Request): The Flask request object representing the incoming HTTP request.
       - user (str): The identifier of the user making the request.
       - ressource (str, optional): The identifier of the requested resource, if applicable.
       - type (str, optional): The type of the requested resource, if applicable.

       Returns:
       - str: A JSON-formatted string representing the OPA input dictionary.
       """
    input= {
        "input": {
            "method": request.method,
            "path": request.path.rstrip('/').strip().split("/")[1:],
            "user": user,
        }
    }
    if ressource is not None:
        input["input"]["ressource"] = ressource
    if type is not None:
        input["input"]["type"] = type
    return json.dumps(input, indent=2)

def create_OPA_input_with_sub_secrurity(request: flask.Request, user_role: str, access_rights: dict):
    """
       Creates an input dictionary in the format suitable for sending to OPA, including access rules information
       extracted from submodel security.

       Args:
           request (flask.Request): The Flask request object containing the HTTP request information.
           user_role (str): The role of the user making the request.
           access_rights (dict): A dictionary containing access rights information.
       """
    input= {
        "input": {
            "method":request.method,
            "path": request.path.rstrip('/').strip().split("/")[1:],
            "role": user_role,
            "pathS": "",
            "roleS": {},
        }
    }
    for operation, roles in access_rights.items():
        input["input"]["pathS"] = [operation]
        input["input"]["roleS"] = {f"r{i + 1}": role for i, role in enumerate(roles)}
    return json.dumps(input, indent=2)

def check_authorization(app,input,url):
    """
        Perform authorization check using Open Policy Agent (OPA).

        This function sends a request to an OPA server to make an authorization decision based on the provided input.

        Parameters:
        - app (Flask): The Flask application instance.
        - input (str): The JSON-formatted input data for the OPA query.
        - url (str): The URL of the OPA server to send the query to.

        Returns:
        - None: This function directly interacts with the OPA server and handles authorization decisions.

        Raises:
        - HTTPException 500: If there is an issue with the OPA server's response.
        - HTTPException 401: If the authorization decision is denied.
        """
    app.logger.debug("OPA query: %s. Body: %s", url, input)
    response = requests.post(url, data=input)  # Ask OPA for decision
    if response.status_code != 200:
        app.logger.error("OPA status code: %s. Body: %s", response.status_code, response.json())
        abort(500)
    result=response.json()
    if url.endswith("/allow"):
        # if url ends with /allow, OPA only gives the value of allow back
        # OPA response format is { 'result': True/False }
        allowed = result.get("result", False)
    else:
        # if url does not end with /allow, OPA gives a dictionary back
        # OPA response format is { 'result': { 'allow': True/False } ... },
        allowed = result.get("result", {}).get("allow", False)
    app.logger.debug("OPA result: %s", result)
    if allowed:  # enforce decision
        print("You are allowed")
    else:
        print("Sorry, but you are not allowed to perform this action")
        abort(401) # status code 401: unauthorized

