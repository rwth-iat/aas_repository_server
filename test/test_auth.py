import unittest


from aas_repository_server import auth


class UserTest(unittest.TestCase):
    def test_add_user(self):
        auth.add_user("test", "test")
        self.assertNotEqual(None, auth.USERS.get("test"))
        self.assertNotEqual("test", auth.USERS.get("test"))
        auth.USERS.pop("test")

    def test_remove_user(self):
        auth.add_user("test", "test")
        auth.remove_user("test")
        self.assertEqual(None, auth.USERS.get("test"))

    def test_get_password_hash(self):
        auth.add_user("test", "test")
        self.assertNotEqual(None, auth.get_password_hash("test"))
        self.assertNotEqual("test", auth.get_password_hash("test"))
        auth.USERS.pop("test")

    def test_check_if_user_exists(self):
        auth.add_user("test", "test")
        self.assertEqual(True, auth.check_if_user_exists("test"))
        self.assertEqual(False, auth.check_if_user_exists("anotherTest"))
        auth.remove_user("test")
