from django.shortcuts import render, redirect
from .forms import MemberAddForm, SubscriptionAddForm, PaymentForm
from .models import MemberData, Subscription, Payment, AccessToGate, Discounts
from django.contrib import messages
from datetime import datetime, timedelta
from django.utils import timezone
from django.http import HttpResponse
import csv
from django.template.loader import get_template
from xhtml2pdf import pisa
from Index.models import ConfigarationDB
# import requests
import requests
import json
from django.contrib.auth.decorators import login_required
from Index.models import Logo
from Index.decorator import allowed_users



this_month = timezone.now().month
today = timezone.now()
start_date = today + timedelta(days=-5)
end_date = today + timedelta(days=5)
resign_date = today +timedelta(days = -30)

notification_payments = Payment.objects.filter(Payment_Date__gte = start_date,Payment_Date__lte = today,Payment_Date = today )


import requests
import json
from datetime import datetime

def disable_person_from_device(member_id, device_serial_number="CQUH233560091"):
    """
    Disable a person from the access control device
    """
    # url = "http://192.168.70.31:8050/api_disableperson"
    
    # headers = {
    #     'Host': 'emmyfitness-betainfotech.pythonanywhere.com',
    #     'Content-Type': 'application/json',
    #     'Content-Length': '0',  # Set to '0' for GET requests, calculate for POST/PUT requests
    #     'Accept': '*/*',
    #     'Accept-Encoding': 'gzip, deflate, br',
    #     'Connection': 'keep-alive',
    #     'Token': '7ee4e345d834feb:c3abbf46c8714cb'
    # }

    url = "https://django.byteboot.in/disable_person/"

    
    payload = {
        "BadgeNumber": str(member_id),
        "DeviceSerialNumber": device_serial_number
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"Successfully disabled member {member_id} from device {device_serial_number}")
            return True
        else:
            print(f"Failed to disable member {member_id} from device. Status code: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Error disabling member {member_id} from device: {str(e)}")
        return False

def ScheduledTask():
    end_date = datetime.now()  # Assuming end_date is current datetime, adjust as necessary
    resign_date = datetime.now()  # Assuming resign_date is current datetime, adjust as necessary

    subscrib = Subscription.objects.filter(Subscription_End_Date__lte=end_date)
    subscriptions_to_update = []
    access_to_update = []
    members_to_disable_from_device = []

    for subscription in subscrib:
        subscription.Payment_Status = False
        subscriptions_to_update.append(subscription)
        subscription.Member.update_active_status()
        
        try:
            access = AccessToGate.objects.get(Subscription=subscription)
            access.Status = False
            access_to_update.append(access)
            
            # Add member to the list for device disabling
            members_to_disable_from_device.append({
                'member_id': subscription.Member.id,
                'member_name': f"{subscription.Member.First_Name} {subscription.Member.Last_Name}"
            })
            
            print(f"Access gate found {access}")

        except AccessToGate.DoesNotExist:
            print(f"No access gate {subscription}")
            continue

    # Bulk update database records
    Subscription.objects.bulk_update(subscriptions_to_update, ['Payment_Status'])
    AccessToGate.objects.bulk_update(access_to_update, ['Status'])

    # Disable members from device
    device_disable_success_count = 0
    device_disable_fail_count = 0
    
    for member_info in members_to_disable_from_device:
        # response = requests.get('http://127.0.0.1:8000/call_connection/')
        # if response.status_code == 200:
        #     print(f"Successfully disabled member")
            
        # else:
        #     print(f"Failed to disable member ")
            
        
        success = disable_person_from_device(member_info['member_id'])
        if success:
            device_disable_success_count += 1
        else:
            device_disable_fail_count += 1

    acc = AccessToGate.objects.all()
    print("Working.....")
    print(f"Database updates completed. Device API calls - Success: {device_disable_success_count}, Failed: {device_disable_fail_count}")

# Alternative version with better error handling and logging
def ScheduledTaskAdvanced():
    """
    Advanced version with better error handling and logging
    """
    import logging
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    end_date = datetime.now()
    
    try:
        subscrib = Subscription.objects.filter(Subscription_End_Date__lte=end_date)
        subscriptions_to_update = []
        access_to_update = []
        device_operations = []

        logger.info(f"Processing {subscrib.count()} expired subscriptions")

        for subscription in subscrib:
            subscription.Payment_Status = False
            subscriptions_to_update.append(subscription)
            subscription.Member.update_active_status()
            
            try:
                access = AccessToGate.objects.get(Subscription=subscription)
                access.Status = False
                access_to_update.append(access)
                
                # Prepare device operation
                device_operations.append({
                    'member_id': subscription.Member.id,
                    'member_name': f"{subscription.Member.First_Name} {subscription.Member.Last_Name}",
                    'access_obj': access
                })
                
                logger.info(f"Prepared access revocation for member: {subscription.Member.First_Name} {subscription.Member.Last_Name}")

            except AccessToGate.DoesNotExist:
                logger.warning(f"No access gate found for subscription: {subscription}")
                continue

        # Bulk update database records
        if subscriptions_to_update:
            Subscription.objects.bulk_update(subscriptions_to_update, ['Payment_Status'])
            logger.info(f"Updated {len(subscriptions_to_update)} subscription payment statuses")
            
        if access_to_update:
            AccessToGate.objects.bulk_update(access_to_update, ['Status'])
            logger.info(f"Updated {len(access_to_update)} access gate statuses")

        # Process device API calls
        success_count = 0
        fail_count = 0
        
        for operation in device_operations:
            try:
                success = disable_person_from_device(operation['member_id'])
                if success:
                    success_count += 1
                    logger.info(f"Successfully disabled {operation['member_name']} from device")
                else:
                    fail_count += 1
                    logger.error(f"Failed to disable {operation['member_name']} from device")
                    
            except Exception as e:
                fail_count += 1
                logger.error(f"Exception while disabling {operation['member_name']} from device: {str(e)}")

        logger.info(f"Scheduled task completed. Device operations - Success: {success_count}, Failed: {fail_count}")
        
        return {
            'subscriptions_updated': len(subscriptions_to_update),
            'access_gates_updated': len(access_to_update),
            'device_disable_success': success_count,
            'device_disable_failed': fail_count
        }
        
    except Exception as e:
        logger.error(f"Error in scheduled task: {str(e)}")
        raise

# def ScheduledTask():
#     try:
#         confdata = ConfigarationDB.objects.get(id=1)
#     except ConfigarationDB.DoesNotExist:
#         confdata = {
#             "JWT_IP": '0',
#             "JWT_PORT": "0",
#             "Call_Back_IP": '0',
#             "Call_Back_Port": "0",
#             "Admin_Username": "",
#             "Admin_Password": ""
#         }

#     # Get JWT token on local host Ztehodevice
#     url = f'http://http://127.0.0.1:80/jwt-api-token-auth/'
#     print(url)
#     header1 = {
#         'Content-Type': 'application/json'
#     }
#     token = "nil"
#     body = {
#         "username": confdata.Admin_Username,
#         "password": confdata.Admin_Password
#     }
#     json_payload = json.dumps(body)

#     try:
#         response = requests.post(url, headers=header1, data=json_payload)
#         if response.status_code == 200:
#             print('Request successful!')
#             token_dict = response.json()
#             token = token_dict['token']
#             print(token_dict)
#         else:
#             print("No connection")
#     except requests.RequestException:
#         print("No connection........")
    
#     urlforapi = 'http://http://127.0.0.1:80/api-token-auth/'
#     header2 = {
#         'Content-Type': 'application/json',
#         'Authorization': f'{token}'
#     }
#     try:
#         tokenresponse = requests.post(urlforapi, headers=header2,data=json_payload)
#         if tokenresponse.status_code == 200:
#             token_val = tokenresponse.json()
#             mytoken = token_val['token']
#     except:
#         print("No connection...")
#         mytoken = 0

#     headers = {
#         'Content-Type': 'application/json',
#         'Authorization': f'Token {mytoken}'
#     }

#     end_date = datetime.now()  # Assuming end_date is current datetime, adjust as necessary
#     resign_date = datetime.now()  # Assuming resign_date is current datetime, adjust as necessary

#     subscrib = Subscription.objects.filter(Subscription_End_Date__lte=end_date)
#     subscriptions_to_update = []
#     access_to_update = []

#     for subscription in subscrib:
#         subscription.Payment_Status = False
#         subscriptions_to_update.append(subscription)
#         subscription.Member.update_active_status()
#         try:
#             access = AccessToGate.objects.get(Subscription=subscription)
#             access.Status = False
#             access_to_update.append(access)
#         except AccessToGate.DoesNotExist:
#             continue

#     Subscription.objects.bulk_update(subscriptions_to_update, ['Payment_Status'])
#     AccessToGate.objects.bulk_update(access_to_update, ['Status'])

#     acc = AccessToGate.objects.all()

#     with requests.Session() as session:
#         for access in acc:
#             accessid = access.Member.Access_Token_Id
#             if access.Status is False:
#                 url = f"http://127.0.0.1:80/personnel/api/resigns/"
#                 data = {
#                     "employee": accessid,
#                     "disableatt": True,
#                     "resign_type": 1,
#                     "resign_date": str(resign_date),
#                     "reason": "Payment Pending",
#                 }
#             else:
#                 url = f"http://127.0.0.1:80/personnel/api/reinstatement/"
#                 data = {
#                     "resigns": [accessid]
#                 }

#             json_payload = json.dumps(data)

#             try:
#                 response = session.patch(url, headers=headers, data=json_payload)
#                 if response.status_code == 200:
#                     print("Succeed...")
#                 else:
#                     print("Failed.....")
#             except requests.RequestException:
#                 print("No connection from resigns")
#                 break

#     print("workinggggg.....")

            

    

# member configarations and subscription add on same method 
# one forign key field is prent in subscription Meber forign key, priod forign key, Batch forgin key

from Finance.models import Income, Expence

# @login_required(login_url='SignIn')
# def Member(request):
#     form = MemberAddForm()
#     sub_form = SubscriptionAddForm()
#     Trainee = MemberData.objects.all()[:8][::-1]
#     subscribers = Subscription.objects.all()[:8][::-1]
#     notification_payments = Payment.objects.filter(Payment_Date__gte = start_date, Payment_Date__lte = today)

#     if request.method == "POST":
#         form = MemberAddForm(request.POST, request.FILES)
#         sub_form = SubscriptionAddForm(request.POST)
#         if form.is_valid() and sub_form.is_valid():
#             member = form.save()
#             member.Discount = 0
#             member.save()
            
#             sub_data = sub_form.save()
#             start_dat = sub_data.Subscribed_Date
            
#             # Calculate end date based on any category
#             if sub_data.Period_Of_Subscription.Category == "Month":
#                 sub_data.Subscription_End_Date = start_dat + timedelta(days=(sub_data.Period_Of_Subscription.Period * 30))
#             elif sub_data.Period_Of_Subscription.Category == "Year":
#                 sub_data.Subscription_End_Date = start_dat + timedelta(days=(sub_data.Period_Of_Subscription.Period * 365))
#             elif sub_data.Period_Of_Subscription.Category == "Week":
#                 sub_data.Subscription_End_Date = start_dat + timedelta(days=(sub_data.Period_Of_Subscription.Period * 7))
#             elif sub_data.Period_Of_Subscription.Category == "Day":
#                 sub_data.Subscription_End_Date = start_dat + timedelta(days=sub_data.Period_Of_Subscription.Period)
#             else:
#                 # Default fallback - set to 30 days if category is unknown
#                 sub_data.Subscription_End_Date = start_dat + timedelta(days=30)
                
#             sub_data.Member = member
#             sub_data.save()
            
#             # Now we're sure Subscription_End_Date has a value
#             access_gate = AccessToGate.objects.create(
#                 Member=member,
#                 Subscription=sub_data,
#                 Validity_Date=sub_data.Subscription_End_Date
#             )
#             access_gate.save()
            
#             messages.success(request, "New Member Was Added Successfully Please Make Payment")
#             return redirect("Member")
#         else:
#             if not form.is_valid():
#                 messages.error(request, "Entered Personal Data is Not Validated Please try again")
#             if not sub_form.is_valid():
#                 messages.error(request, "Entered Subscription Data is Not Validated Please try again")
#             return redirect("Member")
            
#     context = {
#         "notification_payments": notification_payments,
#         "form": form,
#         "sub_form": sub_form,
#         "Trainee": Trainee,
#         "subscribers": subscribers,
#         "notificationcount": notification_payments.count()
#     }
#     return render(request, "members.html", context)

import requests
import json
from datetime import timedelta
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

