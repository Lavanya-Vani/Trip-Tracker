import unittest
from app import app
from unittest.mock import patch, MagicMock
import bcrypt

class TestIntegration(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('app.get_db_connection')
    def test_user_registration_flow(self, mock_db):
        """Test complete user registration flow"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Test registration
        response = self.client.post('/signup', data={
            'username': 'newuser',
            'password': 'newpass123'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)

    @patch('app.get_db_connection')
    def test_user_login_flow(self, mock_db):
        """Test complete user login flow"""
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Test login
        test_password = 'testpass123'
        hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt())
        mock_cursor.fetchone.return_value = (1, 'testuser', hashed.decode('utf-8'))
        
        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': test_password
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertIn('user_id', sess)

    def test_protected_routes_access(self):
        """Test access to protected routes"""
        # Test unauthenticated access
        response = self.client.get('/profile', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
        
        # Test authenticated access
        with self.client as client:
            with client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['username'] = 'testuser'
            
            response = client.get('/profile')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Profile', response.data)

if __name__ == '__main__':
    unittest.main() 