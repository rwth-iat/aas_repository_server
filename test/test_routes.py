import unittest
import requests.auth
import json

from basyx.aas import model
from basyx.aas.adapter.json import json_serialization, json_deserialization
from aas_registry_server import routes, auth


class HTTPServerTestUnauthorizedPaths(unittest.TestCase):
    def setUp(self) -> None:
        routes.APP.config["TESTING"] = True
        routes.APP.config['WTF_CSRF_ENABLED'] = False
        routes.APP.config['DEBUG'] = True
        auth.add_user("test", "test")  # Add a test user to the User DB
        self.test_client = routes.APP.test_client()

    def tearDown(self) -> None:
        auth.remove_user("test")  # Remove the test user from the User DB

    def test_main_page(self):
        response = self.test_client.get("/", follow_redirects=True)
        self.assertEqual(response.status_code, 404)

    def test_connection(self):
        response = self.test_client.get("/test_connection")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode("utf-8"), "Success")

    def test_login_fail(self):
        response = self.test_client.get("/login")
        self.assertEqual(response.status_code, 401)

    def test_login_success(self):
        headers = {"Authorization": requests.auth._basic_auth_str("test", "test")}
        response = self.test_client.get("/login", headers=headers)
        self.assertEqual(response.status_code, 200)


class TestGetIdentifiable(unittest.TestCase):
    def setUp(self) -> None:
        routes.APP.config["TESTING"] = True
        routes.APP.config['WTF_CSRF_ENABLED'] = False
        routes.APP.config['DEBUG'] = True
        auth.add_user("test", "test")  # Add a test user to the User DB
        self.test_client = routes.APP.test_client()
        login = self.test_client.get("/login", headers={"Authorization": requests.auth._basic_auth_str("test", "test")})
        self.token: str = json.loads(login.data)["token"]
        self.auth_headers = {"x-access-tokens": "{}".format(self.token)}

    def tearDown(self) -> None:
        auth.remove_user("test")  # Remove the test user from the User DB

    def test_authorized(self):
        response = self.test_client.get("/test_authorized", headers=self.auth_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {"Connection": "ok", "User": "test"})

    def test_get_identifiable_success(self):
        # Put some Identifiable into the object store
        identifier: model.Identifier = model.Identifier(
            id_="https://example.com/sm/test_submodel",
            id_type=model.IdentifierType.IRI
        )
        identifiable: model.Submodel = model.Submodel(
            identification=identifier,
            id_short="exampleSM"
        )
        routes.OBJECT_STORE.add(identifiable)
        # Get the identifiable via it's id
        response = self.test_client.get(
            "/get_identifiable",
            headers=self.auth_headers,
            data=json.dumps(identifier, cls=json_serialization.AASToJsonEncoder)
        )
        self.assertEqual(200, response.status_code)
        # Check that the returned object is equal to the one that we want
        sm = json.loads(response.data, cls=json_deserialization.AASFromJsonDecoder)
        self.assertIsInstance(sm, model.Submodel)
        self.assertEqual(sm.identification, identifiable.identification)
        self.assertEqual(sm.id_short, identifiable.id_short)
        # Clean up object store
        routes.OBJECT_STORE.remove(identifiable)

    def test_get_identifiable_fail_400(self):
        response = self.test_client.get(
            "/get_identifiable",
            headers=self.auth_headers,
            data="Some senseless data"
        )
        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "Could not parse request, not valid JSON",
            response.data.decode("utf-8")
        )

    def test_get_identifiable_fail_404(self):
        # Request some identifier that is not in the object store
        identifier: model.Identifier = model.Identifier(
            id_="https://example.com/sm/unknown_submodel",
            id_type=model.IdentifierType.IRI
        )
        response = self.test_client.get(
            "/get_identifiable",
            headers=self.auth_headers,
            data=json.dumps(identifier, cls=json_serialization.AASToJsonEncoder)
        )
        self.assertEqual(404, response.status_code)
        self.assertEqual(
            "Could not find Identifiable with id https://example.com/sm/unknown_submodel in repository",
            response.data.decode("utf-8")
        )

    def test_get_identifiable_fail_422(self):
        prop = model.Property(id_short="iAM", value_type=model.datatypes.String, value="A wrong datatype")
        response = self.test_client.get(
            "/get_identifiable",
            headers=self.auth_headers,
            data=json.dumps(prop, cls=json_serialization.AASToJsonEncoder)
        )
        self.assertEqual(422, response.status_code)
        self.assertEqual(
            "Request does not contain an Identifier",
            response.data.decode("utf-8")
        )
