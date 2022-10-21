# AAS Repository Server

An Implementation of an AssetAdministrationShell Repository server, 
using the [Eclipse BaSyx Python SDK](https://github.com/eclipse-basyx/basyx-python-sdk).

## How to Use (Further features follow):

In order to add AASs to the repository, you need a script, that does the following:

    1. Read the AAS in to the Python SDK
    2. Import the `storage.RegistryObjectStore` 
    3. Add them to the RegistryObjectStore via the `.add()` function 

To run the server, copy the `config.ini.default` to `config.ini` and edit the settings to make sense for you.
Then run `routes.py`.