def add_person_to_device_test(member, subscription, device_serial_number="CQUH233560091"):
    """
    Add a person to the access control device
    """
    url = "http://192.168.70.31:8050/api_updateperson"
    
    headers = {
        'Host': 'emmyfitness-betainfotech.pythonanywhere.com',
        'Content-Type': 'application/json',
        'Content-Length': '0',  # Set to '0' for GET requests, calculate for POST/PUT requests
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Token': '7ee4e345d834feb:c3abbf46c8714cb'
    }
    
    # Format dates for the device API
    try:
        start_date = subscription.Subscribed_Date.strftime('%Y-%m-%d')
        end_date = subscription.Subscription_End_Date.strftime('%Y-%m-%d')
    except:
        start_date = '2025-01-10'
        end_date = '2025-10-20'
    
    # Generate a simple card number if not exists (you might want to add this field to your model)
    card_number = f"{member.id:08d}"  # Pad member ID to 8 digits
    
    payload = {
        "BadgeNumber": str(member.id),
        "Name": f"{member.First_Name} {member.Last_Name}",
        "Card": card_number,
        "Password": str(member.id)[-4:].zfill(4),  # Use last 4 digits of ID as password
        "Privilege": "14",  # Default privilege level
        "StartDate": start_date,
        "EndDate": end_date,
        "AuthorizeddoorId": "1",  # Default door ID
        "TimeZone": "1",  # Default timezone
        "DeviceSerialNumber": device_serial_number,
        
    }
    
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"Successfully added member {member.First_Name} {member.Last_Name} to device")
            return True, "Member added to device successfully"
        else:
            error_msg = f"Failed to add member to device. Status code: {response.status_code}, Response: {response.text}"
            print(error_msg)
            return False, error_msg
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Error adding member to device: {str(e)}"
        print(error_msg)
        return False, error_msg

def add_person_to_device(member, subscription,access, device_serial_number="CQUH233560091"):
    
    try:
        start_date = subscription.Subscribed_Date.strftime('%Y-%m-%d')
        end_date = subscription.Subscription_End_Date.strftime('%Y-%m-%d')
    except:
        start_date = '2025-01-10'
        end_date = '2025-10-20'
    
    # Generate a simple card number if not exists (you might want to add this field to your model)
    card_number = f"{member.id:08d}"  # Pad member ID to 8 digits
    
    payload = {
        "BadgeNumber": str(member.id),
        "Name": f"{member.First_Name} {member.Last_Name}",
        "Card": card_number,
        "Password": str(member.id)[-4:].zfill(4),  # Use last 4 digits of ID as password
        "Privilege": "14",  # Default privilege level
        "StartDate": start_date,
        "EndDate": end_date,
        "AuthorizeddoorId": "1",  # Default door ID
        "TimeZone": "1",  # Default timezone
        "DeviceSerialNumber": device_serial_number,
        'access_gate':access
    }
    

    print(payload)

    url = "https://django.byteboot.in/update_person_to_db_device/"
    try:
        response = requests.post(url, data=json.dumps(payload))
        response.raise_for_status()  # raises error for bad status
        return response.json()  # if response is JSON
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
    
  


# def disable_person_from_device(member_id, device_serial_number="CQUH233560091"):
#     """
#     Disable a person from the access control device
#     """
#     url = "http://192.168.70.31:8050/api_disableperson"
    
#     headers = {
       
#         'Accept': '*/*',
#         'Accept-Encoding': 'gzip, deflate, br',
#         'Connection': 'keep-alive',
#         'token': '7ee4e345d834feb:c3abbf46c8714cb',
#         'Content-Type': 'application/json'
#     }
    
#     payload = {
#         "BadgeNumber": str(member_id),
#         "DeviceSerialNumber": device_serial_number
#     }
    
#     try:
#         response = requests.post(url, headers=headers, json=payload, timeout=10)
        
#         if response.status_code == 200:
#             print(f"Successfully disabled member {member_id} from device {device_serial_number}")
#             return True, "Member disabled from device successfully"
#         else:
#             error_msg = f"Failed to disable member from device. Status code: {response.status_code}, Response: {response.text}"
#             print(error_msg)
#             return False, error_msg
            
#     except requests.exceptions.RequestException as e:
#         error_msg = f"Error disabling member from device: {str(e)}"
#         print(error_msg)
#         return False, error_msg

@login_required(login_url='SignIn')
def Member(request):
    form = MemberAddForm()
    sub_form = SubscriptionAddForm()
    Trainee = MemberData.objects.all().order_by('-id')[:8]
    subscribers = Subscription.objects.all().order_by('-id')[:8]
    notification_payments = Payment.objects.filter(Payment_Date__gte=start_date, Payment_Date__lte=today)

    if request.method == "POST":
        form = MemberAddForm(request.POST, request.FILES)
        sub_form = SubscriptionAddForm(request.POST)
        
        if form.is_valid() and sub_form.is_valid():
            try:
                # Save member data
                member = form.save()
                member.Discount = 0
                member.save()
                
                # Save subscription data
                sub_data = sub_form.save()
                start_dat = sub_data.Subscribed_Date
                
                # Calculate end date based on category
                if sub_data.Period_Of_Subscription.Category == "Month":
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=(sub_data.Period_Of_Subscription.Period * 30))
                elif sub_data.Period_Of_Subscription.Category == "Year":
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=(sub_data.Period_Of_Subscription.Period * 365))
                elif sub_data.Period_Of_Subscription.Category == "Week":
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=(sub_data.Period_Of_Subscription.Period * 7))
                elif sub_data.Period_Of_Subscription.Category == "Day":
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=sub_data.Period_Of_Subscription.Period)
                else:
                    # Default fallback - set to 30 days if category is unknown
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=30)
                    
                sub_data.Member = member
                sub_data.save()
                
                # Create access gate entry
                access_gate = AccessToGate.objects.create(
                    Member=member,
                    Subscription=sub_data,
                    Validity_Date=sub_data.Subscription_End_Date
                )
                access_gate.save()
                
                # Add member to device
                device_success, device_message = add_person_to_device(member, sub_data,access_gate.Status)
                
                if device_success:
                    # Update member's access status
                    member.Access_status = True
                    member.save()
                    
                    # Update access gate status
                    access_gate.Status = True
                    access_gate.Payment_status = True  # Assuming payment will be made
                    access_gate.save()
                    
                    messages.success(request, f"New Member '{member.First_Name} {member.Last_Name}' was added successfully to both database and device. Please make payment.")
                else:
                    # Member added to database but failed on device
                    messages.warning(request, f"Member '{member.First_Name} {member.Last_Name}' was added to database but failed to add to device: {device_message}. Please try adding to device manually.")
                
                return redirect("Member")
                
            except Exception as e:
                # If any error occurs, show error message
                messages.error(request, f"Error adding member: {str(e)}")
                return redirect("Member")
        else:
            if not form.is_valid():
                messages.error(request, "Entered Personal Data is Not Validated. Please try again.")
            if not sub_form.is_valid():
                messages.error(request, "Entered Subscription Data is Not Validated. Please try again.")
            return redirect("Member")
            
    context = {
        "notification_payments": notification_payments,
        "form": form,
        "sub_form": sub_form,
        "Trainee": Trainee,
        "subscribers": subscribers,
        "notificationcount": notification_payments.count()
    }
    return render(request, "members.html", context)


# Alternative version with enhanced error handling and logging
@login_required(login_url='SignIn')
def MemberAdvanced(request):
    """
    Enhanced version with better error handling and device sync logging
    """
    form = MemberAddForm()
    sub_form = SubscriptionAddForm()
    Trainee = MemberData.objects.all().order_by('-id')[:8]
    subscribers = Subscription.objects.all().order_by('-id')[:8]
    notification_payments = Payment.objects.filter(Payment_Date__gte=start_date, Payment_Date__lte=today)

    if request.method == "POST":
        form = MemberAddForm(request.POST, request.FILES)
        sub_form = SubscriptionAddForm(request.POST)
        
        if form.is_valid() and sub_form.is_valid():
            member = None
            try:
                # Save member data
                member = form.save()
                member.Discount = 0
                member.save()
                
                # Save subscription data
                sub_data = sub_form.save()
                start_dat = sub_data.Subscribed_Date
                
                # Calculate end date based on category
                if sub_data.Period_Of_Subscription.Category == "Month":
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=(sub_data.Period_Of_Subscription.Period * 30))
                elif sub_data.Period_Of_Subscription.Category == "Year":
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=(sub_data.Period_Of_Subscription.Period * 365))
                elif sub_data.Period_Of_Subscription.Category == "Week":
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=(sub_data.Period_Of_Subscription.Period * 7))
                elif sub_data.Period_Of_Subscription.Category == "Day":
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=sub_data.Period_Of_Subscription.Period)
                else:
                    sub_data.Subscription_End_Date = start_dat + timedelta(days=30)
                    
                sub_data.Member = member
                sub_data.save()
                
                # Create access gate entry
                access_gate = AccessToGate.objects.create(
                    Member=member,
                    Subscription=sub_data,
                    Validity_Date=sub_data.Subscription_End_Date,
                    Status=False,  # Will be set to True if device sync succeeds
                    Payment_status=False
                )
                
                # Try to add member to device
                device_success, device_message = add_person_to_device(member, sub_data, access_gate.Status)
                
                if device_success:
                    # Device sync successful
                    member.Access_status = True
                    member.Access_Token_Id = f"DEVICE_SYNC_{member.id}"  # Optional: track device sync
                    member.save()
                    
                    access_gate.Status = True
                    access_gate.save()
                    
                    messages.success(request, 
                        f"✅ Member '{member.First_Name} {member.Last_Name}' added successfully! "
                        f"Database ID: {member.id}, Device Access: Enabled. Please make payment."
                    )
                else:
                    # Device sync failed but database entry exists
                    messages.warning(request, 
                        f"⚠️ Member '{member.First_Name} {member.Last_Name}' added to database (ID: {member.id}) "
                        f"but device sync failed: {device_message}. "
                        f"Please contact admin to manually sync with device."
                    )
                
                return redirect("Member")
                
            except Exception as e:
                # Log the error and clean up if necessary
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error adding member: {str(e)}")
                
                # If member was created but process failed, you might want to keep it
                # or optionally delete it depending on your business logic
                if member:
                    messages.error(request, 
                        f"❌ Error occurred after creating member '{member.First_Name} {member.Last_Name}'. "
                        f"Database ID: {member.id}. Error: {str(e)}. Please contact admin."
                    )
                else:
                    messages.error(request, f"❌ Failed to create member: {str(e)}")
                
                return redirect("Member")
        else:
            # Form validation errors
            error_messages = []
            if not form.is_valid():
                error_messages.append("Personal data validation failed")
                for field, errors in form.errors.items():
                    error_messages.append(f"{field}: {', '.join(errors)}")
                    
            if not sub_form.is_valid():
                error_messages.append("Subscription data validation failed")
                for field, errors in sub_form.errors.items():
                    error_messages.append(f"{field}: {', '.join(errors)}")
            
            messages.error(request, "Validation errors: " + "; ".join(error_messages))
            return redirect("Member")
            
    context = {
        "notification_payments": notification_payments,
        "form": form,
        "sub_form": sub_form,
        "Trainee": Trainee,
        "subscribers": subscribers,
        "notificationcount": notification_payments.count()
    }
    return render(request, "members.html", context)


# Utility function to manually sync existing members to device
def sync_member_to_device(member_id):
    """
    Utility function to manually sync a specific member to the device
    Can be called from Django admin or a management command
    """
    try:
        member = MemberData.objects.get(id=member_id)
        
        # Get the latest active subscription
        subscription = Subscription.objects.filter(
            Member=member,
            Payment_Status=True
        ).order_by('-Subscription_End_Date').first()
        
        if not subscription:
            return False, "No active subscription found for this member"
        
        success, message = add_person_to_device(member, subscription, member.Access_status)
        
        if success:
            member.Access_status = True
            member.save()
            
            # Update access gate if exists
            try:
                access_gate = AccessToGate.objects.get(Member=member, Subscription=subscription)
                access_gate.Status = True
                access_gate.save()
            except AccessToGate.DoesNotExist:
                pass
        
        return success, message
        
    except MemberData.DoesNotExist:
        return False, "Member not found"
    except Exception as e:
        return False, str(e)

@login_required(login_url='SignIn')
def MembersSingleView(request,pk):
    member = MemberData.objects.get(id = pk)
    try:
        subscription = Subscription.objects.filter(Member = member).first()
    except:
        subscription = None
    try:
        access = AccessToGate.objects.filter(Member = member).first()
    except:
        access = AccessToGate.objects.create(Member = member,Subscription = subscription,Validity_Date = datetime.now()) 
        access.save()
    sub_form = SubscriptionAddForm()
    payments = Payment.objects.filter(Member = member)
    

    context = {
        "member":member,
        "subscription":subscription,
        'sub_form':sub_form,
        "access":access,
        "notification_payments":notification_payments,
        "payments":payments

    }
    return render(request,"memberssingleview.html",context)

@login_required(login_url='SignIn')
def UpdateMember(request,pk):
    member = MemberData.objects.get(id = pk)
    if request.method == "POST":
        fname = request.POST["fname"]
        lname = request.POST["lname"]
        email = request.POST["email"]
        phone = request.POST["phone"]
        dob = request.POST["dob"]
        address = request.POST["address"]
        medicahistory = request.POST["mhistory"]

        member.First_Name = fname
        member.Last_Name = lname
        member.Date_Of_Birth = dob
        member.Mobile_Number = phone
        member.Email = email
        member.Address = address
        member.Medical_History = medicahistory
        member.save()
        messages.success(request,"User Data Updated..")
        return redirect("MembersSingleView",pk)

    return redirect("MembersSingleView",pk)

