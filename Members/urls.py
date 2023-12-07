from django.urls import path 
from .import views 

urlpatterns = [
    path("Member",views.Member,name="Member"),
    path("Payments",views.Payments,name="Payments"),
    path("MembersSingleView/<int:pk>",views.MembersSingleView,name="MembersSingleView"),
    path("MemberAccess",views.MemberAccess,name="MemberAccess"),
    path("DeletePayment/<int:pk>",views.DeletePayment,name="DeletePayment"),
    path("DeleteMember/<int:pk>",views.DeleteMember,name="DeleteMember"),
    path("UpdateMember/<int:pk>",views.UpdateMember,name="UpdateMember"),
    path("UpdateAccessToken/<int:pk>",views.UpdateAccessToken,name="UpdateAccessToken"),
    path("ChangeSubscription/<int:pk>",views.ChangeSubscription,name="ChangeSubscription"),
    path("ExtendAccessToGate/<int:pk>",views.ExtendAccessToGate,name="ExtendAccessToGate"),
    path("BlockAccess/<int:pk>",views.BlockAccess,name="BlockAccess"),
    path("ProfilephotoUpdate/<int:pk>",views.ProfilephotoUpdate,name="ProfilephotoUpdate"),
    path("AllMembers",views.AllMembers,name="AllMembers"),
    path("AllPayments",views.AllPayments,name="AllPayments"),
    
    
    path("FullMemberReport",views.FullMemberReport,name="FullMemberReport"),
    path("MonthMemberReport",views.MonthMemberReport,name="MonthMemberReport"),
    path("DateWiseMemberReport",views.DateWiseMemberReport,name="DateWiseMemberReport"),
    path("DateWisePaymentReport",views.DateWisePaymentReport,name="DateWisePaymentReport"),
    path("PaymentReport",views.PaymentReport,name="PaymentReport"),
    path("PaymentReportMonth",views.PaymentReportMonth,name="PaymentReportMonth"),

    
]
