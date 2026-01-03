import requests
import requests
from requests.auth import HTTPDigestAuth
import json
from Index.models import ConfigarationDB

call_back_url = ConfigarationDB.objects.first().Call_Back_IP


def hik_connection_test(device_ip, username, password, timeout=8):
    """
    Try to call the device endpoint and return the requests.Response on success,
    or None on failure.
    device_ip may include a port, e.g. "127.0.0.1:8000"
    """
    # Ensure the URL has scheme
    if not device_ip.startswith("http://") and not device_ip.startswith("https://"):
        url = f"http://{call_back_url}/call_connection/{device_ip}/{username}/{password}/"
    else:
        # user passed full URL already
        url = f"{call_back_url}/call_connection/{device_ip}/{username}/{password}/"

    try:
        print(f"[hik_connection_test] calling {url}")
        response = requests.get(url, timeout=timeout)
        # Optionally: response.raise_for_status()  # if you want to treat non-2xx as exception
        return response
    except requests.RequestException as ex:
        # log or print the error for debugging
        print(f"[hik_connection_test] request failed: {ex}")
        return None




def get_all_persons_from_device(call_back, device_ip, username, password, timeout=120):
    """
    Calls your Django server to get ALL persons from a Hikvision Face Terminal
    Example: call_back = "http://192.168.1.100:8000/api/get-all-persons/"
    
    Returns:
        list of persons (Python dicts) on success
        None on any error
    """
    # Build the full URL with query parameters
    if not call_back.endswith('/'):
        call_back += '/'
    
    url = f"http://{call_back}/api/get-all-persons/?ip={device_ip}&user={username}&pass={password}"

    print(f"[Device Sync] Calling Django API → {url}")

    try:
        response = requests.get(url, timeout=timeout)

        if response.status_code != 200:
            print(f"[ERROR] Django returned {response.status_code}")
            print(response.text[:300])
            return None

        data = response.json()

        # Check if our Django view returned success
        if data.get("status") != "success":
            print(f"[ERROR] API failed: {data.get('message', 'Unknown error')}")
            return None

        persons = data.get("persons", [])
        total = len(persons)

        print(f"[SUCCESS] Retrieved {total} persons from device {device_ip}")
        
        return persons  # ← This is the clean list you want

    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] Request to Django server timed out after {timeout}s")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[CONNECTION ERROR] Cannot reach Django server at {call_back}")
        return None
    except json.JSONDecodeError:
        print("[ERROR] Invalid JSON received from Django server")
        return None
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {e}")
        return None




def get_single_person_from_device(
    call_back,
    device_ip,
    username,
    password,
    employee_no,
    timeout=120
):
    """
    Fetch a SINGLE person from Hikvision device by employeeNo via Django API
    Returns: dict of person data or None
    """
    if not employee_no:
        print("[ERROR] employee_no is required")
        return None

    if not call_back.endswith('/'):
        call_back += '/'
    
    url = f"http://{call_back}get_person_by_employee_no/"
    # url = f"{call_back.rstrip('/')}/api/get_person_by_employee_no/"

    payload = {
        "device_ip": device_ip,
        "username": username,
        "password": password,
        "employee_no": str(employee_no)
    }

    print(f"[GET PERSON] Fetching employee {employee_no} from {device_ip} via {url}")

    try:
        response = requests.post(url, json=payload, timeout=timeout)

        if response.status_code != 200:
            print(f"[ERROR] Django returned {response.status_code}: {response.text[:300]}")
            return None

        data = response.json()

        if data.get("status") != "success":
            print(f"[NOT FOUND] {data.get('message', 'User not found')}")
            return None

        person = data.get("person")
        if not person:
            print("[ERROR] No 'person' field in response")
            return None

        print(f"[SUCCESS] Found user: {person.get('name')} ({employee_no})")
        return person

    except Exception as e:
        print(f"[EXCEPTION] {type(e).__name__}: {e}")
        return None
    