@login_required(login_url='SignIn')
def ProfilephotoUpdate(request,pk):
    if request.method == "POST":
        file = request.FILES["photo"]
        member = MemberData.objects.get(id = pk)
        member.Photo.delete()
        member.Photo = file
        member.save()
        messages.success(request, "Photo Changed...")
        return redirect("MembersSingleView",pk)
    return redirect("MembersSingleView",pk)

@login_required(login_url='SignIn')
def IdphotoUpdate(request,pk):
    if request.method == "POST":
        file = request.FILES["photo"]
        member = MemberData.objects.get(id = pk)
        member.Id_Upload.delete()
        member.Id_Upload = file
        member.save()
        messages.success(request, "Id Proof updated...")
        return redirect("MembersSingleView",pk)
    return redirect("MembersSingleView",pk)
    

@login_required(login_url='SignIn')
def UpdateAccessToken(request,pk):
    if request.method == "POST":
        newtoken = request.POST['newtkn']
        member = MemberData.objects.get(id=pk)
        member.Access_Token_Id = newtoken
        member.save()
        messages.info(request,"Token Changed")
        return redirect("MembersSingleView",pk)

    return redirect("MembersSingleView",pk)

@login_required(login_url='SignIn')
def DeleteMember(request,pk):
    member = MemberData.objects.get(id=pk)
    member.Photo.delete()
    member.delete()
    messages.error(request,"Member Data Deleted Success")
    return redirect("Member")

@login_required(login_url='SignIn')
def MemberAccess(request):
    return render(request,"memberaccess.html")



@login_required(login_url='SignIn')
def ChangeSubscription(request,pk):
    print("function Started..................")
    sub_form = SubscriptionAddForm()
    member = MemberData.objects.get(id = pk )

    if request.method == "POST":
        sub_form = SubscriptionAddForm(request.POST)
        if sub_form.is_valid():
            member = MemberData.objects.get(id = pk )
         
            subscription = Subscription.objects.filter(Member = member)
            for i in subscription:
                i.delete()

            sub_data = sub_form.save()
            sub_data.Member = member
            start_dat = sub_data.Subscribed_Date
            if sub_data.Period_Of_Subscription.Category == "Month":
                # days = sub_data.Period_Of_Subscription
                sub_data.Subscription_End_Date = start_dat +timedelta(days = (sub_data.Period_Of_Subscription.Period * 30))
            elif sub_data.Period_Of_Subscription.Category == "Year":
                # days = sub_data.Period_Of_Subscription
                sub_data.Subscription_End_Date = start_dat +timedelta(days = (sub_data.Period_Of_Subscription.Period * 365))
            sub_data.save()


            access = AccessToGate.objects.filter(Member = member)

            for i in access:
                i.delete()

            access_gate = AccessToGate.objects.create(Member = member,Subscription = sub_data,Validity_Date = sub_data.Subscription_End_Date )
            access_gate.save()

            messages.success(request,"Subscription Changed Success..")
            return redirect(MembersSingleView,pk)
            
        messages.error(request,"Form Is not valid")
        return redirect(MembersSingleView,pk)

    context = {
        "sub_form":sub_form,
        "member":member
    }
    return render(request,'changesubscription.html',context)
        
            
@login_required(login_url='SignIn')
def Payments(request):
    form = PaymentForm()
    pay = Payment.objects.all().order_by('-Payment_Date', '-id')[:8]
    sub_today = Subscription.objects.filter(Subscription_End_Date = today,Payment_Status = False).order_by('-Subscription_End_Date', '-id')[:8]
    sub_past = Subscription.objects.filter(Subscription_End_Date__lte = today,Payment_Status = False).order_by('-Subscription_End_Date', '-id')[:8]
    sub_Upcoming = Subscription.objects.filter(Subscription_End_Date__gte = today,Subscription_End_Date__lte = end_date, Payment_Status = False).order_by('-Subscription_End_Date', '-id')[:8]
    member = MemberData.objects.all()
    
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            access = AccessToGate.objects.get(Member = payment.Member)
            sub = Subscription.objects.get(Member = payment.Member)

            payment.Subscription_ID = sub
            payment.Amount = sub.Amount
            payment.Payment_Status = True 
            payment.Access_status = True
            payment.save()
            sub.Payment_Status = True
            sub.save()
            user = payment.Member
            user.Access_status = True
            user.save()
           
            try:
                sub_date = request.POST["sub_extendate"]
                access.Validity_Date = sub_date
                access.save()

            except:
                sub_date = sub.Subscription_End_Date
                access.Validity_Date = sub_date
                access.save()
                
            sub.Subscription_End_Date = sub_date
            sub.save()
            
            if AccessToGate.objects.filter(Validity_Date__gte = today, Member = payment.Member ).exists():
                access.Status = True 
                access.Payment_status = True
            else:
                access.Status = False 
            access.save()
            messages.success(request,"Payment Updated for member {}".format(user))
            return redirect("Payments")
        else:
            messages.error(request,"Payment Not Updated")
            return redirect("Payments")


    context = {
        "form":form,
        "pay":pay,
        "notification_payments":notification_payments,
        "sub_today":sub_today,
        "sub_past":sub_past,
        "sub_Upcoming":sub_Upcoming,
        "member":member,
    }
    return render(request, "payments.html",context)


# Add this view to your views.py
from django.http import JsonResponse
from django.db.models import Q

def search_members(request):
    search_term = request.GET.get('term', '')
    
    if len(search_term) < 2:
        return JsonResponse([], safe=False)
    
    members = MemberData.objects.filter(
        Q(First_Name__icontains=search_term) | 
        Q(Last_Name__icontains=search_term)
    )
    
    results = []
    for member in members:
        results.append({
            'id': member.id,
            'name': f"{member.First_Name} {member.Last_Name}"
        })
    
    return JsonResponse(results, safe=False)

@login_required(login_url='SignIn')
def AddNewPayment(request):
    if request.method == "POST":
        try:
            mid = request.POST["member"]
            member = MemberData.objects.get(id = mid)
            Sub = Subscription.objects.get(Member = member)
            context = {
                "member":member,
                "sub":Sub,
                "discounted":Sub.Amount - (Sub.Amount*member.Discount)/100
            }
            return render(request,"paymentscreen.html",context)
        except:
            messages.error(request, "Member is not exists")
            return redirect("Payments")
    else:
        messages.info(request, "Please select member to continue...")
        return redirect("Payments")

    
@login_required(login_url='SignIn')
def AddNewPaymentFromMember(request,pk):

    member = MemberData.objects.get(id = pk)
    Sub = Subscription.objects.get(Member = member)

    context = {
        "member":member,
        "sub":Sub,
        "discounted":Sub.Amount - (Sub.Amount*member.Discount)/100
    }
    return render(request,"paymentscreen.html",context)
    

@login_required(login_url='SignIn')
def PostNewPayment(request,pk):

    if request.method == "POST":

        mode = request.POST["mode"]
        date = request.POST["date"]
        member = MemberData.objects.get(id = pk)
        access = AccessToGate.objects.get(Member = member)
        sub = Subscription.objects.get(Member = member)
        payment = Payment.objects.create(Member = member, Subscription_ID = sub,Mode_of_Payment = mode,Payment_Date = date, Amount = sub.Amount - (sub.Amount*member.Discount)/100 )
        payment.save()

        payment.Payment_Status = True 
        payment.Access_status = True
        payment.save()
        sub.Payment_Status = True
        sub.save()
        user = payment.Member
        user.Access_status = True
        user.save()
        

        try:
            sub_date = request.POST.get("sub_extendate")
            if sub_date:
                access.Validity_Date = sub_date
                access.save()
            
                sub.Subscription_End_Date = sub_date
                sub.save()
            else:
                sub_date = sub.Subscription_End_Date
                access.Validity_Date = sub_date
                access.save()

        except:
            sub_date = sub.Subscription_End_Date
            access.Validity_Date = sub_date
            access.save()
           
        sub.Subscription_End_Date = sub_date
        sub.save()

        try:
             
            amount = request.POST.get("Custome_amount")
            if amount:
                payment.Amount = amount
                balance = float(sub.Amount) - float(amount)
                print(balance,"-------------------------------------------------")
                payment.Payment_Balance = balance
                payment.save()
            
            
        except:
            a = 100
    
            
        if AccessToGate.objects.filter(Validity_Date__gte = today, Member = member ).exists():
            access.Status = True 
            access.Payment_status = True
            add_person_to_device(member,sub, access.Status)

        else:
            access.Status = False 
        access.save()
        # ScheduledTask()
        print(payment.Amount,"------------------------------------")

        income = Income.objects.create(perticulers = f"Payment from {member} by {payment.Mode_of_Payment}",amount = payment.Amount,date = date)
        income.save()

        messages.success(request,"Payment Updated for member: {}".format(user))
        return redirect("Payments")

    return redirect("Payments")

from .models import BalancePayment

def make_balance_payment(request, pk):
    payment = Payment.objects.get(id=pk)
    balance = payment.Payment_Balance
    if request.method == "POST":
        payment.Payment_Status = True
        payment.Payment_Balance = 0
        payment.save() 
        balance_bill = BalancePayment.objects.create(payment = payment,Amount = balance)
        balance_bill.save()

        income = Income.objects.create(perticulers = f"Payment from {payment.Member} by {payment.Mode_of_Payment}",amount = balance)
        income.save()
        messages.success(request,"Balance Payment Updated for member {}".format(payment.Member))
        return redirect("AllPayments")

@login_required(login_url='SignIn')
def AddPaymentFromMemberTab(request,pk):
    member = MemberData.objects.get(id = pk)
    if request.method == "POST":
        date = request.POST["pay_date"]
        access = AccessToGate.objects.get(Member = member)
        sub = Subscription.objects.get(Member = member)

        payment = Payment.objects.create(Member = member,Payment_Date = date, Subscription_ID = sub,Amount = sub.Amount,Payment_Status = True,Access_status = True )
        payment.save()
        sub.Payment_Status = True
        sub.save()
        user = member
        user.Access_status = True
        user.save()

        try:
            sub_date = request.POST.get("sub_extendate")
            if sub_date:
                access.Validity_Date = sub_date
                access.save()

        except:
            sub_date = sub.Subscription_End_Date
            access.Validity_Date = sub_date
            access.save()

        
            
        sub.Subscription_End_Date = sub_date
        sub.save()
        if AccessToGate.objects.filter(Validity_Date__gte = today, Member = payment.Member ).exists():
            access.Status = True 
            access.Payment_status = True 
            add_person_to_device(member,sub,access.Status)

        else:
            access.Status = False 
        access.save()
        # ScheduledTask()
        income = Income.objects.create(perticulers = f"Payment from {member}",amount = payment.Amount,date = date)
        income.save()
        messages.success(request,"Payment Updated for member {}".format(user))
        return redirect("MembersSingleView",pk)

    context ={
        "member":member
    }
    # messages.success(request, "Payment Added")
    return render(request,"paymentaddsingle.html",context)

# creating receipt for payment 

# @login_required(login_url='SignIn')
# def ReceiptGenerate(request,pk):
#     logo = Logo.objects.get(id = 1)
#     payment  = Payment.objects.get(id = pk)
#     member = payment.Member
#     amount  = payment.Amount
#     payid  = pk
#     payment_date = payment.Payment_Date
#     try:
#         sub_start = payment.Subscription_ID.Subscribed_Date
#         sub_end = payment.Subscription_ID.Subscription_End_Date
#         period = payment.Subscription_ID.Period_Of_Subscription
#     except:
#         sub_start = "Null"
#         sub_end = "Null"
#         period = "Null"
#     template_path = "receipt.html"

#     context = {
#        "member":member,
#        "amount":amount,
#        "payid":payid,
#        "payment_date":payment_date,
#        "sub_start":sub_start,
#        "sub_end":sub_end,
#        "period":period,
#        "pk":pk,
#        "logo":logo
#     }
#     response = HttpResponse(content_type = "application/pdf")
#     response['Content-Disposition'] = 'filename=f"payment_receipt_{member}.pdf"'
#     template = get_template(template_path)
#     html = template.render(context)

#     # create PDF
#     pisa_status = pisa.CreatePDF(html, dest = response)
#     if pisa_status.err:
#         return HttpResponse("we are some erros <pre>" + html + '</pre>')
#     return response


