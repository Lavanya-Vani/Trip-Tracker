import unittest
from app import app

class TestTemplates(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_home_template(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Travel Buddy', response.data)

    def test_login_template(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
        self.assertIn(b'username', response.data)
        self.assertIn(b'password', response.data)

    def test_signup_template(self):
        response = self.client.get('/signup')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Sign Up', response.data)
        self.assertIn(b'username', response.data)
        self.assertIn(b'password', response.data)

    def test_profile_template(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'testuser'
            response = client.get('/profile')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Profile', response.data)

if __name__ == '__main__':
    unittest.main() 