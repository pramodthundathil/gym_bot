from django.shortcuts import render, redirect
from .forms import MemberAddForm, SubscriptionAddForm, PaymentForm
from .models import MemberData, Subscription, Payment, AccessToGate
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


this_month = timezone.now().month
today = timezone.now()
start_date = today + timedelta(days=-5)
end_date = today + timedelta(days=5)
resign_date = today +timedelta(days = -30)

notification_payments = Payment.objects.filter(Payment_Date__gte = start_date,Payment_Date__lte = today,Payment_Date = today )

def ScheduledTask():

    confdata = ConfigarationDB.objects.get(id = 1)

    # get jwt token on local host Ztehodevice 
    url = f'http://{confdata.JWT_IP}:{confdata.JWT_PORT}/jwt-api-token-auth/'
    print(url)
    header1 = {
        'Content-Type': 'application/json'
        }
    token = "nil"
    body = {
        "username": confdata.Admin_Username,
        "password": confdata.Admin_Password
    }
    json_payload = json.dumps(body)
    try:
        reponse = requests.post(url,headers = header1,data = json_payload)
        if response.status_code == 200:
            print('Request successful!')
            token_dict = json.load(response)
            token = token_dict['token']
            print(response.json())
        else:
            print("no connection")

    except:
        print("No connection")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'JWT {}'.format(token)
    }

    subscrib = Subscription.objects.filter(Subscription_End_Date__lte = end_date)
    for i in subscrib:
        i.Payment_Status = False
        i.save()
        # print("hrlloooooooooooo")
        access = AccessToGate.objects.get(Subscription = i)
        access.Status = False
        access.save() 

    acc = AccessToGate.objects.all()
    for i in acc:
        if i.Status == False:
            accessid = i.Member.Access_Token_Id
            url = f"http://{confdata.Call_Back_IP}:{confdata.Call_Back_Port}/personal/api/resigns/"
            print(url)
            data = {
                "employee":accessid,
                "disableatt":True,
                "resign_type":1,
                "resign_date":str(resign_date),
                "reason":"Payment Pending",
            }
            json_payload = json.dumps(data)
            try:
                respose = request.patch(url, hedders = headers, data = json_payload)
                if respose.status_code == 200:
                    print("Succeed...")
                else:
                    print("Failed.....")
            except:
                print("no connection")
        else:
            accessid = i.Member.Access_Token_Id
            url = f"http://{confdata.Call_Back_IP}:{confdata.Call_Back_Port}/personal/api/resigns/reinstatement/"
            print(url)
            data = {
                "resigns":[accessid]
            }
            json_payload = json.dumps(data)
            try:
                respose = request.patch(url, hedders = headers, data = json_payload)
                if respose.status_code == 200:
                    print("Succeed...")
                else:
                    print("Failed.....")
            except:
                print("no connection")

    
    print("workinggggg.....")

            

    
    

# member configarations and subscription add on same method 
# one forign key field is prent in subscription Meber forign key, priod forign key, Batch forgin key
#
def Member(request):
    form = MemberAddForm()
    sub_form = SubscriptionAddForm()
    Trainee = MemberData.objects.all()[:8][::-1]
    subscribers = Subscription.objects.all()[:8][::-1]
    notification_payments = Payment.objects.filter(Payment_Date__gte = start_date,Payment_Date__lte = today )


    if request.method == "POST":
        form = MemberAddForm(request.POST,request.FILES)
        sub_form = SubscriptionAddForm(request.POST)
        if form.is_valid():
            member = form.save()
            member.save()
        else:
            messages.error(request,"Entered Personal Data is Not Validated Please try agine")
            return redirect("Member")
        if sub_form.is_valid():
            sub_data = sub_form.save()
            sub_data.save()
            sub_data.Member = member
            sub_data.save()
            access_gate = AccessToGate.objects.create(Member = member,Subscription = sub_data,Validity_Date = sub_data.Subscription_End_Date )
            access_gate.save()
            messages.success(request,"New Member Was Added Successfully Please Make Payment")
            return redirect("Member") 
        else:    
            messages.error(request,"Entered Subscription Data is Not Validated Please try agine")
            return redirect("Member") 

         
    context = {
        "notification_payments":notification_payments,
        "form":form,
        "sub_form":sub_form,
        "Trainee":Trainee,
        "subscribers":subscribers

        }
    return render(request,"members.html",context)