def get_balance_receipt(request, pk):
    """
    Generate a professional PDF receipt for a payment.
    Uses WeasyPrint for higher quality PDF generation with better CSS support.
    """
    # Get necessary data
    logo = Logo.objects.get(id=1)
    balance_ = BalancePayment.objects.get(id=pk)
    payment = balance_.payment
    member = payment.Member
    amount = balance_.Amount
    payid = pk
    payment_date = payment.Payment_Date
    
    try:
        sub_start = payment.Subscription_ID.Subscribed_Date
        sub_end = payment.Subscription_ID.Subscription_End_Date
        period = payment.Subscription_ID.Period_Of_Subscription
    except:
        sub_start = "N/A"
        sub_end = "N/A"
        period = "N/A"
    
    # Generate barcode for receipt
    import barcode
    from barcode.writer import ImageWriter
    import base64
    from io import BytesIO
    
    # Create EAN13 barcode (you can use other formats too)
    ean = barcode.get_barcode_class('code128')
    ean_barcode = ean(f'OYAFITNESS{payid}', writer=ImageWriter())
    
    # Convert barcode to base64 for embedding in HTML
    buffer = BytesIO()
    ean_barcode.write(buffer)
    buffer.seek(0)
    barcode_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # Prepare context for template
    context = {
       "member": member,
       "amount": amount,
       "payid": payid,
       "payment_date": payment_date,
       "sub_start": sub_start,
       "sub_end": sub_end,
       "period": period,
       "barcode_image": barcode_image,
       "logo": logo,
       "balance":"balance"
    }
    
    # Render template to HTML
    template_path = "receipt.html"
    template = get_template(template_path)
    html = template.render(context)
    
    # Generate PDF using WeasyPrint for better CSS support
    try:
        from weasyprint import HTML, CSS
        from django.conf import settings
        import os
        
        # Create response object
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="payment_receipt_{member}_{payid}.pdf"'
        
        # Generate PDF with WeasyPrint
        base_url = request.build_absolute_uri('/')
        pdf = HTML(string=html, base_url=base_url).write_pdf()
        
        # Write PDF to response
        response.write(pdf)
        return response
        
    except ImportError:
        # Fallback to xhtml2pdf if WeasyPrint is not available
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="payment_receipt_{member}_{payid}.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        
        if pisa_status.err:
            return HttpResponse("We encountered some errors <pre>" + html + '</pre>')
        return response

@login_required(login_url='SignIn')
def ReceiptGenerate(request, pk):
    """
    Generate a professional PDF receipt for a payment.
    Uses WeasyPrint for higher quality PDF generation with better CSS support.
    """
    # Get necessary data
    logo = Logo.objects.get(id=1)
    payment = Payment.objects.get(id=pk)
    member = payment.Member
    amount = payment.Amount
    payid = pk
    payment_date = payment.Payment_Date
    
    try:
        sub_start = payment.Subscription_ID.Subscribed_Date
        sub_end = payment.Subscription_ID.Subscription_End_Date
        period = payment.Subscription_ID.Period_Of_Subscription
    except:
        sub_start = "N/A"
        sub_end = "N/A"
        period = "N/A"
    
    # Generate barcode for receipt
    import barcode
    from barcode.writer import ImageWriter
    import base64
    from io import BytesIO
    
    # Create EAN13 barcode (you can use other formats too)
    ean = barcode.get_barcode_class('code128')
    ean_barcode = ean(f'OYAFITNESS{payid}', writer=ImageWriter())
    
    # Convert barcode to base64 for embedding in HTML
    buffer = BytesIO()
    ean_barcode.write(buffer)
    buffer.seek(0)
    barcode_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # Prepare context for template
    context = {
       "member": member,
       "amount": amount,
       "payid": payid,
       "payment_date": payment_date,
       "sub_start": sub_start,
       "sub_end": sub_end,
       "period": period,
       "barcode_image": barcode_image,
       "logo": logo,
       "balance":" "
    }
    
    # Render template to HTML
    template_path = "receipt.html"
    template = get_template(template_path)
    html = template.render(context)
    
    # Generate PDF using WeasyPrint for better CSS support
    try:
        from weasyprint import HTML, CSS
        from django.conf import settings
        import os
        
        # Create response object
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="payment_receipt_{member}_{payid}.pdf"'
        
        # Generate PDF with WeasyPrint
        base_url = request.build_absolute_uri('/')
        pdf = HTML(string=html, base_url=base_url).write_pdf()
        
        # Write PDF to response
        response.write(pdf)
        return response
        
    except ImportError:
        # Fallback to xhtml2pdf if WeasyPrint is not available
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = f'attachment; filename="payment_receipt_{member}_{payid}.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        
        if pisa_status.err:
            return HttpResponse("We encountered some errors <pre>" + html + '</pre>')
        return response

@login_required(login_url='SignIn')
def DeletePayment(request,pk):
    Pay = Payment.objects.get(id = pk).delete()
    messages.info(request,"Payment Deleted")
    return redirect("Payments")



from datetime import datetime, date, time
import json
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.decorators import login_required

@login_required(login_url='SignIn')
def ExtendAccessToGate(request, pk):

    settings_conf = ConfigarationDB.objects.first()
    call_back = settings_conf.JWT_IP
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password

    member = get_object_or_404(MemberData, id=pk)
    try:
        subscrib = Subscription.objects.filter(Member=member).first()
    except Subscription.DoesNotExist:
        subscrib = None

    if request.method == "POST":

        # comes as: 2025-01-20 or 2025-01-20T10:30 depending on input
        extension_raw = request.POST.get("exend")

        # --- normalize extension to datetime end-of-day ---
        try:
            # try full datetime first
            try:
                ext_dt = datetime.strptime(extension_raw, "%Y-%m-%dT%H:%M")
            except ValueError:
                # otherwise treat as date and set to 23:59:59
                ext_d = datetime.strptime(extension_raw, "%Y-%m-%d").date()
                ext_dt = datetime.combine(ext_d, time.max)

        except Exception as e:
            messages.error(request, f"Invalid extension date: {e}")
            return redirect("MembersSingleView", pk=pk)

        # ---------- SAVE DB ----------
        access = AccessToGate.objects.get(Member=member)
        access.Validity_Date = ext_dt.date()      # if this is DateField
        access.Status = True
        access.save()

        # IMPORTANT: your field is DateField so time is lost
        # But we keep full datetime for device
        subscrib.Subscription_End_Date = ext_dt.date()
        subscrib.save()

        # -------- build begin and end times --------
        # begin comes from subscription start date
        began_dt = datetime.combine(subscrib.Subscribed_Date, time.min)

        # end = extension, full dt with time
        beginTime = began_dt.strftime("%Y-%m-%dT%H:%M:%S")
        endTime = ext_dt.strftime("%Y-%m-%dT%H:%M:%S")

        # -------- payload MATCHING working function --------
        person_data = {
            "employee_no": str(member.id),
            "name": member.First_Name,
            "userType": "normal",
            "is_valid": True,
            "beginTime": beginTime,
            "endTime": endTime,
            "doorRight": "1"
        }

        # -------- CALL DEVICE API --------
        try:
            response = disable_enable_person_form_hik(
                call_back,
                device_ip,
                username,
                password,
                person_data
            )

            if not response:
                raise ValueError("Empty response from device API")

            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response

        except Exception as e:
            messages.error(request, f"Device communication failed: {e}")
            return redirect("MembersSingleView", pk=pk)

        # -------- SAFE GETTERS --------
        status_code = response_data.get("statusCode")
        status_string = response_data.get("statusString", "")
        sub_status = response_data.get("subStatusCode", "")
        error_msg = response_data.get("errorMsg", "")

        # -------- HANDLE RESPONSES --------
        if status_code == 1:
            messages.success(
                request,
                f"Access extended till {ext_dt.strftime('%Y-%m-%d %H:%M:%S')} and synced to device."
            )

        elif status_code == 6 and sub_status == "employeeNoNotExist":
            messages.error(request, "User not found on device. Add user first.")

        elif status_code == 6 and sub_status == "badJsonContent":
            messages.error(request, f"Bad JSON payload: {error_msg}")

        else:
            messages.error(
                request,
                f"Device error: {status_string} ({status_code}) {sub_status} {error_msg}"
            )

        return redirect("MembersSingleView", pk=pk)

    return render(request, "grandaccessforgate.html", {"member": member})


@login_required(login_url='SignIn')
def BlockAccess(request,pk):
    member = MemberData.objects.get(id = pk)
    access = AccessToGate.objects.get(Member = member)
    access.Status = False
    access.save()
    # disable_person_from_device(member.id)
    messages.success(request,"Access Status Changed....")
    return redirect ("delete_person_form_hik_device" ,employee_no =  member.id)
    # return redirect(MembersSingleView,pk)

@login_required(login_url='SignIn')
def AllMembers(request):
    members = MemberData.objects.all().order_by('-id')
    return render(request, "allmembers.html",{"member":members})

@login_required(login_url='SignIn')
def AllPayments(request):
    payments = Payment.objects.all().order_by('-Payment_Date', '-id')
    return render(request,"allpayments.html",{"payments":payments})



@login_required(login_url='SignIn')
def FeePendingMembers(request):
    subscribers = Subscription.objects.all().order_by('-id')

    return render(request,"feependingmembers.html",{"subscribers":subscribers})
# Reports generation

@login_required(login_url='SignIn')
def FullMemberReport(request):
    
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=Memberreportfull{}-{}.csv'.format(date,date_year)
    
    member = MemberData.objects.all().order_by("-Date_Added")
    def generate_serial_number():
        current_time = datetime.now()
        serial_number = current_time.strftime("%Y%m%d%H%M%S")
        return serial_number
    TokenU = generate_serial_number()
    writer = csv.writer(response)
    writer.writerow(["Sl No",'First_Name',"Last_Name","Date_Of_Birth","Gender","Mobile_Number","Email","Address","Registration_Date","Date_Added","Access_Token","Subscription","Batch"])
    counter = 0
    for i in member:
        sub = Subscription.objects.get(Member = i)
        batch = sub.Batch
        counter +=1
        writer.writerow([counter,i.First_Name,i.Last_Name,i.Date_Of_Birth,i.Gender,i.Mobile_Number,i.Email,i.Address,i.Registration_Date,i.Date_Added,i.Access_Token_Id,sub,batch])
    response.write('\n')  # Move to the next line after the first row
    response.write(f"Doc Number: {TokenU}")  # Write the unique report number to the next line
    return response


@login_required(login_url='SignIn')
def MonthMemberReport(request):
    
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=Memberreportmonth{}-{}.csv'.format(date,date_year)
    counter = 0
    
    member = MemberData.objects.filter(Date_Added__month = date).order_by("-Date_Added")
    
    writer = csv.writer(response)
    writer.writerow(["Sl No",'First_Name',"Last_Name","Date_Of_Birth","Gender","Mobile_Number","Email","Address","Medical_History","Registration_Date","Date_Added","Access_Token"])
    for i in member:
        counter +=1
        writer.writerow([counter,i.First_Name,i.Last_Name,i.Date_Of_Birth,i.Gender,i.Mobile_Number,i.Email,i.Address,i.Medical_History,i.Registration_Date,i.Date_Added,i.Access_Token_Id])

    def generate_serial_number():
        current_time = datetime.now()
        serial_number = current_time.strftime("%Y%m%d%H%M%S")
        return serial_number
    TokenU = generate_serial_number()

    response.write('\n')  # Move to the next line after the first row
    response.write(f"Doc Number: {TokenU}")  # Write the unique report number to the next line

    return response

@login_required(login_url='SignIn')
def DateWiseMemberReport(request):
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=MemberreportDate{}-{}.csv'.format(date,date_year)
    if request.method == "POST":
        sdate = request.POST["sdate"]
        edate = request.POST["enddate"]
        
    counter = 0
    member = MemberData.objects.filter(Date_Added__gte = sdate,Date_Added__lte = edate ).order_by("-Date_Added")
    
    writer = csv.writer(response)
    writer.writerow(["Slno",'First_Name',"Last_Name","Date_Of_Birth","Gender","Mobile_Number","Email","Address","Medical_History","Registration_Date","Date_Added","Access_Token"])
    for i in member:
        counter +=1
        writer.writerow([counter,i.First_Name,i.Last_Name,i.Date_Of_Birth,i.Gender,i.Mobile_Number,i.Email,i.Address,i.Medical_History,i.Registration_Date,i.Date_Added,i.Access_Token_Id])


    def generate_serial_number():
        current_time = datetime.now()
        serial_number = current_time.strftime("%Y%m%d%H%M%S")
        return serial_number
    TokenU = generate_serial_number()
    response.write('\n')  # Move to the next line after the first row
    response.write(f"Doc Number: {TokenU}")  # Write the unique report number to the next line
    
    return response


@login_required(login_url='SignIn')
def DateWisePaymentReport(request):
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=paymentreportDate{}-{}.csv'.format(date,date_year)
    if request.method == "POST":
        sdate = request.POST["sdate"]
        edate = request.POST["enddate"]
        counter = 0
    
        payment = Payment.objects.filter(Payment_Date__gte = sdate,Payment_Date__lte = edate ).order_by("-Payment_Date")
        
        writer = csv.writer(response)
        writer.writerow(["Slno","Member","Subscription_ID","Amount","Payment_Date"])
        for i in payment:
            counter +=1
            writer.writerow([counter,i.Member,i.Subscription_ID,i.Amount,i.Payment_Date])

        def generate_serial_number():
            current_time = datetime.now()
            serial_number = current_time.strftime("%Y%m%d%H%M%S")
            return serial_number
        TokenU = generate_serial_number()
        response.write('\n')  # Move to the next line after the first row
        response.write(f"Doc Number: {TokenU}") 
        return response
    return HttpResponse("No Valid Fiels")
    

