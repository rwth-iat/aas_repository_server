import flask
import requests, json
from basyx.aas.model import Identifiable

from flask import abort
from basyx.aas import model
from basyx.aas.util import traversal


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


def extract_accessRights_from_submodelSecurity(aas_id: model.AssetAdministrationShell):

    #this should be adapted based on the structure of the Security Submodel
    submodel_security = {}  # Dictionary to store submodel security roles
    ressource_identifier = None  # Initialize the resource identifier
    # remenber to implement exception, e.g when ressource_identifier is none, what if no security Submodel is found
    # Iterate through the submodel elements of the Security Submodel
    """""
    security_submodel = None
    for submodel in aas_id.submodel:
        if submodel. == 'https://acplt.org/Security_Submodel':
            security_submodel = submodel
            break
    for submodel_element in traversal.walk_submodel(submodel):
    for submodel_element in aas_id.submodel("SecuritySubmodel"):
        if submodel_element.id_short == "ressource":
            ressource_identifier = submodel_element.value
        elif submodel_element.id_short == "read":
            submodel_security['read'] = submodel_element.value
        elif submodel_element.id_short == "modify":
            submodel_security['modify'] = submodel_element.value
    """""
    return ressource_identifier, submodel_security




def create_rego_file(ressource_identifier, submodels_security):
    # Assuming you have a dictionary of submodels_security, where keys are submodel id_short and values are lists of roles
    # For example: submodels_security = {'read': ['admin', 'rwthStudent', 'otherStudent'], 'modify': ['admin']}

    rego_policy = f'''
package access

default allow = false

allow {{
    input.method = "GET"
    input.ressource = "{ressource_identifier}"
    input.role = role
    role = {submodels_security['read']}
}}

allow {{
    input.method = "PUT"
    input.ressource = "{ressource_identifier}"
    input.role = role
    role = {submodels_security['modify']}
}}
    '''

    with open('policy.rego', 'w') as f:
        f.write(rego_policy)


class AuthorizationError(Exception):
    """Exception raised when authorization fails."""