def MembersSingleView(request,pk):
    member = MemberData.objects.get(id = pk)
    subscription = Subscription.objects.get(Member = member)
    access = AccessToGate.objects.get(Member = member)
    sub_form = SubscriptionAddForm()
    ScheduledTask()

    context = {
        "member":member,
        "subscription":subscription,
        'sub_form':sub_form,
        "access":access,
        "notification_payments":notification_payments

    }
    return render(request,"memberssingleview.html",context)

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
    

def UpdateAccessToken(request,pk):
    if request.method == "POST":
        newtoken = request.POST['newtkn']
        member = MemberData.objects.get(id=pk)
        member.Access_Token_Id = newtoken
        member.save()
        messages.info(request,"Token Changed")
        return redirect("MembersSingleView",pk)

    return redirect("MembersSingleView",pk)

def DeleteMember(request,pk):
    member = MemberData.objects.get(id=pk)
    member.Photo.delete()
    member.delete()
    messages.error(request,"Member Data Deleted Success")
    return redirect("Member")

def MemberAccess(request):
    return render(request,"memberaccess.html")



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
        
            
def Payments(request):
    form = PaymentForm()
    pay = Payment.objects.all()[:8][::-1]
    sub_today = Subscription.objects.filter(Subscription_End_Date = today,Payment_Status = False)[:8][::-1]
    sub_past = Subscription.objects.filter(Subscription_End_Date__lte = today,Payment_Status = False)[:8][::-1]
    sub_Upcoming = Subscription.objects.filter(Subscription_End_Date__gte = today,Subscription_End_Date__lte = end_date, Payment_Status = False)[:8][::-1]

    
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
            ScheduledTask()
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
        "sub_Upcoming":sub_Upcoming
    }
    return render(request, "payments.html",context)

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
        ScheduledTask()
        messages.success(request,"Payment Updated for member {}".format(user))
        return redirect("MembersSingleView",pk)

    context ={
        "member":member
    }
    # messages.success(request, "Payment Added")
    return render(request,"paymentaddsingle.html",context)

# creating receipt for payment 

def ReceiptGenerate(request,pk):
    template_path = "receipt.html"
    context = {
        'myvar':"this is your template content"
    }
    response = HttpResponse(content_type = "application/pdf")
    response['Content-Disposition'] = 'attachment; filename="payment_receipt.pdf"'
    template = get_template(template_path)
    html = template.render(context)

    # create PDF
    pisa_status = pisa.CreatePDF(html, dest = response)
    if pisa_status.err:
        return HttpResponse("we are some erros <pre>" + html + '</pre>')
    return response

def DeletePayment(request,pk):
    Pay = Payment.objects.get(id = pk).delete()
    messages.info(request,"Payment Deleted")
    return redirect("Payments")

def ExtendAccessToGate(request,pk):
    member = MemberData.objects.get(id = pk)
    subscrib = Subscription.objects.get(Member = member)
    if request.method == "POST":
        extention = request.POST['exend']
        access = AccessToGate.objects.get(Member = member)
        access.Validity_Date = extention
        access.Status = True
        access.save()
        subscrib.Subscription_End_Date = extention
        subscrib.save()
        messages.success(request, "Access Granded Till {}".format(extention))
        return redirect(MembersSingleView, pk)
    context = {
        "member":member,
        "notification_payments":notification_payments
    }  
    return render(request,"grandaccessforgate.html",context)

def BlockAccess(request,pk):
    member = MemberData.objects.get(id = pk)
    access = AccessToGate.objects.get(Member = member)
    access.Status = False
    access.save()
    messages.success(request,"Access Status Changed....")
    return redirect(MembersSingleView,pk)

def AllMembers(request):
    members = MemberData.objects.all()[::-1]
    return render(request, "allmembers.html",{"member":members})

def AllPayments(request):
    payments = Payment.objects.all()[::-1]
    return render(request,"allpayments.html",{"payments":payments})