def PaymentReport(request):
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=paymentreportfull{}-{}.csv'.format(date,date_year)
    counter = 0
        
    try:
        payment = Payment.objects.all().order_by("-Payment_Date")
        
        writer = csv.writer(response)
        writer.writerow(["Slno","Member","Subscription_ID","Amount","Payment_Date"])
        for i in payment:
            counter +=1
            writer.writerow([counter,i.Member,i.Subscription_ID,i.Amount,i.Payment_Date])

        
        def generate_serial_number():
            current_time = datetime.now()
            serial_number = current_time.strftime("%Y%m%d%H%M%S")
            return serial_number
        TokenU = generate_serial_number()
        response.write('\n')  # Move to the next line after the first row
        response.write(f"Doc Number: {TokenU}") 

        return response
    except:
        return HttpResponse("No Valid Fiels")
    

@login_required(login_url='SignIn')
def PaymentReportMonth(request):
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=paymentreportmonth{}-{}.csv'.format(date,date_year)
    counter = 0
        
    try:
        payment = Payment.objects.filter(Payment_Date__month = date ).order_by("-Payment_Date")
        
        writer = csv.writer(response)
        writer.writerow(["SlNo","Member","Subscription_ID","Amount","Payment_Date"])
        for i in payment:
            counter += 1
            writer.writerow([counter,i.Member,i.Subscription_ID,i.Amount,i.Payment_Date])

        
        def generate_serial_number():
            current_time = datetime.now()
            serial_number = current_time.strftime("%Y%m%d%H%M%S")
            return serial_number
        TokenU = generate_serial_number()
        response.write('\n')  # Move to the next line after the first row
        response.write(f"Doc Number: {TokenU}") 
        return response
    except:
        return HttpResponse("No Valid Fiels")


@login_required(login_url='SignIn')
def PDFprintFullMemberReport(request):
    date = timezone.now().month
    date_year = timezone.now().year
    member = MemberData.objects.all()
    template_path = "reportpdf_fulldata.html"
    def generate_serial_number():
        current_time = datetime.now()
        serial_number = current_time.strftime("%Y%m%d%H%M%S")
        return serial_number
    TokenU = generate_serial_number()
    context = {
       "member":member,
       "Token":TokenU
    }
    response = HttpResponse(content_type = "application/pdf")
    response['Content-Disposition'] = "filename=Memberreportfull{}-{}.pdf".format(date,date_year)
    template = get_template(template_path)
    html = template.render(context)

    # create PDF
    pisa_status = pisa.CreatePDF(html, dest = response)
    if pisa_status.err:
        return HttpResponse("we are some erros <pre>" + html + '</pre>')
    return response


@login_required(login_url='SignIn')
def PDFprintFullPaymentReport(request):
    date = timezone.now().month
    date_year = timezone.now().year
    payment = Payment.objects.all()
    template_path = "reportpdf_fulldata_payment.html"
    def generate_serial_number():
        current_time = datetime.now()
        serial_number = current_time.strftime("%Y%m%d%H%M%S")
        return serial_number
    TokenU = generate_serial_number()

    context = {
       "payment":payment,
       "Token":TokenU
    }
    response = HttpResponse(content_type = "application/pdf")
    response['Content-Disposition'] = "filename=Paymentreportfull{}-{}.pdf".format(date,date_year)
    template = get_template(template_path)
    html = template.render(context)

    # create PDF
    pisa_status = pisa.CreatePDF(html, dest = response)
    if pisa_status.err:
        return HttpResponse("we are some erros <pre>" + html + '</pre>')
    return response

@login_required(login_url='SignIn')
def PDFmonthMember(request):
    date = timezone.now().month
    date_year = timezone.now().year
    member = MemberData.objects.filter(Date_Added__month = date)
    template_path = "reportPDFmonthMember.html"
    def generate_serial_number():
        current_time = datetime.now()
        serial_number = current_time.strftime("%Y%m%d%H%M%S")
        return serial_number
    TokenU = generate_serial_number()

    context = {
       "member":member,
       "date":date,
       "Token":TokenU
    }
    response = HttpResponse(content_type = "application/pdf")
    response['Content-Disposition'] = "filename=Memberreportmonth{}-{}.pdf".format(date,date_year)
    template = get_template(template_path)
    html = template.render(context)

    # create PDF
    pisa_status = pisa.CreatePDF(html, dest = response)
    if pisa_status.err:
        return HttpResponse("we are some erros <pre>" + html + '</pre>')
    return response


@login_required(login_url='SignIn')
def PDFmonthpayment(request):
    date = timezone.now().month
    date_year = timezone.now().year
    payment = Payment.objects.filter(Payment_Date__month = date)
    template_path = "reportPDFmonthpayment.html"
    def generate_serial_number():
        current_time = datetime.now()
        serial_number = current_time.strftime("%Y%m%d%H%M%S")
        return serial_number
    TokenU = generate_serial_number()

    context = {
       "payment":payment,
       "date":date,
       "Token":TokenU
    }
    response = HttpResponse(content_type = "application/pdf")
    response['Content-Disposition'] = "filename=Paymentreportmonth{}-{}.pdf".format(date,date_year)
    template = get_template(template_path)
    html = template.render(context)

    # create PDF
    pisa_status = pisa.CreatePDF(html, dest = response)
    if pisa_status.err:
        return HttpResponse("we are some erros <pre>" + html + '</pre>')
    return response

    

# Payments and now updates after deploy


@allowed_users(allowed_roles=["admin",])
@login_required(login_url='SignIn')
def EditPayment(request,pk):
    mypay = Payment.objects.get(id = pk)
    sub = mypay.Subscription_ID
    print("sub----------------------------",sub)
    if request.method == "POST":
        mode = request.POST["Mode"]
        Amount = request.POST["amount"]
        date = request.POST["date"]

        mypay.Amount = Amount
        print(mypay.Amount)
        try:
            balance = float(sub.Amount) - float(Amount)
            mypay.Payment_Balance = balance
        except:
            pass
        mypay.Mode_of_Payment = mode 
        mypay.Payment_Date = date
        mypay.save()
        messages.success(request,"Payment Data Updated")
        return redirect("Payments")

    context = {
        "mypay":mypay
    }
    return render(request,"editpayment.html",context)


# discounts to members 
@allowed_users(allowed_roles=["admin",])
@login_required(login_url='SignIn')
def Discount(request):
    member = MemberData.objects.all()
    discount = Discounts.objects.all()
    context = {
        "member":member,
        "discount":discount
    }
    return render(request,"discounts.html",context)


@allowed_users(allowed_roles=["admin",])
@login_required(login_url='SignIn')
def DiscountAllAdd(request):
    if request.method == "POST":
        dateend = request.POST["dateend"]
        disper  = request.POST["disper"]
        member  = MemberData.objects.filter(Special_Discount = False)
        dis = Discounts.objects.create(Discount_Percentage = disper,Till_Date = dateend)
        dis.save()
        member.update(Discount = disper)
        # member.save()
        messages.success(request,"Discount Applied for all members")
        return redirect("Discount")

    return redirect("Discounts")

@allowed_users(allowed_roles=["admin",])
@login_required(login_url='SignIn')
def DiscountSingleAdd(request):
    if request.method == "POST":
        member = MemberData.objects.get(id = request.POST["member"])
        dis = request.POST["disper"]
        member.Discount = dis
        member.Special_Discount = True
        member.save()
        messages.success(request,"Special Discount Applied Members")
        return redirect("Discount")


@allowed_users(allowed_roles=["admin",])
@login_required(login_url='SignIn')
def DeleteAllDiscounts(request,pk):
    Discounts.objects.get(id = pk).delete()
    member = MemberData.objects.filter(Special_Discount = False)
    member.update(Discount = 0)
    # member.save()
    messages.success(request,"Discount Deleted")
    return redirect("Discount")

@allowed_users(allowed_roles=["admin",])
@login_required(login_url='SignIn')
def DeletespecialDiscount(request,pk):
    member = MemberData.objects.get(id = pk)
    member.Discount = 0
    member.Special_Discount = False
    member.save()
    messages.success(request,"Discount Deleted")
    return redirect("Discount")







    




#    Api call for node mcu access to gate
from django.shortcuts import render,redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.mail import send_mail,EmailMessage
from django.template.loader import render_to_string

@csrf_exempt
def api_call(request):
    if request.method == "POST":
        data  = request.POST
        token = request.POST["token"]
        print(data,"0000000000000000000000000000")
        try:
            member = MemberData.objects.get(Access_Token_Id = token)
        except:
            access = False
        # access = AccessToGate.objects.get(Member = member)
        # access.Status = True
        # access.save()
        try:
            access = member.Access_status
        except:
            access = False
            
        if access == True:
            # access.Status = True
            # access.save()

            return JsonResponse({"status": True, "member": member.First_Name})
        else:
            # access.Status = False
            # access.save()
            mail_subject = 'NEW RFID DETECTED '
            template = 'email_for_rfid.html'
            context = {
            'rfid_number': token,
            
                }
    
            message = render_to_string(template, context)
            email = EmailMessage(mail_subject, message, to=['emmysforrfid@gmail.com',"gopinath.pramod@gmail.com"])
            email.content_subtype = "html"
            email.send(fail_silently=True)

            return JsonResponse({"status": False})

    return JsonResponse({"status": False})







# bulk page sync members 

# views.py - Enhanced Backend Functions with Real-time Updates

import requests
import json
import logging
import threading
import time
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from datetime import datetime
from django.utils import timezone

# Configure logging for command line output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bulk_sync.log'),
        logging.StreamHandler()  # This outputs to command line
    ]
)

logger = logging.getLogger(__name__)

# Global variables for tracking sync status
SYNC_STATUS_KEY = 'bulk_sync_status'
SYNC_UPDATES_KEY = 'bulk_sync_updates'

class SyncStatusManager:
    """Manages sync status and updates in cache"""
    
    @staticmethod
    def initialize_sync(total_members):
        """Initialize sync status"""
        status = {
            'status': 'in_progress',
            'total': total_members,
            'processing': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'current_member': None,
            'start_time': timezone.now().isoformat(),
            'updates': []
        }
        cache.set(SYNC_STATUS_KEY, status, timeout=3600)  # 1 hour timeout
        cache.set(SYNC_UPDATES_KEY, [], timeout=3600)
        logger.info(f"🚀 BULK SYNC STARTED - Total members to process: {total_members}")
        return status
    
    @staticmethod
    def update_status(field, value, current_member=None):
        """Update sync status"""
        status = cache.get(SYNC_STATUS_KEY, {})
        if field in status:
            status[field] = value
        if current_member:
            status['current_member'] = current_member
        cache.set(SYNC_STATUS_KEY, status, timeout=3600)
        return status
    
    @staticmethod
    def increment_counter(counter_name, current_member=None):
        """Increment a counter in sync status"""
        status = cache.get(SYNC_STATUS_KEY, {})
        if counter_name in status:
            status[counter_name] += 1
        if current_member:
            status['current_member'] = current_member
        cache.set(SYNC_STATUS_KEY, status, timeout=3600)
        return status
    
    @staticmethod
    def add_update(message, update_type='info'):
        """Add a status update"""
        updates = cache.get(SYNC_UPDATES_KEY, [])
        update = {
            'timestamp': timezone.now().isoformat(),
            'message': message,
            'type': update_type
        }
        updates.append(update)
        
        # Keep only last 50 updates to prevent memory issues
        if len(updates) > 50:
            updates = updates[-50:]
        
        cache.set(SYNC_UPDATES_KEY, updates, timeout=3600)
        
        # Log to command line with appropriate level
        if update_type == 'error':
            logger.error(f"❌ {message}")
        elif update_type == 'warning':
            logger.warning(f"⚠️ {message}")
        elif update_type == 'success':
            logger.info(f"✅ {message}")
        elif update_type == 'processing':
            logger.info(f"⏳ {message}")
        else:
            logger.info(f"ℹ️ {message}")
        
        return updates
    
    @staticmethod
    def get_status():
        """Get current sync status"""
        return cache.get(SYNC_STATUS_KEY, {})
    
    @staticmethod
    def get_recent_updates(limit=10):
        """Get recent status updates"""
        updates = cache.get(SYNC_UPDATES_KEY, [])
        return updates[-limit:] if updates else []
    
    @staticmethod
    def complete_sync():
        """Mark sync as completed"""
        status = cache.get(SYNC_STATUS_KEY, {})
        status['status'] = 'completed'
        status['end_time'] = timezone.now().isoformat()
        cache.set(SYNC_STATUS_KEY, status, timeout=3600)
        
        total = status.get('total', 0)
        successful = status.get('successful', 0)
        failed = status.get('failed', 0)
        skipped = status.get('skipped', 0)
        
        logger.info(f"🏁 BULK SYNC COMPLETED - Total: {total}, Success: {successful}, Failed: {failed}, Skipped: {skipped}")
        return status

