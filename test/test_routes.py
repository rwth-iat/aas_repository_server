import unittest
import requests.auth
import json

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


# class HTTPServerTestAuthorizedPaths(unittest.TestCase):
#     def setUp(self) -> None:
#         http_server.APP.config["TESTING"] = True
#         http_server.APP.config['WTF_CSRF_ENABLED'] = False
#         http_server.APP.config['DEBUG'] = True
#         http_server.MYSQL_ADAPTER = mysql_adapter.MySQLAdapter(testing=True)
#         auth.add_user("test", "test")  # Add a test user to the User DB
#         self.test_client = http_server.APP.test_client()
#         login = self.test_client.get("/login", headers={"Authorization": requests.auth._basic_auth_str("test", "test")})
#         self.token: str = json.loads(login.data)["token"]
#         self.auth_headers = {"x-access-tokens": "{}".format(self.token)}
#
#     def tearDown(self) -> None:
#         auth.remove_user("test")  # Remove the test user from the User DB
#
#     def test_authorized(self):
#         response = self.test_client.get("/test_authorized", headers=self.auth_headers)
#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(json.loads(response.data), {"Connection": "ok", "User": "test"})
#
#     def test_insert_success(self):
#         obj: model.Exchange = model.Exchange(name="TestExchange", uri="uri")
#         data = obj.to_dict()
#         response = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(response.status_code, 201)
#         ac = http_server.MYSQL_ADAPTER.session.query(model.Exchange).where(
#             model.Exchange.name == "TestExchange"
#         ).one()
#         obj.id = ac.id
#         self.assertEqual(ac, obj)
#
#     def test_insert_fail_400(self):
#         data = {
#             "something": "other"
#         }
#         response = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(400, response.status_code)
#         self.assertEqual("Missing object type", response.data.decode("utf-8"))
#
#         data = {
#             "OBJ_TYPE": "exchange"
#         }
#         response = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(400, response.status_code)
#         self.assertEqual(
#             "Cannot instantiate 'exchange' object with given data",
#             response.data.decode("utf-8")
#         )
#
#     def test_insert_fail_409(self):
#         obj: model.Exchange = model.Exchange(name="TestExchange", uri="uri")
#         data = obj.to_dict()
#         response = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(201, response.status_code)
#         response = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(409, response.status_code)
#         self.assertEqual("Duplicate exchange object", response.data.decode("utf-8"))
#
#     def test_insert_fail_415(self):
#         data = {
#             "OBJ_TYPE": "other"
#         }
#         response = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(415, response.status_code)
#         self.assertEqual("Invalid object type 'other'", response.data.decode("utf-8"))
#
#     def test_query_object_one(self):
#         obj: model.Exchange = model.Exchange(name="TestExchange", uri="uri")
#         data = obj.to_dict()
#         self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(data))
#
#         # Query object
#         data = {
#             "OBJ_TYPE": "exchange",
#             "attribute": "name",
#             "value": "TestExchange",
#             "multi_result": False
#         }
#         response = self.test_client.get("/query_object", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(response.status_code, 200)
#         ac = model.Exchange.from_dict(json.loads(response.data))
#         obj.id = ac.id
#         self.assertEqual(obj, ac)
#
#     def test_query_object_multiple(self):
#         first: model.Exchange = model.Exchange(name="First", uri="uri1", description="SameDescription")
#         second: model.Exchange = model.Exchange(name="Second", uri="uri2", description="SameDescription")
#         f_data = first.to_dict()
#         s_data = second.to_dict()
#         result = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(f_data))
#         self.assertEqual(201, result.status_code)
#         result = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(s_data))
#         self.assertEqual(201, result.status_code)
#
#         data = {
#             "OBJ_TYPE": "exchange",
#             "attribute": "description",
#             "value": "SameDescription",
#             "multi_result": True
#         }
#         response = self.test_client.get("/query_object", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(200, response.status_code)
#         first.id = 1
#         second.id = 2
#         ac_f_data, ac_s_data = json.loads(response.data)
#         ac_f = model.Exchange.from_dict(ac_f_data)
#         ac_s = model.Exchange.from_dict(ac_s_data)
#         self.assertEqual(ac_f, first)
#         self.assertEqual(ac_s, second)
#         # Check that an empty list is returned, if the query has no result, but multi_result is True
#         data = {
#             "OBJ_TYPE": "exchange",
#             "attribute": "name",
#             "value": "SomethingRandom",
#             "multi_result": True
#         }
#         response = self.test_client.get("/query_object", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(200, response.status_code)
#         self.assertEqual([], json.loads(response.data))
#
#     def test_query_fail_400(self):
#         data = {
#             "attribute": "description",
#             "value": "SameDescription"
#         }
#         response = self.test_client.get("/query_object", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(400, response.status_code)
#         self.assertEqual("Missing object type", response.data.decode("utf-8"))
#         data = {
#             "OBJ_TYPE": "exchange",
#             "value": "something"
#         }
#         response = self.test_client.get("/query_object", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(400, response.status_code)
#         self.assertEqual("Missing attribute name", response.data.decode("utf-8"))
#         data = {
#             "OBJ_TYPE": "exchange",
#             "attribute": "description"
#         }
#         response = self.test_client.get("/query_object", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(400, response.status_code)
#         self.assertEqual("Missing attribute value", response.data.decode("utf-8"))
#
#     def test_query_object_fail_404(self):
#         data = {
#             "OBJ_TYPE": "exchange",
#             "attribute": "name",
#             "value": "TestExchange",
#             "multi_result": False
#         }
#         response = self.test_client.get("/query_object", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(404, response.status_code)
#         self.assertEqual("Cannot find 'exchange' where 'name' is 'TestExchange'", response.data.decode("utf-8"))
#
#     def test_query_object_fail_412(self):
#         first: model.Exchange = model.Exchange(name="First", uri="uri1", description="SameDescription")
#         second: model.Exchange = model.Exchange(name="Second", uri="uri2", description="SameDescription")
#         f_data = first.to_dict()
#         s_data = second.to_dict()
#         result = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(f_data))
#         self.assertEqual(201, result.status_code)
#         result = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(s_data))
#         self.assertEqual(201, result.status_code)
#
#         data = {
#             "OBJ_TYPE": "exchange",
#             "attribute": "description",
#             "value": "SameDescription",
#             "multi_result": False
#         }
#         response = self.test_client.get("/query_object", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(412, response.status_code)
#         self.assertEqual("More than one result found", response.data.decode("utf-8"))
#
#     def test_query_object_fail_415(self):
#         data = {
#             "OBJ_TYPE": "somerandomclass",
#             "attribute": "name",
#             "value": "TestExchange",
#             "multi_result": False
#         }
#         response = self.test_client.get("/query_object", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(415, response.status_code)
#         self.assertEqual("Invalid Object type 'somerandomclass'", response.data.decode("utf-8"))
#
#     def test_get_all_success(self):
#         first: model.Exchange = model.Exchange(name="First", uri="uri1", description="SameDescription")
#         second: model.Exchange = model.Exchange(name="Second", uri="uri2", description="SameDescription")
#         f_data = first.to_dict()
#         s_data = second.to_dict()
#         result = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(f_data))
#         self.assertEqual(201, result.status_code)
#         result = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(s_data))
#         self.assertEqual(201, result.status_code)
#
#         data = {"OBJ_TYPE": "exchange"}
#         response = self.test_client.get("/get_all", headers=self.auth_headers, data=json.dumps(data))
#         self.assertEqual(200, response.status_code)
#         f_data["id"] = 1
#         s_data["id"] = 2
#         self.assertEqual([f_data, s_data], json.loads(response.data))
#
#     def test_get_all_fail_400(self):
#         response = self.test_client.get("/get_all", headers=self.auth_headers, data=json.dumps({}))
#         self.assertEqual(400, response.status_code)
#         self.assertEqual("Missing object type", response.data.decode("utf-8"))
#
#     def test_get_all_fail_415(self):
#         response = self.test_client.get("/get_all", headers=self.auth_headers, data=json.dumps({"OBJ_TYPE": "no"}))
#         self.assertEqual(415, response.status_code)
#         self.assertEqual("Invalid object type 'no'", response.data.decode("utf-8"))
#
#     def test_delete_success(self):
#         first: model.Exchange = model.Exchange(name="First", uri="uri1", description="SameDescription")
#         result = self.test_client.post("/insert", headers=self.auth_headers, data=json.dumps(first.to_dict()))
#         self.assertEqual(201, result.status_code)
#
#         first.id = 1
#         response = self.test_client.delete("/delete", headers=self.auth_headers, data=json.dumps(first.to_dict()))
#         self.assertEqual(200, response.status_code)
#         self.assertEqual("Successfully deleted exchange with ID 1", response.data.decode("utf-8"))
#
#     def test_delete_fail_400(self):
#         response = self.test_client.delete("/delete", headers=self.auth_headers, data=json.dumps({}))
#         self.assertEqual(400, response.status_code)
#         self.assertEqual("Missing object type", response.data.decode("utf-8"))
#
#     def test_delete_fail_415(self):
#         response = self.test_client.delete("/delete", headers=self.auth_headers, data=json.dumps({"OBJ_TYPE": "a"}))
#         self.assertEqual(415, response.status_code)
#         self.assertEqual("Invalid object type 'a'", response.data.decode("utf-8"))
