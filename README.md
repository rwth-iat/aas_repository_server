# Asset Administration Shell (AAS) Access Control Implementation

## Introduction

This repository implements access control mechanisms for managing the security and permissions of an Asset Administration Shell (AAS). Access control ensures that only authorized users can perform specific actions on the AAS and its submodels.

## Access Control Mechanism

Access control is achieved through a combination of user authentication(not yet implemented), authorization rules, and the use of an external authorization service, such as Open Policy Agent (OPA).

### Authorization Rules

- Authorization rules define what actions different user roles are allowed to perform on the AAS and its submodels.

### Open Policy Agent (OPA)

- OPA is used to evaluate authorization policies against incoming requests. Policies define the conditions under which a request is authorized or denied.
  For more about OPA, see https://www.openpolicyagent.org/docs/latest/ and https://github.com/open-policy-agent/opa

## Getting Started
1. **download and configure OPA**:
    Please note that the URLs mentioned here are based on the information available at the time of writing, so make sure to check for the latest versions and updates on the official OPA website or repository.
   - Download the source code of OPA https://github.com/open-policy-agent/opa/archive/refs/tags/v0.55.0.zip and extract the downloaded ZIP file to a location on your system.
   - Download the OPA executable, rename the downloaded executable to 'opa.exe' and move  move the executable to the folder where you extracted the OPA source code:
   For Windows: https://openpolicyagent.org/downloads/v0.55.0/opa_windows_amd64.exe
   For linux: https://github.com/open-policy-agent/opa/releases/download/v0.55.0/opa_linux_amd64
   -  If you use linux, you may need to set executable permissions for the OPA executable. To do this open a terminal window and navigate to the folder where the OPA executable is located. Run the following command: 
   chmod 755 ./opa
   - To verify that OPA is correctly installed and configured, open a terminal or command prompt and navigate to the folder where the OPA executable is located. Run the following command to check the version of OPA:
   ./opa version
   If you see the version information printed, OPA is successfully installed and configured.

2. **Authorization Rules Setup**:
   - Define the roles and corresponding permissions (actions) they are allowed to perform.
   - Example roles: admin, rwthStudent, otherStudent.

3. **Policy Definition**:
   - Define authorization policies using the Rego policy language supported by OPA.
   - You can start with the example policy (policy.rego file) provided in this repository and adjust it according to your needs 
   - See https://www.openpolicyagent.org/docs/latest/#rego for more about the rego language
   - You can also experiment with rego and test policy code online: https://play.openpolicyagent.org/
   
4. **Policy Evaluation with OPA**:
   - OPA is already configure to listen on http://localhost:8181/v1/data/policy/allow, you can change this in the config.ini.default file
   - Run OPA as Server by navigating to the folder containing the OPA executable in the terminal and running the following command:
   opa run --server --set default_decision=policy.main policy.rego
   Replace "policy.rego" with the actual name of your policy file.
   - Start your AAS Repository Server as you normally would.

5. **Access Control in Routes**:
   - In each route of the AAS repository server, apply access control checks before processing requests.
   - Retrieve user roles from the authentication token.
   - Send the user roles and other relevant information to OPA for policy evaluation.
   - Implement error handling for denied requests.


## Security Submodel

- A Security Submodel is automatically added to each new AAS.
- The Security Submodel contains access control rules for the AAS, its submodels, and specific actions.

## Dependencies

## License

## Contributing

- Contributions to this access control implementation are welcome! If you find bugs or have suggestions for improvements, please open an issue or a pull request.



