import requests
import unittest
import json
import time

BASE_URL = "http://localhost:5050"

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        # Wait for server to be ready
        for i in range(5):
            try:
                requests.get(f"{BASE_URL}/health")
                break
            except:
                time.sleep(1)

    def test_health(self):
        resp = requests.get(f"{BASE_URL}/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "healthy", "service": "retirement-planner-api"})

    def test_run_simulation(self):
        with open("test_payload.json", "r") as f:
            payload = json.load(f)
        
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(f"{BASE_URL}/api/run-simulation", json=payload, headers=headers)
        
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        self.assertTrue(data['success'])
        self.assertIn('scenarios', data)
        self.assertIn('standard', data['scenarios'])
        self.assertIn('taxable_first', data['scenarios'])
        
        # Check integrity of results
        std_results = data['scenarios']['standard']['results']
        self.assertGreater(len(std_results), 10)
        self.assertIn('Net_Worth', std_results[0])
        
    def test_run_monte_carlo(self):
        with open("test_payload.json", "r") as f:
            payload = json.load(f)
            
        # Add MC params
        payload['volatility'] = 0.15
        payload['num_simulations'] = 50 
        
        headers = {'Content-Type': 'application/json'}
        resp = requests.post(f"{BASE_URL}/api/run-monte-carlo", json=payload, headers=headers)
        
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        
        self.assertTrue(data['success'])
        self.assertIn('success_rate', data)
        self.assertEqual(data['num_simulations'], 50)
        self.assertIn('stats', data)
        self.assertIn('all_runs', data)

    def test_csv_upload(self):
        # Verify CSV upload parity support
        with open("nisha.csv", "rb") as f:
            files = {'file': ('nisha.csv', f, 'text/csv')}
            resp = requests.post(f"{BASE_URL}/api/run-simulation", files=files)
            
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertIn('scenarios', data)

if __name__ == '__main__':
    unittest.main()