# Reports generation

def FullMemberReport(request):
    
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=Memberreportfull{}-{}.csv'.format(date,date_year)
    
    member = MemberData.objects.all().order_by("-Date_Added")
    
    writer = csv.writer(response)
    writer.writerow(['First_Name',"Last_Name","Date_Of_Birth","Gender","Mobile_Number","Email","Address","Medical_History","Registration_Date","Date_Added","Access_Token"])
    for i in member:
        writer.writerow([i.First_Name,i.Last_Name,i.Date_Of_Birth,i.Gender,i.Mobile_Number,i.Email,i.Address,i.Medical_History,i.Registration_Date,i.Date_Added,i.Access_Token_Id])

    return response


def MonthMemberReport(request):
    
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=Memberreportmonth{}-{}.csv'.format(date,date_year)
    
    member = MemberData.objects.filter(Date_Added__month = date).order_by("-Date_Added")
    
    writer = csv.writer(response)
    writer.writerow(['First_Name',"Last_Name","Date_Of_Birth","Gender","Mobile_Number","Email","Address","Medical_History","Registration_Date","Date_Added","Access_Token"])
    for i in member:
        writer.writerow([i.First_Name,i.Last_Name,i.Date_Of_Birth,i.Gender,i.Mobile_Number,i.Email,i.Address,i.Medical_History,i.Registration_Date,i.Date_Added,i.Access_Token_Id])

    return response

def DateWiseMemberReport(request):
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=MemberreportDate{}-{}.csv'.format(date,date_year)
    if request.method == "POST":
        sdate = request.POST["sdate"]
        edate = request.POST["enddate"]
        
    
    member = MemberData.objects.filter(Date_Added__gte = sdate,Date_Added__lte = edate ).order_by("-Date_Added")
    
    writer = csv.writer(response)
    writer.writerow(['First_Name',"Last_Name","Date_Of_Birth","Gender","Mobile_Number","Email","Address","Medical_History","Registration_Date","Date_Added","Access_Token"])
    for i in member:
        writer.writerow([i.First_Name,i.Last_Name,i.Date_Of_Birth,i.Gender,i.Mobile_Number,i.Email,i.Address,i.Medical_History,i.Registration_Date,i.Date_Added,i.Access_Token_Id])

    return response


def DateWisePaymentReport(request):
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=paymentreportDate{}-{}.csv'.format(date,date_year)
    if request.method == "POST":
        sdate = request.POST["sdate"]
        edate = request.POST["enddate"]
        
    
        payment = Payment.objects.filter(Payment_Date__gte = sdate,Payment_Date__lte = edate ).order_by("-Payment_Date")
        
        writer = csv.writer(response)
        writer.writerow(["Member","Subscription_ID","Amount","Payment_Date"])
        for i in payment:
            writer.writerow([i.Member,i.Subscription_ID,i.Amount,i.Payment_Date])

        return response
    return HttpResponse("No Valid Fiels")
    

def PaymentReport(request):
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=paymentreportfull{}-{}.csv'.format(date,date_year)
    
        
    try:
        payment = Payment.objects.all().order_by("-Payment_Date")
        
        writer = csv.writer(response)
        writer.writerow(["Member","Subscription_ID","Amount","Payment_Date"])
        for i in payment:
            writer.writerow([i.Member,i.Subscription_ID,i.Amount,i.Payment_Date])

        return response
    except:
        return HttpResponse("No Valid Fiels")
    

def PaymentReportMonth(request):
    date = timezone.now().month
    date_year = timezone.now().year
    response = HttpResponse(content_type = 'text/csv')
    response['Content-Disposition'] = 'attachment; filename=paymentreportmonth{}-{}.csv'.format(date,date_year)
    
        
    try:
        payment = Payment.objects.filter(Payment_Date__month = date ).order_by("-Payment_Date")
        
        writer = csv.writer(response)
        writer.writerow(["Member","Subscription_ID","Amount","Payment_Date"])
        for i in payment:
            writer.writerow([i.Member,i.Subscription_ID,i.Amount,i.Payment_Date])

        return response
    except:
        return HttpResponse("No Valid Fiels")






    