def add_person_to_device_bulk(member, subscription, device_serial_number="CQUH233560091"):
    """
    Add a person to the access control device (for bulk operations) with enhanced logging
    """
    member_name = f"{member.First_Name} {member.Last_Name}"
    
    # Log the attempt
    SyncStatusManager.add_update(f"Processing {member_name} (ID: {member.id})", 'processing')
    logger.info(f"⏳ PROCESSING MEMBER: {member_name} (ID: {member.id})")
    
    url = "http://192.168.70.31:8050/api_updateperson"
    
    
    headers = {
        'Host': 'emmyfitness-betainfotech.pythonanywhere.com',
        'Content-Type': 'application/json',
        'Content-Length': '0',  # Set to '0' for GET requests, calculate for POST/PUT requests
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Token': '7ee4e345d834feb:c3abbf46c8714cb'
    }
    
    
    # Format dates for the device API
    start_date = subscription.Subscribed_Date.strftime('%Y-%m-%d')
    end_date = subscription.Subscription_End_Date.strftime('%Y-%m-%d')
    
    # Generate card number and password
    card_number = f"{member.id:08d}"  # Pad member ID to 8 digits
    password = str(member.id)[-4:].zfill(4)  # Last 4 digits of ID as password
    
    payload = {
        "BadgeNumber": str(member.id),
        "Name": member_name,
        "Card": card_number,
        "Password": password,
        "Privilege": "14",  # Default privilege level
        "StartDate": start_date,
        "EndDate": end_date,
        "AuthorizeddoorId": "1",  # Default door ID
        "TimeZone": "1",  # Default timezone
        "DeviceSerialNumber": device_serial_number
    }
    
    logger.info(f"📡 SENDING REQUEST: {member_name} -> Device (Card: {card_number}, Valid: {start_date} to {end_date})")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            logger.info(f"✅ SUCCESS: {member_name} successfully synced to device")
            SyncStatusManager.add_update(f"✅ {member_name} successfully synced", 'success')
            return True, "Success"
        else:
            error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
            logger.error(f"❌ FAILED: {member_name} - {error_msg}")
            SyncStatusManager.add_update(f"❌ {member_name} failed: {error_msg}", 'error')
            return False, error_msg
            
    except requests.exceptions.Timeout:
        error_msg = "Request timeout"
        logger.error(f"❌ TIMEOUT: {member_name} - {error_msg}")
        SyncStatusManager.add_update(f"❌ {member_name} timeout", 'error')
        return False, error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {str(e)[:100]}"
        logger.error(f"❌ NETWORK ERROR: {member_name} - {error_msg}")
        SyncStatusManager.add_update(f"❌ {member_name} network error", 'error')
        return False, error_msg

def bulk_sync_all_members():
    """
    Sync all active members to the device with real-time status updates
    """
    logger.info("=" * 80)
    logger.info("🚀 STARTING BULK MEMBER SYNCHRONIZATION")
    logger.info("=" * 80)
    
    results = {
        'total_members': 0,
        'successful': [],
        'failed': [],
        'skipped': [],
        'start_time': datetime.now(),
        'end_time': None
    }
    
    try:
        # Get all active members with valid subscriptions
        from .models import MemberData, Subscription, AccessToGate  # Import your models here
        
        active_members = MemberData.objects.filter(Active_status=True)
        results['total_members'] = active_members.count()
        
        logger.info(f"📊 FOUND {results['total_members']} active members to process")
        
        # Initialize sync status
        SyncStatusManager.initialize_sync(results['total_members'])
        
        processed_count = 0
        
        for member in active_members:
            member_name = f"{member.First_Name} {member.Last_Name}"
            
            try:
                # Update current processing status
                SyncStatusManager.update_status('current_member', member_name)
                SyncStatusManager.increment_counter('processing')
                
                logger.info(f"🔍 CHECKING MEMBER: {member_name} (ID: {member.id}) - Progress: {processed_count + 1}/{results['total_members']}")
                
                # Get the latest active subscription for this member
                subscription = Subscription.objects.filter(
                    Member=member,
                    Payment_Status=True,
                    Subscription_End_Date__gte=datetime.now().date()
                ).order_by('-Subscription_End_Date').first()
                
                if not subscription:
                    skip_reason = 'No active subscription found'
                    logger.warning(f"⏭️ SKIPPING: {member_name} - {skip_reason}")
                    SyncStatusManager.add_update(f"⏭️ {member_name} skipped: {skip_reason}", 'warning')
                    
                    results['skipped'].append({
                        'member_id': member.id,
                        'member_name': member_name,
                        'reason': skip_reason
                    })
                    
                    SyncStatusManager.increment_counter('skipped')
                    processed_count += 1
                    continue
                
                logger.info(f"📅 SUBSCRIPTION FOUND: {member_name} - Valid until {subscription.Subscription_End_Date}")
                
                # Add small delay to prevent overwhelming the device
                time.sleep(0.5)  # 500ms delay between requests
                
                # Sync to device
                success, message = add_person_to_device_bulk(member, subscription)
                
                if success:
                    # Update member status
                    member.Access_status = True
                    member.save()
                    
                    # Update access gate if exists
                    try:
                        access_gate = AccessToGate.objects.get(Member=member, Subscription=subscription)
                        access_gate.Status = True
                        access_gate.save()
                        logger.info(f"🔄 UPDATED: Access gate status for {member_name}")
                    except AccessToGate.DoesNotExist:
                        logger.info(f"ℹ️ NO ACCESS GATE: {member_name} - Skipping gate update")
                    
                    results['successful'].append({
                        'member_id': member.id,
                        'member_name': member_name,
                        'subscription_end': subscription.Subscription_End_Date.strftime('%Y-%m-%d')
                    })
                    
                    SyncStatusManager.increment_counter('successful')
                    logger.info(f"✅ COMPLETED: {member_name} successfully processed")
                    
                else:
                    results['failed'].append({
                        'member_id': member.id,
                        'member_name': member_name,
                        'error': message
                    })
                    
                    SyncStatusManager.increment_counter('failed')
                    logger.error(f"❌ FAILED: {member_name} - {message}")
                
                # Update processing counter
                SyncStatusManager.update_status('processing', SyncStatusManager.get_status().get('processing', 0) - 1)
                processed_count += 1
                
                # Log progress every 10 members
                if processed_count % 10 == 0:
                    progress_pct = (processed_count / results['total_members']) * 100
                    logger.info(f"📈 PROGRESS UPDATE: {processed_count}/{results['total_members']} ({progress_pct:.1f}%) processed")
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ EXCEPTION: {member_name} - {error_msg}")
                SyncStatusManager.add_update(f"❌ {member_name} exception: {error_msg}", 'error')
                
                results['failed'].append({
                    'member_id': member.id,
                    'member_name': member_name,
                    'error': error_msg
                })
                
                SyncStatusManager.increment_counter('failed')
                SyncStatusManager.update_status('processing', SyncStatusManager.get_status().get('processing', 0) - 1)
                processed_count += 1
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"❌ CRITICAL ERROR: {error_msg}")
        SyncStatusManager.add_update(f"❌ Critical error: {error_msg}", 'error')
        results['general_error'] = error_msg
    
    results['end_time'] = datetime.now()
    results['duration'] = (results['end_time'] - results['start_time']).total_seconds()
    
    # Complete the sync
    SyncStatusManager.complete_sync()
    
    # Final summary
    logger.info("=" * 80)
    logger.info("🏁 BULK SYNCHRONIZATION COMPLETED")
    logger.info(f"📊 FINAL RESULTS:")
    logger.info(f"   Total Members: {results['total_members']}")
    logger.info(f"   ✅ Successful: {len(results['successful'])}")
    logger.info(f"   ❌ Failed: {len(results['failed'])}")
    logger.info(f"   ⏭️ Skipped: {len(results['skipped'])}")
    logger.info(f"   ⏱️ Duration: {results['duration']:.2f} seconds")
    logger.info("=" * 80)
    
    return results

@login_required(login_url='SignIn')
def bulk_sync_page(request):
    """
    Page to display bulk sync interface
    """
    from .models import MemberData  # Import your models here
    
    context = {
        'total_active_members': MemberData.objects.filter(Active_status=True).count(),
        'total_members': MemberData.objects.count(),
        'members_with_access': MemberData.objects.filter(Access_status=True).count(),
    }
    return render(request, 'bulk_sync.html', context)

@csrf_exempt
@login_required(login_url='SignIn')
def bulk_sync_execute(request):
    """
    AJAX endpoint to execute bulk sync
    """
    if request.method == 'POST':
        try:
            logger.info("🎯 BULK SYNC REQUEST RECEIVED")
            
            # Check if sync is already running
            current_status = SyncStatusManager.get_status()
            if current_status.get('status') == 'in_progress':
                logger.warning("⚠️ SYNC ALREADY RUNNING - Request rejected")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Sync is already in progress. Please wait for it to complete.'
                })
            
            # Initialize sync status immediately
            from .models import MemberData  # Import your models here
            active_members_count = MemberData.objects.filter(Active_status=True).count()
            SyncStatusManager.initialize_sync(active_members_count)
            
            # Start the bulk sync process in a separate thread
            def run_sync():
                try:
                    results = bulk_sync_all_members()
                    
                    # Store final results in cache for retrieval
                    cache.set('bulk_sync_final_results', results, timeout=3600)
                    logger.info("✅ SYNC THREAD COMPLETED SUCCESSFULLY")
                except Exception as e:
                    logger.error(f"❌ SYNC THREAD FAILED: {str(e)}")
                    SyncStatusManager.add_update(f"Critical error: {str(e)}", 'error')
                    # Mark as completed even if failed so UI can handle it
                    SyncStatusManager.complete_sync()
            
            sync_thread = threading.Thread(target=run_sync)
            sync_thread.daemon = True
            sync_thread.start()
            
            logger.info("🚀 SYNC THREAD STARTED")
            
            return JsonResponse({
                'status': 'started',
                'message': 'Bulk sync started successfully. Monitor progress via status endpoint.',
                'initial_count': active_members_count
            })
            
        except Exception as e:
            logger.error(f"❌ SYNC EXECUTION ERROR: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required(login_url='SignIn')
def bulk_sync_status(request):
    """
    AJAX endpoint to get current sync status
    """
    try:
        status = SyncStatusManager.get_status()
        recent_updates = SyncStatusManager.get_recent_updates(3)  # Get last 3 updates
        
        if status:
            response_data = {
                'status': status.get('status', 'unknown'),
                'data': {
                    'total': status.get('total', 0),
                    'processing': status.get('processing', 0),
                    'successful': status.get('successful', 0),
                    'failed': status.get('failed', 0),
                    'skipped': status.get('skipped', 0),
                    'current_member': status.get('current_member')
                },
                'recent_updates': recent_updates
            }
            
            # Add debug info
            logger.debug(f"Status check: {status.get('status')} - {status.get('successful', 0)}/{status.get('total', 0)}")
            
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'status': 'idle',
                'data': {
                    'total': 0,
                    'processing': 0,
                    'successful': 0,
                    'failed': 0,
                    'skipped': 0,
                    'current_member': None
                },
                'recent_updates': []
            })
    except Exception as e:
        logger.error(f"❌ STATUS CHECK ERROR: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'data': {},
            'recent_updates': [],
            'error': str(e)
        })

@login_required(login_url='SignIn')
def bulk_sync_results(request):
    """
    AJAX endpoint to get final sync results
    """
    try:
        results = cache.get('bulk_sync_final_results')
        if results:
            # Prepare response data similar to the old format
            response_data = {
                'status': 'success',
                'summary': {
                    'total_members': results['total_members'],
                    'successful': len(results['successful']),
                    'failed': len(results['failed']),
                    'skipped': len(results['skipped']),
                    'duration_seconds': round(results['duration'], 2)
                },
                'details': {
                    'successful_members': results['successful'][:20],  # Limit for response size
                    'failed_members': results['failed'][:20],
                    'skipped_members': results['skipped'][:20]
                }
            }
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'No results available'
            })
    except Exception as e:
        logger.error(f"❌ RESULTS FETCH ERROR: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@csrf_exempt
@login_required(login_url='SignIn')
def bulk_sync_stop(request):
    """
    AJAX endpoint to stop bulk sync
    """
    if request.method == 'POST':
        # Update status to stopped
        status = SyncStatusManager.get_status()
        status['status'] = 'stopped'
        cache.set(SYNC_STATUS_KEY, status, timeout=3600)
        
        logger.warning("🛑 BULK SYNC STOPPED BY USER REQUEST")
        SyncStatusManager.add_update("🛑 Sync stopped by user", 'warning')
        
        return JsonResponse({
            'status': 'success',
            'message': 'Sync stopped successfully'
        })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    })

@login_required(login_url='SignIn')
def test_device_connection(request):
    """
    Test connection to the access control device
    """
    logger.info("🔍 TESTING DEVICE CONNECTION")
    
    url = "http://192.168.70.31:8050/api_updateperson"
    headers = {
        'Host': 'emmyfitness-betainfotech.pythonanywhere.com',
        'Content-Type': 'application/json',
        'Content-Length': '0',  # Set to '0' for GET requests, calculate for POST/PUT requests
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Token': '7ee4e345d834feb:c3abbf46c8714cb'
    }
    
    # Send a minimal test request
    test_payload = {
        "BadgeNumber": "TEST",
        "Name": "Connection Test",
        "DeviceSerialNumber": "CQUH233560091"
    }
    
    try:
        response = requests.post(url, headers=headers, json=test_payload, timeout=10)
        
        if response.status_code in [200, 400]:  # 400 might be expected for test data
            logger.info("✅ DEVICE CONNECTION TEST SUCCESSFUL")
            return JsonResponse({
                'status': 'success',
                'message': f'Device responded with status {response.status_code}'
            })
        else:
            logger.warning(f"⚠️ DEVICE CONNECTION TEST FAILED: HTTP {response.status_code}")
            return JsonResponse({
                'status': 'warning',
                'message': f'Unexpected response: HTTP {response.status_code}'
            })
            
    except requests.exceptions.Timeout:
        logger.error("❌ DEVICE CONNECTION TEST TIMEOUT")
        return JsonResponse({
            'status': 'error',
            'message': 'Connection timeout - Device may be offline'
        })
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ DEVICE CONNECTION TEST FAILED: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Connection failed: {str(e)}'
        })

