package policy

import future.keywords.if

default allow := false

# Allow access if:
# - The user's role matches a role in the security submodel
# - The path matches the path in the security submodel
allow if {
    some idKey
    input.role == input.roleS[idKey]  
    input.path == input.pathS
}

# Access rules regarding who can post new resources to the server are defined separately.
# These rules do not depend on the resource, hence they are not stored in a security submodel.
# In this example only admins can add new resources to the server.
allow if {
    input.role == "admin"
    input.method == "POST"
}
