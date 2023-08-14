import flask
import requests, json

from flask import abort


def create_OPA_input(request: flask.Request, user: str, ressource: str = None, #opa input
                 type: str = None):
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


class AuthorizationError(Exception):
    """Exception raised when authorization fails."""