@login_required(login_url='SignIn')
def bulk_sync_status_page(request):
    """
    Page to show current sync status and statistics
    """
    from .models import MemberData, Subscription  # Import your models here
    
    stats = {
        'total_members': MemberData.objects.count(),
        'active_members': MemberData.objects.filter(Active_status=True).count(),
        'members_with_device_access': MemberData.objects.filter(Access_status=True).count(),
        'members_without_device_access': MemberData.objects.filter(Active_status=True, Access_status=False).count(),
        'expired_subscriptions': Subscription.objects.filter(
            Subscription_End_Date__lt=datetime.now().date(),
            Payment_Status=True
        ).count(),
        'active_subscriptions': Subscription.objects.filter(
            Subscription_End_Date__gte=datetime.now().date(),
            Payment_Status=True
        ).count()
    }
    
    # Get recent members without device access
    members_needing_sync = MemberData.objects.filter(
        Active_status=True, 
        Access_status=False
    )[:10]
    
    context = {
        'stats': stats,
        'members_needing_sync': members_needing_sync
    }
    
    return render(request, 'bulk_sync_status.html', context)


################################################################
################################################################
################################################################
################################################################
################################################################
################################################################
################################################################
################################################################
################################################################
################## Hik Connection essentials ##################


import requests
from django.shortcuts import render
from .hik_access_middle_contact import hik_connection_test, get_all_persons_from_device, add_person_to_hik_device, delete_user_from_device, disable_enable_person_form_hik, get_single_person_from_device
from Index.models import ConfigarationDB


def connection_test(request):
    # Use proper parameters here
    settings_conf = ConfigarationDB.objects.first()
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password

    print("Started connection -------------------------------------------------------------------")
    response = hik_connection_test(device_ip, username, password)

    if not response:
        # helper failed to call the endpoint
        context = {
            "success": False,
            "error": "Network error: failed to reach device endpoint.",
            "raw_text": None,
            "device_info": None,
            "user_check": None,
            "status_code": None,
        }
        return render(request, "test_connection/hik_connection.html", context)

    # At this point we have a requests.Response
    raw_text = response.text
    status_code = response.status_code
    device_info = None
    user_check = None
    error = None
    success = False

    try:
        data = response.json()
    except ValueError:
        data = None
        error = "Invalid JSON returned by the endpoint."

    if data:
        if "DeviceInfo" in data:
            device_info = data.get("DeviceInfo")
            success = True
        elif "userCheck" in data:
            user_check = data.get("userCheck")
            status_value = str(user_check.get("statusValue", "")).strip()
            status_string = str(user_check.get("statusString", "")).strip().lower()
            if status_value == "200" or status_string in ("ok", "success"):
                success = True
            else:
                success = False
                error = f"{user_check.get('statusString', 'Unknown error')} (statusValue={status_value})"
        else:
            error = "Unexpected JSON structure from endpoint."
    else:
        error = error or "Empty/invalid response."

    # Also treat non-2xx as failure by default (unless you purposely override)
    if status_code and not (200 <= status_code < 300):
        success = False
        if not error:
            error = f"HTTP {status_code}"

    context = {
        "success": success,
        "error": error,
        "raw_text": raw_text,
        "device_info": device_info,
        "user_check": user_check,
        "status_code": status_code,
    }
    return render(request, "test_connection/hik_connection.html", context)


import json
import logging
from django.shortcuts import render

logger = logging.getLogger(__name__)

def get_all_persons(request):
    # Use proper parameters here
    settings_conf = ConfigarationDB.objects.first()
    call_back = settings_conf.JWT_IP
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password

    # Call your helper which may return a requests.Response, a JSON string, or a list
    response = get_all_persons_from_device(call_back, device_ip, username, password)

    # If helper failed (None/False), show error
    if not response:
        logger.error("get_all_persons_from_device returned falsy value: %r", response)
        return render(request, "test_connection/all_persons.html", {
            "users": [],
            "raw_json": "ERROR: Could not connect to device.",
            "status": False
        })

    users = []
    raw_json_text = None

    # 1) If it's a requests.Response-like object: try .json()
    if hasattr(response, "json") and callable(response.json):
        try:
            data = response.json()
            raw_json_text = getattr(response, "text", None)
            logger.debug("Parsed JSON from Response object, type=%s", type(data))
        except ValueError:
            # response.text may contain JSON string or plain text
            raw_json_text = getattr(response, "text", None)
            logger.exception("response.json() failed. raw text: %s", raw_json_text)
            # try to parse text as JSON
            try:
                data = json.loads(raw_json_text) if raw_json_text else None
            except Exception:
                data = None

    # 2) If it's already a Python list/dict
    elif isinstance(response, list) or isinstance(response, dict):
        data = response
        try:
            raw_json_text = json.dumps(response, indent=2)
        except Exception:
            raw_json_text = str(response)

    # 3) If it's a JSON string
    elif isinstance(response, str):
        raw_json_text = response
        try:
            data = json.loads(response)
        except Exception:
            logger.exception("Failed to json.loads(response string). response: %s", response)
            data = None
    else:
        # unknown type
        logger.warning("Unknown response type from helper: %s", type(response))
        data = None
        try:
            raw_json_text = str(response)
        except Exception:
            raw_json_text = None

    # Now coerce data into a list of users
    if isinstance(data, list):
        users = data
    elif isinstance(data, dict):
        # common cases: the list might be under some key, try likely keys
        for k in ("users", "persons", "data", "result", "UserList", "PersonList"):
            if k in data and isinstance(data[k], list):
                users = data[k]
                break
        else:
            # not found — if the dict itself represents a single user, wrap it
            # (e.g. {"employeeNo":...})
            # We'll treat dict-as-single-user only if it contains employeeNo/name keys
            if any(key in data for key in ("employeeNo", "name", "employeeID", "id")):
                users = [data]
            else:
                users = []
    else:
        users = []

    # Safety: ensure users is a list of dicts
    if not isinstance(users, list):
        users = []

    # prepare raw_json for display
    if raw_json_text is None:
        try:
            raw_json_text = json.dumps(users, indent=2)
        except Exception:
            raw_json_text = str(users)

    context = {
        "users": users,
        "raw_json": raw_json_text,
        "status": True if users else False
    }
    return render(request, "test_connection/all_persons.html", context)


from datetime import datetime

def add_person(request):
    settings_conf = ConfigarationDB.objects.first()
    call_back = settings_conf.JWT_IP
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password

    if request.method == "POST":
        employeeNo = request.POST["employee_no"]
        name = request.POST["name"]
        gender = request.POST["gender"]
        began_time_raw =  request.POST["began_time"]
        end_time_raw =  request.POST["end_time"]

        try:
            # Parse the datetime-local format (2024-01-01T00:00)
            began_dt = datetime.strptime(began_time_raw, "%Y-%m-%dT%H:%M")
            end_dt = datetime.strptime(end_time_raw, "%Y-%m-%dT%H:%M")
            
            # Format to Hikvision format with seconds (2024-01-01T00:00:00)
            beginTime = began_dt.strftime("%Y-%m-%dT%H:%M:%S")
            endTime = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
            
            print(f"Converted beginTime: {beginTime}")
            print(f"Converted endTime: {endTime}")
            
        except ValueError as e:
            return JsonResponse({
                "status": "error",
                "message": f"Invalid datetime format: {e}"
            }, status=400)

        person_data = {
            "employeeNo": employeeNo,      # Required: Unique ID for the person
            "name": name,        # Required: Person's name
            "userType": "normal",      # Optional: normal, visitor, blacklist
            "gender": gender,          # Optional: male, female
            "enable": True,            # Optional: Enable/disable user
            "beginTime": beginTime,  # Start validity
            "endTime": endTime,    # End validity
            "doorRight": "1",          # Door access rights
            "RightPlan": [             # Access schedule
                {
                    "doorNo": 1,
                    "planTemplateNo": "1"
                }
            ]
        }
        try:
            # Example API call (replace with your actual implementation)
            response =  add_person_to_hik_device(call_back, device_ip, username, password,person_data)

            
            # Parse response
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
            
            # Check status code
            status_code = response_data.get('statusCode', 0)
            status_string = response_data.get('statusString', '')
            sub_status_code = response_data.get('subStatusCode', '')
            error_msg = response_data.get('errorMsg', '')
            
            # Handle different status codes
            if status_code == 1:  # Success
                messages.success(request, f'Member "{name}" added successfully!')
                return redirect('get_all_persons')  # Replace with your success redirect URL
            
            elif status_code == 6:  # Invalid Content
                if sub_status_code == 'employeeNoAlreadyExist':
                    error_message = f'Employee No "{employeeNo}" already exists. Please use a different employee number.'
                else:
                    error_message = f'{status_string}: {sub_status_code if sub_status_code else error_msg}'
                
                messages.error(request, error_message)
                return redirect('connection_test')
            
            else:  # Other errors
                error_message = f'{status_string} (Code: {status_code})'
                if sub_status_code:
                    error_message += f' - {sub_status_code}'
                if error_msg:
                    error_message += f' - {error_msg}'
                
                messages.error(request, error_message)
                return redirect('connection_test')
        
        except json.JSONDecodeError:
            messages.error(request, 'Invalid response from device. Please try again.')
            return redirect('connection_test')
        
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('connection_test')
    
    return redirect('connection_test')


def get_user_friendly_message(response_data):
    """
    Convert API response to user-friendly message
    """
    status_code = response_data.get('statusCode', 0)
    sub_status = response_data.get('subStatusCode', '')
    
    # Map common error codes to user-friendly messages
    error_messages = {
        'employeeNoAlreadyExist': 'This employee number is already registered in the system.',
        'nameAlreadyExist': 'This name is already registered in the system.',
        'invalidEmployeeNo': 'The employee number format is invalid.',
        'invalidTimeRange': 'The time range is invalid. End time must be after begin time.',
        'deviceBusy': 'The device is currently busy. Please try again in a moment.',
        'insufficientPermission': 'You do not have permission to perform this action.',
    }
    
    # Return mapped message or default
    if sub_status in error_messages:
        return error_messages[sub_status]
    
    # Default error message
    status_string = response_data.get('statusString', 'Unknown Error')
    return f'{status_string} ({sub_status if sub_status else "Error"})'


def delete_person_form_hik_device(request, employee_no):
    call_back = "127.0.0.1:8000"
    settings_conf = ConfigarationDB.objects.first()
    call_back = settings_conf.JWT_IP
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password

    try:
        # Example API call (replace with your actual implementation)
        response =  delete_user_from_device(call_back, device_ip, username, password,str(employee_no))

        # Parse response
        if isinstance(response, str):
            response_data = json.loads(response)
        else:
            response_data = response
        
        # Check status code
        status_code = response_data.get('statusCode', 0)
        status_string = response_data.get('statusString', '')
        sub_status_code = response_data.get('subStatusCode', '')
        error_msg = response_data.get('errorMsg', '')
        
        # Handle different status codes
        if status_code == 1:  # Success
            messages.success(request, f'Member Deleted successfully!')
            # return redirect('get_all_persons')  # Replace with your success redirect URL
            return redirect("MembersSingleView",pk = employee_no )
        
        elif status_code == 6:  # Invalid Content
            if sub_status_code == 'employeeNoAlreadyExist':
                error_message = f'Employee No already exists. Please use a different employee number.'
            else:
                error_message = f'{status_string}: {sub_status_code if sub_status_code else error_msg}'
            
            # messages.error(request, error_message)
            return redirect("MembersSingleView",pk = employee_no )

        
        else:  # Other errors
            error_message = f'{status_string} (Code: {status_code})'
            if sub_status_code:
                error_message += f' - {sub_status_code}'
            if error_msg:
                error_message += f' - {error_msg}'
            
            # messages.error(request, status_string)
            # return redirect('connection_test')
            return redirect("MembersSingleView",pk = employee_no )

    
    except json.JSONDecodeError:
        messages.error(request, 'Invalid response from device. Please try again.')
        # return redirect('connection_test')
        return redirect("MembersSingleView",pk = employee_no )

    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        # return redirect('connection_test')
        return redirect("MembersSingleView",pk = employee_no )


    