def add_person_to_hik_device(call_back, device_ip, username, password, person_data, timeout=120):
    if not call_back.endswith('/'):
        call_back += '/'
    
    url = f"http://{call_back}add_person_record/"
    
    # Prepare the payload as JSON
    payload = {
        "device_ip": device_ip,
        "username": username,
        "password": password,
        "person_data": person_data  # This should be a dict or list
    }
    
    print(f"Calling App person to device API → {url}")
    print(f"Payload: {payload}")
    
    try:
        # Use POST instead of GET
        response = requests.post(url, json=payload, timeout=timeout)
        
        if response.status_code != 200:
            print(f"[ERROR] Django returned {response.status_code}")
            print(response.text[:300])
            return None
            
        data = response.json()
        
        # Check if our Django view returned success
        if data.get("status") != "success":
            print(f"[ERROR] API failed: {data.get('message', 'Unknown error')}")
            return None
            
        persons = data.get("persons", [])
        total = len(persons)
        print(f"[SUCCESS] Added {total} persons to device {device_ip}")
        
        return persons
        
    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] Request to Django server timed out after {timeout}s")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[CONNECTION ERROR] Cannot reach Django server at {call_back}")
        return None
    except json.JSONDecodeError:
        print("[ERROR] Invalid JSON received from Django server")
        print(f"Response text: {response.text[:500]}")
        return None
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {type(e).__name__}: {e}")
        return None
    


def delete_user_from_device(call_back, device_ip, username, password, employee_no, timeout=120):
    if not call_back.endswith('/'):
        call_back += '/'
    
    url = f"http://{call_back}delete_user_from_device/"
    
    # Prepare the payload as JSON
    payload = {
        "device_ip": device_ip,
        "username": username,
        "password": password,
        "employee_no": employee_no  # This should be a dict or list
    }
    
    print(f"Calling Delete person to device API → {url}")
    print(f"Payload: {payload}")
    
    try:
        # Use POST instead of GET
        response = requests.post(url, json=payload, timeout=timeout)
        
        if response.status_code != 200:
            print(f"[ERROR] Django returned {response.status_code}")
            print(response.text[:300])
            return None
            
        data = response.json()
        
        # Check if our Django view returned success
        if data.get("status") != "success":
            print(f"[ERROR] API failed: {data.get('message', 'Unknown error')}")
            return None
            
        persons = data.get("persons", [])
        total = len(persons)
        print(f"[SUCCESS] Deleted {total} persons From device {device_ip}")
        
        return persons
        
    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] Request to Django server timed out after {timeout}s")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[CONNECTION ERROR] Cannot reach Django server at {call_back}")
        return None
    except json.JSONDecodeError:
        print("[ERROR] Invalid JSON received from Django server")
        print(f"Response text: {response.text[:500]}")
        return None
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {type(e).__name__}: {e}")
        return None


def disable_enable_person_form_hik(call_back, device_ip, username, password, person_data, timeout=120):
    if not call_back.endswith('/'):
        call_back += '/'
    
    url = f"http://{call_back}disable_enable_user_setup/"
    
    # Prepare the payload as JSON
    payload = {
        "device_ip": device_ip,
        "username": username,
        "password": password,
        "person_data": person_data  # This should be a dict or list
    }
    
    print(f"Calling App person to device API → {url}")
    print(f"Payload: {payload}")
    
    try:
        # Use POST instead of GET
        response = requests.post(url, json=payload, timeout=timeout)
        
        if response.status_code != 200:
            print(f"[ERROR] Django returned {response.status_code}")
            print(response.text[:300])
            return None
            
        data = response.json()
        
        # Check if our Django view returned success
        if data.get("status") != "success":
            print(f"[ERROR] API failed: {data.get('message', 'Unknown error')}")
            return None
            
        persons = data.get("persons", [])
        total = len(persons)
        print(f"[SUCCESS] Added {total} persons to device {device_ip}")
        
        return persons
        
    except requests.exceptions.Timeout:
        print(f"[TIMEOUT] Request to Django server timed out after {timeout}s")
        return None
    except requests.exceptions.ConnectionError:
        print(f"[CONNECTION ERROR] Cannot reach Django server at {call_back}")
        return None
    except json.JSONDecodeError:
        print("[ERROR] Invalid JSON received from Django server")
        print(f"Response text: {response.text[:500]}")
        return None
    except Exception as e:
        print(f"[UNEXPECTED ERROR] {type(e).__name__}: {e}")
        return None
