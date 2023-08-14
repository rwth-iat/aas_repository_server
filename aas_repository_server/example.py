import typing
Policy = dict[str, typing.Any]
from urllib import parse
from aas_repository_server.exceptions import InvalidPolicy


def convert_to_rego(python_policy: str) -> str:
    """Convert a Python policy to Rego format.

    :param python_policy: Policy written in Python.
    :return: Policy in Rego format.
    """
    rego_policy = 'package policy\n\n'
    rego_policy += 'import future.keywords.if\n\n'
    rego_policy += 'default allow := false\n\n'

    for role, rights in python_policy.items():
        for method, path in rights:
            rego_policy += f'allow if  \n{{\n  input.path ==["{path}"]\n  input.method == "{method}"\n}}\n\n'
    return rego_policy


def save_policy_as_rego(id: str, policy: str) -> Policy:
    """Create or update a policy and store it as a Rego file.

    :param id: Id of the policy.
    :param policy: Policy written in Python.

    """
    rego_policy = convert_to_rego(policy)
    rego_filename = f"{id}.rego"

    # Save the Rego policy to a file
    with open(rego_filename, "w") as rego_file:
        rego_file.write(rego_policy)
"""""
    path = parse.urljoin("/v1/policies/", id)
    resp = request("put", path, data=rego_policy)

    if resp.ok:
        return typing.cast(Policy, resp.json())
    if resp.status_code == 400:
        raise InvalidPolicy(resp.json())

    raise ConnectionError("Unable to save policy.")
    
subject_roles = {
        "admin": ["GET", "POST", "PUT"],
        "rwthStudent": ["GET", "POST"],
        "otherStudent": ["GET"],
        # Add more subject roles and access rights as needed
    }
    """
subject_roles= {
    "admin": [("GET", "get_identifiable"), ("POST", "add_identifiable")],}
save_policy_as_rego("pi1", subject_roles)