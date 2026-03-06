import requests
import time
import json
import hashlib
from datetime import datetime, timedelta

class TTLockManager:
    def __init__(self, client_id, client_secret, username, password):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = hashlib.md5(password.encode('utf-8')).hexdigest().lower()
        self.base_url = "https://euapi.ttlock.com"
        self.access_token = None

    def get_access_token(self):
        """Get access token from TTLock OAuth API."""
        url = f"{self.base_url}/oauth2/token"
        
        data = {
            "clientId": self.client_id,
            "clientSecret": self.client_secret,
            "username": self.username,
            "password": self.password,
            "grant_type": "password"
        }
        
        try:
            response = requests.post(url, data=data)  # Let requests handle form encoding
            response.raise_for_status()
            token_info = response.json()
            
            if "access_token" in token_info:
                self.access_token = token_info["access_token"]
                return token_info
            else:
                raise Exception(f"Failed to get access token: {token_info}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get access token: {str(e)}")
            
    def get_lock_status(self, lock_id):
        """Get the current state of a lock (locked/unlocked)"""
        url = f"{self.base_url}/v3/lock/queryOpenState"
        params = {
            "clientId": self.client_id,
            "accessToken": self.access_token,
            "lockId": lock_id,
            "date": int(time.time() * 1000)
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def create_temporary_passcode(self, lock_id, name, start_time=None, end_time=None, custom_passcode=None):
        """Create a temporary passcode for a lock."""
        # Get access token if not already set
        if not self.access_token:
            token_info = self.get_access_token()
            if not token_info.get('access_token'):
                return None

        # Get current timestamp in milliseconds
        current_timestamp = int(time.time() * 1000)

        # Convert times to timestamps
        start_timestamp = int(start_time.timestamp() * 1000) if start_time else current_timestamp
        end_timestamp = int(end_time.timestamp() * 1000) if end_time else (current_timestamp + 31536000000)  # 1 year default

        # Generate a passcode if not provided (6 digits)
        if not custom_passcode:
            custom_passcode = str(int(time.time() * 1000))[-6:]

        # Prepare data exactly as in working example
        data = {
            "clientId": self.client_id,
            "accessToken": self.access_token,
            "lockId": lock_id,
            "keyboardPwd": custom_passcode,
            "keyboardPwdName": name,
            "keyboardPwdType": 3,
            "startDate": start_timestamp,
            "endDate": end_timestamp,
            "addType": 2,
            "date": current_timestamp
        }

        # Make API request
        url = f'{self.base_url}/v3/keyboardPwd/add'
        
        try:
            response = requests.post(url, data=data)  # Let requests handle form encoding
            
            if response.status_code == 200:
                result = response.json()
                if "keyboardPwdId" in result:
                    return {
                        "keyboardPwd": custom_passcode,
                        "keyboardPwdId": result["keyboardPwdId"],
                        "startDate": start_timestamp,
                        "endDate": end_timestamp
                    }
                else:
                    raise Exception(f"Failed to create passcode: {result}")
            else:
                raise Exception(f"HTTP Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"HTTP Error: {str(e)}")
        except ValueError as e:
            raise Exception(f"Invalid response format: {str(e)}")

    def delete_passcode(self, lock_id, keyboard_pwd_id):
        """Delete a passcode from TTLock system"""
        url = f"{self.base_url}/v3/keyboardPwd/delete"
        current_time = int(time.time() * 1000)
        
        payload = {
            "clientId": self.client_id,
            "accessToken": self.access_token,
            "lockId": lock_id,
            "keyboardPwdId": keyboard_pwd_id,
            "date": current_time
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        try:
            response = requests.post(url, data=payload, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get("errcode") == 0:
                print("Successfully deleted passcode", keyboard_pwd_id)
                return result
            else:
                print("Failed to delete passcode:", result.get('errmsg'))
                return None
                
        except Exception as e:
            print("Error deleting passcode:", str(e))
            return None

    def get_unlock_records(self, lock_id, start_date=None, end_date=None, page_no=1, page_size=20):
        """Get unlock records for a specific lock"""
        url = f"{self.base_url}/v3/lockRecord/list"
        params = {
            "clientId": self.client_id,
            "accessToken": self.access_token,
            "lockId": lock_id,
            "pageNo": page_no,
            "pageSize": page_size,
            "date": int(time.time() * 1000)
        }
        if start_date:
            params["startDate"] = int(start_date.timestamp() * 1000)
        if end_date:
            params["endDate"] = int(end_date.timestamp() * 1000)
            
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def remote_unlock(self, lock_id):
        """Remotely unlock a lock"""
        url = f"{self.base_url}/v3/lock/unlock"
        params = {
            "clientId": self.client_id,
            "accessToken": self.access_token,
            "lockId": lock_id,
            "date": int(time.time() * 1000)
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_lock_details(self, lock_id):
        """Get detailed information about a specific lock"""
        url = f"{self.base_url}/v3/lock/detail"
        params = {
            "clientId": self.client_id,
            "accessToken": self.access_token,
            "lockId": lock_id,
            "date": int(time.time() * 1000)
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def get_lock_users(self, lock_id, page_no=1, page_size=20):
        """Get list of users who have access to the lock"""
        url = f"{self.base_url}/v3/lock/listUser"
        params = {
            "clientId": self.client_id,
            "accessToken": self.access_token,
            "lockId": lock_id,
            "pageNo": page_no,
            "pageSize": page_size,
            "date": int(time.time() * 1000)
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def list_passcodes(self, lock_id, page_no=1, page_size=20):
        """List all passcodes for a lock"""
        url = f"{self.base_url}/v3/lock/listKeyboardPwd"  # Updated endpoint
        params = {
            "clientId": self.client_id,
            "accessToken": self.access_token,
            "lockId": lock_id,
            "pageNo": page_no,
            "pageSize": page_size,
            "date": int(time.time() * 1000)
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def list_locks(self, page_no=1, page_size=20):
        """Get list of all locks"""
        if not self.access_token:
            token_info = self.get_access_token()
            if not token_info.get('access_token'):
                return None

        url = f"{self.base_url}/v3/lock/list"
        params = {
            "clientId": self.client_id,
            "accessToken": self.access_token,
            "pageNo": page_no,
            "pageSize": page_size,
            "date": int(time.time() * 1000)
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()

# Example usage
if __name__ == "__main__":
    # Initialize the manager with actual credentials
    manager = TTLockManager(
        client_id="a67f3b3552a64b0c81aa5e3b2a19dffb",
        client_secret="8db22fad0b66cc784b06cbddc1ccab9a",
        username="a7mdoh@hotmail.com",
        password="Aa@112233123"
    )

    try:
        # Step 1: Get access token
        print("\n1. Getting access token...")
        token_info = manager.get_access_token()
        print(f"* Access Token obtained: {token_info.get('access_token')}")

        # Step 2: List all locks
        print("\n2. Fetching all locks...")
        locks = manager.list_locks()
        
        if not locks.get("list"):
            print("No locks found!")
            exit()

        print(f"Found {len(locks['list'])} locks:")
        for lock in locks["list"]:
            print(f"\n* Lock: {lock.get('lockName')}")
            print(f"  - ID: {lock.get('lockId')}")
            print(f"  - MAC: {lock.get('lockMac')}")
            print(f"  - Battery: {lock.get('electricQuantity')}%")

        # Step 3: Select first lock
        first_lock = locks["list"][0]
        lock_id = first_lock["lockId"]
        print(f"\n3. Selected lock '{first_lock['lockName']}' (ID: {lock_id})")

        # Step 4: Get all passcodes for the selected lock
        print("\n4. Fetching passcodes for selected lock...")
        passcodes = manager.list_passcodes(lock_id)
        
        if passcodes.get("list"):
            print(f"\nFound {len(passcodes['list'])} passcodes:")
            for code in passcodes["list"]:
                start = datetime.fromtimestamp(code.get('startDate', 0)/1000)
                end = datetime.fromtimestamp(code.get('endDate', 0)/1000)
                
                # Check if it's a permanent passcode (dates from 1970 or very old dates)
                is_permanent = start.year < 2000 or end.year < 2000
                
                print(f"\n* Passcode: {code.get('keyboardPwd')}")
                print(f"  - Name: {code.get('keyboardPwdName')}")
                
                if is_permanent:
                    print("  - Type: Permanent Passcode")
                else:
                    duration = end - start
                    days = duration.days
                    hours = duration.seconds // 3600
                    minutes = (duration.seconds % 3600) // 60
                    
                    print(f"  - Start: {start.strftime('%Y-%m-%d %H:%M')}")
                    print(f"  - End: {end.strftime('%Y-%m-%d %H:%M')}")
                    print(f"  - Duration: {days} days, {hours} hours, {minutes} minutes")
                    print(f"  - Type: {'Temporary' if code.get('keyboardPwdType') == 2 else 'Custom'} (Type {code.get('keyboardPwdType', 'Unknown')})")
                
                print(f"  - Status: {'Active' if code.get('status') == 1 else 'Inactive'}")
        else:
            print("No passcodes found for this lock")

    except requests.exceptions.RequestException as e:
        print(f"\nError occurred: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print("Error details:", json.dumps(error_details, indent=2))
            except:
                print("Error response:", e.response.text)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
