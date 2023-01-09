# AAS Repository Server

An Implementation of an AssetAdministrationShell Repository server, 
using the [Eclipse BaSyx Python SDK](https://github.com/eclipse-basyx/basyx-python-sdk).


## Features

* Login with a username and password
* Store Identifiables and FMU-Files
* Make changes to the storage
* Downloading Identifiables and FMU-Files via the [client](https://github.com/acplt/aas_repository_client)


## License

The AAS Repository Server project is licensed under the terms of the Eclipse Public License v. 2.0.

SPDX-License-Identifier: EPL-2.0

or the Apache License, Version 2.0

SPDX-License-Identifier: Apache-2.0


## Dependencies

The AAS Repository Server requires the following Python packages to be installed. These dependencies are listed in
`requirements.txt`:
* `basyx-python-sdk` and its dependencies (MIT License)
* `werkzeug` (BSD 3-clause License)
* `flask` ( BSD-3-Clause license)
* `PyJWT` (MIT License)


## Getting Started

### Installation

For working with the current development version, you can install the package directly from GitHub, using Pip's Git feature:
```bash
pip install git+https://github.com/acplt/aas_repository_server.git@main
```

You may want to use a Python's `venv` or a similar tool to install BaSyx Python SDK and its dependencies only in a project-specific local environment. 


### How to Use

To run the server, copy the `config.ini.default` to `config.ini` and edit the settings to make sense for you.
Username and password need to be added to `users.dat`.
Then run `routes.py`.


### Example

The following code shows how to log-in and add an identifiable to the AAS Repository Server

How to `Log-in`:
```python
from aas_repository_client.aas_repository_client import client
client = client.AASRepositoryClient("http://127.0.0.1:2234", username="admin")
client.login(password="admin")
```

Add an `identifiable` to the AAS Repository Server:
```python
client.add_identifiable(
        model.Submodel(identification=model.Identifier(id_="https://acplt.org/Simple_Submodel",
                                                       id_type=model.IdentifierType.IRI),
                       semantic_id=model.Reference((model.Key(type_=model.KeyElements.GLOBAL_REFERENCE,
                                                              local=False,
                                                              value='http://acplt.org/Properties/SimpleProperty',
                                                              id_type=model.KeyType.IRI),))), )
```

Get an `identifiable` from the AAS Repository Server:
```python
client.get_identifiable(model.Identifier(id_="https://acplt.org/Simple_Submodel", id_type=model.IdentifierType.IRI))
```


## Development

### Codestyle

Our code follows the [PEP 8 -- Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/).
Additionally, we use [PEP 484 -- Type Hints](https://www.python.org/dev/peps/pep-0484/) throughout the code to enable type checking the code.