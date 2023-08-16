# Asset Administration Shell (AAS) Access Control Implementation

## Introduction

This repository implements access control mechanisms for managing the security and permissions of an Asset Administration Shell (AAS). Access control ensures that only authorized users can perform specific actions on the AAS and its submodels.

## Access Control Mechanism

Access control is achieved through a combination of user authentication(not yet implemented), authorization rules, and the use of an external authorization service, such as Open Policy Agent (OPA).

### Authorization Rules

- Authorization rules define what actions different user roles are allowed to perform on the AAS and its submodels.

### Open Policy Agent (OPA)

- OPA is used to evaluate authorization policies against incoming requests. Policies define the conditions under which a request is authorized or denied.
  For more about OPA, see https://www.openpolicyagent.org/docs/latest/

## License

## Dependencies


## Getting Started

2. **Authorization Rules Setup**:
   - Define the roles and corresponding permissions (actions) they are allowed to perform.
   - Example roles: admin, rwthStudent, otherStudent.

3. **Policy Definition**:
   - Define authorization policies using the Rego policy language supported by OPA.
   - Policies should be granular and cover different scenarios.

4. **Policy Evaluation with OPA**:
   - Integrate OPA with your AAS repository server.
   - Configure OPA to receive requests for policy evaluation.
   - Use the OPA API to send requests and receive authorization decisions.

5. **Access Control in Routes**:
   - In each route of the AAS repository server, apply access control checks before processing requests.
   - Retrieve user roles from the authentication token.
   - Send the user roles and other relevant information to OPA for policy evaluation.
   - Implement error handling for denied requests.


## Security Submodel

- A Security Submodel is automatically added to each new AAS.
- The Security Submodel contains access control rules for the AAS, its submodels, and specific actions.

## Contributing

- Contributions to this access control implementation are welcome! If you find bugs or have suggestions for improvements, please open an issue or a pull request.