def disable_enable_user(request):
    settings_conf = ConfigarationDB.objects.first()
    call_back = settings_conf.JWT_IP
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password

    if request.method == "POST":
        employeeNo = request.POST["employee_no"]
        name = request.POST["name"]
        # gender = request.POST["gender"]
        began_time_raw =  request.POST["began_time"]
        end_time_raw =  request.POST["end_time"]
        userType = 'normal'
        is_active = True
        try:
            # Parse the datetime-local format (2024-01-01T00:00)
            began_dt = datetime.strptime(began_time_raw, "%Y-%m-%dT%H:%M")
            end_dt = datetime.strptime(end_time_raw, "%Y-%m-%dT%H:%M")
            
            # Format to Hikvision format with seconds (2024-01-01T00:00:00)
            beginTime = began_dt.strftime("%Y-%m-%dT%H:%M:%S")
            endTime = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
            
            print(f"Converted beginTime: {beginTime}")
            print(f"Converted endTime: {endTime}")
            
        except ValueError as e:
            return JsonResponse({
                "status": "error",
                "message": f"Invalid datetime format: {e}"
            }, status=400)

        person_data = {
            "employee_no": employeeNo,      # Required: Unique ID for the person
            "name": name,       # Required: Person's name
            "userType": userType,      # Optional: normal, visitor, blacklist
            # "gender": gender,          # Optional: male, female
            "is_valid": is_active,            # Optional: Enable/disable user
            "beginTime": beginTime,  # Start validity
            "endTime": endTime,    # End validity
            "doorRight": "1",          # Door access rights
            
            }
        try:
            # Example API call (replace with your actual implementation)
            response =  disable_enable_person_form_hik(call_back, device_ip, username, password,person_data)

            
            # Parse response
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
            
        
            print(response_data,"---------------------")
            # Check status code
            status_code = response_data.get('statusCode', 0)
            status_string = response_data.get('statusString', '')
            sub_status_code = response_data.get('subStatusCode', '')
            error_msg = response_data.get('errorMsg', '')
            
            # Handle different status codes
            if status_code == 1:  # Success
                messages.success(request, f'Member "{name}" disabled successfully!')
                return redirect('get_all_persons')  # Replace with your success redirect URL
            
            elif status_code == 6:  # Invalid Content
                if sub_status_code == 'employeeNoAlreadyExist':
                    error_message = f'Employee No "{employeeNo}" already exists. Please use a different employee number.'
                else:
                    error_message = f'{status_string}: {sub_status_code if sub_status_code else error_msg}'
                
                messages.error(request, error_message)
                return redirect('connection_test')
            
            else:  # Other errors
                error_message = f'{status_string} (Code: {status_code})'
                if sub_status_code:
                    error_message += f' - {sub_status_code}'
                if error_msg:
                    error_message += f' - {error_msg}'
                
                messages.error(request, error_message)
                return redirect('connection_test')
        
        except json.JSONDecodeError:
            messages.error(request, 'Invalid response from device. Please try again.')
            return redirect('connection_test')
        
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('connection_test')
    
    return redirect('connection_test') 




def BulkUserUpdate(request):
    subscription = Subscription.objects.all()[:100]
    settings_conf = ConfigarationDB.objects.first()
    call_back = settings_conf.JWT_IP
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password

    for subscrib in subscription:
        employeeNo = str(subscrib.Member.id)
        name = f'{subscrib.Member.First_Name} {subscrib.Member.Last_Name}'
        gender = subscrib.Member.Gender
        beginTime = subscrib.Subscribed_Date.strftime("%Y-%m-%d") + "T00:00:00"

        if subscrib.Subscription_End_Date:
            end_date = subscrib.Subscription_End_Date
        else:
            end_date = datetime.date.today()   # <-- Use today when empty

        endTime = end_date.strftime("%Y-%m-%d") + "T00:00:00"
        person_data = {
                "employeeNo": employeeNo,      # Required: Unique ID for the person
                "name": name,        # Required: Person's name
                "userType": "normal",      # Optional: normal, visitor, blacklist
                "gender": "female",          # Optional: male, female
                "enable": True,            # Optional: Enable/disable user
                "beginTime": beginTime,  # Start validity
                "endTime": endTime,    # End validity
                "doorRight": "1",          # Door access rights
                "RightPlan": [             # Access schedule
                    {
                        "doorNo": 1,
                        "planTemplateNo": "1"
                    }
                ]
            }
        try:
            # Example API call (replace with your actual implementation)
            response =  add_person_to_hik_device(call_back, device_ip, username, password,person_data)

            
            # Parse response
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
            
            # Check status code
            status_code = response_data.get('statusCode', 0)
            status_string = response_data.get('statusString', '')
            sub_status_code = response_data.get('subStatusCode', '')
            error_msg = response_data.get('errorMsg', '')
            
            # Handle different status codes
            if status_code == 1:  # Success
                messages.success(request, f'Member "{name}" added successfully!')
                print(f'Member "{name}" added successfully!')  # Replace with your success redirect URL
            
            elif status_code == 6:  # Invalid Content
                if sub_status_code == 'employeeNoAlreadyExist':
                    error_message = f'Employee No "{employeeNo}" already exists. Please use a different employee number.'
                else:
                    error_message = f'{status_string}: {sub_status_code if sub_status_code else error_msg}'
                
                messages.error(request, error_message)
                print(error_message)
            
            else:  # Other errors
                error_message = f'{status_string} (Code: {status_code})'
                if sub_status_code:
                    error_message += f' - {sub_status_code}'
                if error_msg:
                    error_message += f' - {error_msg}'
                
                messages.error(request, error_message)
                print(error_message)

        
        except json.JSONDecodeError:
            messages.error(request, 'Invalid response from device. Please try again.')
            print('Invalid response from device. Please try again.')

        
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            print(f'An error occurred: {str(e)}')
    return redirect("get_all_persons")


def get_person_data(request, employee_no):
    settings_conf = ConfigarationDB.objects.first()
    call_back = settings_conf.JWT_IP
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password
    try:
        response  = get_single_person_from_device(call_back, device_ip, username, password,employee_no)
    # Parse response
        if isinstance(response, str):
            response_data = json.loads(response)
            print(response_data)
        else:
            response_data = response
            print("-----------------",response_data)
        
        
    except json.JSONDecodeError:
        messages.error(request, 'Invalid response from device. Please try again.')
        print('Invalid response from device. Please try again.')

    
    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        print(f'An error occurred: {str(e)}')
    return render(request, "test_connection/persondata.html", {"person": response_data, "employee_no":employee_no })
################################################################
################################################################
################################################################
################################################################
################################################################
from django.shortcuts import get_object_or_404

from datetime import datetime, date, time
import json
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages

def add_person_to_device_hik(request, employee_id):
    memeber = get_object_or_404(MemberData, id=employee_id)

    # ---------- Subscription dates ----------
    try:
        subscription = get_object_or_404(Subscription, memeber=memeber)
        began_time = subscription.Subscribed_Date
        end_time = subscription.Subscription_End_Date
    except:
        began_time = "2024-01-01T00:00:00"
        end_time = "2024-01-02T00:00:00"

    # ---------- Device Configuration ----------
    settings_conf = ConfigarationDB.objects.first()
    call_back = settings_conf.JWT_IP
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password

    employeeNo = str(memeber.id)
    name = memeber.First_Name
    # gender = memeber.Gender
    raw_gender = memeber.Gender

# Normalize to hikvision format: male / female
    gender = str(raw_gender).strip().lower()

    # Optional mappings if your DB stores short forms
    if gender in ["m", "man", "male"]:
        gender = "male"
    elif gender in ["f", "woman", "female"]:
        gender = "female"
    else:
        gender = "male"   # sensible default or raise error

    # ---------- date parser ----------
    def parse_dt(value):
        # Already python date object
        if isinstance(value, date) and not isinstance(value, datetime):
            return datetime.combine(value, time.min)

        # Already python datetime
        if isinstance(value, datetime):
            return value

        # String formats
        for fmt in ("%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M",
                    "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                pass

        raise ValueError(f"Unsupported datetime format: {value}")

    # ---------- Convert to required Hikvision format ----------
    try:
        began_dt = parse_dt(began_time)
        end_dt = parse_dt(end_time)

        beginTime = began_dt.strftime("%Y-%m-%dT%H:%M:%S")
        endTime = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

    except ValueError as e:
        return JsonResponse({
            "status": "error",
            "message": f"Invalid datetime format: {e}"
        }, status=400)

    # ---------- Build person payload ----------
    person_data = {
        "employeeNo": employeeNo,
        "name": name,
        "userType": "normal",
        "gender": gender,
        "enable": True,
        "beginTime": beginTime,
        "endTime": endTime,
        "doorRight": "1",
        "RightPlan": [
            {
                "doorNo": 1,
                "planTemplateNo": "1"
            }
        ]
    }

    # ---------- Send to HIK device ----------
    try:
        response = add_person_to_hik_device(
            call_back,
            device_ip,
            username,
            password,
            person_data
        )

        # Normalize response
        if isinstance(response, str):
            response_data = json.loads(response)
        else:
            response_data = response

        status_code = response_data.get('statusCode', 0)
        status_string = response_data.get('statusString', '')
        sub_status_code = response_data.get('subStatusCode', '')
        error_msg = response_data.get('errorMsg', '')

        # ---------- Success ----------
        if status_code == 1:
            messages.success(request, f'Member "{name}" added successfully!')
            return redirect('MembersSingleView', pk=employee_id)

        # ---------- Employee exists ----------
        elif status_code == 6:
            if sub_status_code == 'employeeNoAlreadyExist':
                messages.error(
                    request,
                    f'Employee No "{employeeNo}" already exists on device.'
                )
            else:
                messages.error(
                    request,
                    f'{status_string}: {sub_status_code or error_msg}'
                )
            return redirect('MembersSingleView', pk=employee_id)

        # ---------- Other errors ----------
        else:
            error_message = f'{status_string} (Code: {status_code})'
            if sub_status_code:
                error_message += f' - {sub_status_code}'
            if error_msg:
                error_message += f' - {error_msg}'

            messages.error(request, error_message)
            return redirect('MembersSingleView', pk=employee_id)

    except json.JSONDecodeError:
        messages.error(request, 'Invalid response from device.')
        return redirect('MembersSingleView', pk=employee_id)

    except Exception as e:
        messages.error(request, f'An error occurred: {str(e)}')
        return redirect('MembersSingleView', pk=employee_id)




def disable_enable_user_(request):
    settings_conf = ConfigarationDB.objects.first()
    call_back = settings_conf.JWT_IP
    device_ip = settings_conf.Call_Back_IP
    username = settings_conf.Admin_Username
    password = settings_conf.Admin_Password

    if request.method == "POST":
        employeeNo = request.POST["employee_no"]
        name = request.POST["name"]
        # gender = request.POST["gender"]
        began_time_raw =  request.POST["began_time"]
        end_time_raw =  request.POST["end_time"]
        userType = 'normal'
        is_active = True
        try:
            # Parse the datetime-local format (2024-01-01T00:00)
            began_dt = datetime.strptime(began_time_raw, "%Y-%m-%dT%H:%M")
            end_dt = datetime.strptime(end_time_raw, "%Y-%m-%dT%H:%M")
            
            # Format to Hikvision format with seconds (2024-01-01T00:00:00)
            beginTime = began_dt.strftime("%Y-%m-%dT%H:%M:%S")
            endTime = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
            
            print(f"Converted beginTime: {beginTime}")
            print(f"Converted endTime: {endTime}")
            
        except ValueError as e:
            return JsonResponse({
                "status": "error",
                "message": f"Invalid datetime format: {e}"
            }, status=400)

        person_data = {
            "employee_no": employeeNo,      # Required: Unique ID for the person
            "name": name,       # Required: Person's name
            "userType": userType,      # Optional: normal, visitor, blacklist
            # "gender": gender,          # Optional: male, female
            "is_valid": is_active,            # Optional: Enable/disable user
            "beginTime": beginTime,  # Start validity
            "endTime": endTime,    # End validity
            "doorRight": "1",          # Door access rights
            
            }
        try:
            # Example API call (replace with your actual implementation)
            response =  disable_enable_person_form_hik(call_back, device_ip, username, password,person_data)

            
            # Parse response
            if isinstance(response, str):
                response_data = json.loads(response)
            else:
                response_data = response
            
            # Check status code
            status_code = response_data.get('statusCode', 0)
            status_string = response_data.get('statusString', '')
            sub_status_code = response_data.get('subStatusCode', '')
            error_msg = response_data.get('errorMsg', '')
            
            # Handle different status codes
            if status_code == 1:  # Success
                messages.success(request, f'Member "{name}" disabled successfully!')
                return redirect('get_all_persons')  # Replace with your success redirect URL
            
            elif status_code == 6:  # Invalid Content
                if sub_status_code == 'employeeNoAlreadyExist':
                    error_message = f'Employee No "{employeeNo}" already exists. Please use a different employee number.'
                else:
                    error_message = f'{status_string}: {sub_status_code if sub_status_code else error_msg}'
                
                messages.error(request, error_message)
                return redirect('connection_test')
            
            else:  # Other errors
                error_message = f'{status_string} (Code: {status_code})'
                if sub_status_code:
                    error_message += f' - {sub_status_code}'
                if error_msg:
                    error_message += f' - {error_msg}'
                
                messages.error(request, error_message)
                return redirect('connection_test')
        
        except json.JSONDecodeError:
            messages.error(request, 'Invalid response from device. Please try again.')
            return redirect('connection_test')
        
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('connection_test')
    
    return redirect('connection_test') 

################################################################
################################################################
################################################################
################################################################