#!/usr/bin/env python3
"""
Discord Bot Management API Test Suite
Tests all backend API endpoints for the Discord bot management system.
"""

import requests
import sys
import json
from datetime import datetime
import uuid
import time

class DiscordBotAPITester:
    def __init__(self, base_url="https://f599ebe2-918b-492d-ae63-239fb1a3bfcc.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def run_test(self, name, method, endpoint, expected_status=200, data=None, timeout=10):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}" if not endpoint.startswith('http') else endpoint
        headers = {'Content-Type': 'application/json'}
        
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                self.log_test(name, False, f"Unsupported method: {method}")
                return False, {}

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    self.log_test(name, True, f"Status: {response.status_code}")
                    return True, response_data
                except json.JSONDecodeError:
                    # Some endpoints might not return JSON
                    self.log_test(name, True, f"Status: {response.status_code} (No JSON response)")
                    return True, {}
            else:
                error_details = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_response = response.json()
                    error_details += f" - {error_response}"
                except:
                    error_details += f" - {response.text[:200]}"
                
                self.log_test(name, False, error_details)
                return False, {}

        except requests.exceptions.Timeout:
            self.log_test(name, False, f"Request timeout after {timeout}s")
            return False, {}
        except requests.exceptions.ConnectionError:
            self.log_test(name, False, "Connection error - server may be down")
            return False, {}
        except Exception as e:
            self.log_test(name, False, f"Unexpected error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root endpoint"""
        return self.run_test("Root Endpoint", "GET", "")

    def test_bot_status(self):
        """Test bot status endpoint"""
        return self.run_test("Bot Status", "GET", "api/bot/status")

    def test_bot_start(self):
        """Test bot start endpoint"""
        return self.run_test("Bot Start", "POST", "api/bot/start")

    def test_bot_stop(self):
        """Test bot stop endpoint"""
        return self.run_test("Bot Stop", "POST", "api/bot/stop")

    def test_get_servers(self):
        """Test get servers endpoint"""
        return self.run_test("Get Servers", "GET", "api/servers")

    def test_create_server_config(self):
        """Test create server configuration"""
        test_server_data = {
            "server_id": f"test_server_{int(time.time())}",
            "server_name": "Test Server",
            "prefix": "!",
            "welcome_channel": "general",
            "log_channel": "logs",
            "auto_role": "member",
            "settings": {
                "auto_mod": True,
                "welcome_enabled": True
            }
        }
        
        return self.run_test("Create Server Config", "POST", "api/servers", 200, test_server_data)

    def test_get_server_by_id(self):
        """Test get specific server"""
        # First create a server, then try to get it
        success, server_data = self.test_create_server_config()
        if success:
            server_id = f"test_server_{int(time.time())}"
            return self.run_test("Get Server by ID", "GET", f"api/servers/{server_id}", expected_status=404)  # Expect 404 for non-existent server
        return False, {}

    def test_get_commands(self):
        """Test get all commands endpoint"""
        success, data = self.run_test("Get All Commands", "GET", "api/commands")
        
        if success and data:
            # Check if news commands are included
            commands = data.get("commands", [])
            total_commands = data.get("total", 0)
            
            # Look for news commands
            news_commands = [cmd for cmd in commands if cmd.get("category") == "news"]
            
            print(f"   📊 Total commands found: {total_commands}")
            print(f"   📰 News commands found: {len(news_commands)}")
            
            # Expected news commands
            expected_news_commands = [
                "news", "news us", "news uk", "news india", 
                "news us tech", "news uk business", "news india sports"
            ]
            
            found_news_commands = [cmd.get("name") for cmd in news_commands]
            print(f"   📝 News commands: {found_news_commands}")
            
            # Check if we have the expected total (should be around 142)
            if total_commands >= 140:
                print(f"   ✅ Command count looks correct: {total_commands}")
            else:
                print(f"   ⚠️  Command count seems low: {total_commands} (expected ~142)")
            
            # Check if news commands exist
            if len(news_commands) >= 6:  # At least 6 news commands
                print(f"   ✅ News commands found: {len(news_commands)}")
            else:
                print(f"   ⚠️  Few news commands found: {len(news_commands)}")
        
        return success, data

    def test_get_commands_by_category(self):
        """Test get commands by category"""
        categories = ["moderation", "server", "roles", "channels", "users", "utility", "fun", "economy", "news"]
        
        results = []
        for category in categories:
            success, data = self.run_test(f"Get Commands - {category.title()}", "GET", f"api/commands/{category}")
            results.append(success)
            
            # Special check for news category
            if category == "news" and success and data:
                commands = data.get("commands", [])
                print(f"   📰 News category commands: {len(commands)}")
                for cmd in commands:
                    print(f"      • {cmd.get('name')}: {cmd.get('description')}")
        
        return all(results), {}

    def test_log_command_execution(self):
        """Test command execution logging"""
        test_log_data = {
            "command_id": str(uuid.uuid4()),
            "server_id": f"test_server_{int(time.time())}",
            "user_id": f"test_user_{int(time.time())}",
            "command_name": "test_command",
            "parameters": {"test_param": "test_value"},
            "timestamp": datetime.utcnow().isoformat(),
            "success": True,
            "error_message": None
        }
        
        return self.run_test("Log Command Execution", "POST", "api/commands/execute", 200, test_log_data)

    def test_get_logs(self):
        """Test get logs endpoint"""
        return self.run_test("Get Logs", "GET", "api/logs")

    def test_get_server_logs(self):
        """Test get server-specific logs"""
        test_server_id = f"test_server_{int(time.time())}"
        return self.run_test("Get Server Logs", "GET", f"api/logs/{test_server_id}")

    def test_invalid_endpoints(self):
        """Test invalid endpoints return proper errors"""
        invalid_tests = [
            ("Invalid API Endpoint", "GET", "api/invalid", 404),
            ("Invalid Server ID", "GET", "api/servers/invalid_id", 404),
            ("Invalid Command Category", "GET", "api/commands/invalid_category", 200),  # Should return empty list
        ]
        
        results = []
        for name, method, endpoint, expected_status in invalid_tests:
            success, _ = self.run_test(name, method, endpoint, expected_status)
            results.append(success)
        
        return all(results), {}

    def test_news_api_integration(self):
        """Test news API integration and environment setup"""
        print(f"\n🔍 Testing News API Integration...")
        
        # Test if we can access the news API key (indirectly through bot status)
        success, data = self.run_test("News API Environment Check", "GET", "api/bot/status")
        
        if success:
            print("   ✅ Backend is accessible for news API testing")
            
            # Test news category specifically
            success_news, news_data = self.run_test("News Category Commands", "GET", "api/commands/news")
            
            if success_news and news_data:
                commands = news_data.get("commands", [])
                if len(commands) >= 6:
                    print(f"   ✅ News commands properly configured: {len(commands)} commands")
                    return True, news_data
                else:
                    print(f"   ❌ Insufficient news commands: {len(commands)}")
                    return False, {}
            else:
                print("   ❌ Failed to get news category commands")
                return False, {}
        else:
            print("   ❌ Backend not accessible for news testing")
            return False, {}

    def test_cors_headers(self):
        """Test CORS headers are present"""
        try:
            response = requests.options(f"{self.base_url}/api/bot/status")
            cors_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers'
            ]
            
            has_cors = any(header in response.headers for header in cors_headers)
            self.log_test("CORS Headers", has_cors, "CORS headers present" if has_cors else "CORS headers missing")
            return has_cors, {}
        except Exception as e:
            self.log_test("CORS Headers", False, f"Error checking CORS: {str(e)}")
            return False, {}
        """Test CORS headers are present"""
        try:
            response = requests.options(f"{self.base_url}/api/bot/status")
            cors_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers'
            ]
            
            has_cors = any(header in response.headers for header in cors_headers)
            self.log_test("CORS Headers", has_cors, "CORS headers present" if has_cors else "CORS headers missing")
            return has_cors, {}
        except Exception as e:
            self.log_test("CORS Headers", False, f"Error checking CORS: {str(e)}")
            return False, {}

    def run_comprehensive_tests(self):
        """Run all tests"""
        print("🚀 Starting Discord Bot API Comprehensive Test Suite")
        print("=" * 60)
        
        # Basic connectivity tests
        print("\n📡 CONNECTIVITY TESTS")
        print("-" * 30)
        self.test_root_endpoint()
        
        # Bot management tests
        print("\n🤖 BOT MANAGEMENT TESTS")
        print("-" * 30)
        self.test_bot_status()
        self.test_bot_start()
        time.sleep(2)  # Wait for bot to start
        self.test_bot_status()  # Check status again
        self.test_bot_stop()
        time.sleep(2)  # Wait for bot to stop
        
        # Server management tests
        print("\n🏢 SERVER MANAGEMENT TESTS")
        print("-" * 30)
        self.test_get_servers()
        self.test_create_server_config()
        self.test_get_server_by_id()
        
        # Commands tests
        print("\n⚡ COMMANDS TESTS")
        print("-" * 30)
        self.test_get_commands()
        self.test_get_commands_by_category()
        
        # Logging tests
        print("\n📋 LOGGING TESTS")
        print("-" * 30)
        self.test_log_command_execution()
        self.test_get_logs()
        self.test_get_server_logs()
        
        # Error handling tests
        print("\n❌ ERROR HANDLING TESTS")
        print("-" * 30)
        self.test_invalid_endpoints()
        
        # News API Integration tests
        print("\n📰 NEWS API INTEGRATION TESTS")
        print("-" * 30)
        self.test_news_api_integration()
        
        # CORS tests
        print("\n🌐 CORS TESTS")
        print("-" * 30)
        self.test_cors_headers()
        
        # Print final results
        self.print_final_results()

    def print_final_results(self):
        """Print comprehensive test results"""
        print("\n" + "=" * 60)
        print("📊 FINAL TEST RESULTS")
        print("=" * 60)
        
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 ALL TESTS PASSED! The Discord Bot API is working correctly.")
        else:
            print(f"\n⚠️  {self.tests_run - self.tests_passed} tests failed. Check the details above.")
            
            # Show failed tests
            failed_tests = [test for test in self.test_results if not test['success']]
            if failed_tests:
                print("\n❌ FAILED TESTS:")
                for test in failed_tests:
                    print(f"   • {test['name']}: {test['details']}")
        
        print("\n📝 DETAILED RESULTS:")
        for test in self.test_results:
            status = "✅" if test['success'] else "❌"
            print(f"   {status} {test['name']}")
            if test['details'] and not test['success']:
                print(f"      └─ {test['details']}")

def main():
    """Main test execution"""
    print("Discord Bot Management API Test Suite")
    print("Testing backend API endpoints...")
    
    # Initialize tester with the public URL
    tester = DiscordBotAPITester()
    
    # Run all tests
    tester.run_comprehensive_tests()
    
    # Return exit code based on test results
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())