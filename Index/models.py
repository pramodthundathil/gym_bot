from django.db import models

# Create your models here.


class ConfigarationDB(models.Model):
    JWT_IP = models.CharField(max_length=255)
    JWT_PORT = models.CharField(max_length=11)
    Call_Back_IP = models.CharField(max_length=255)
    Call_Back_Port = models.CharField(max_length=11)
    Admin_Username = models.CharField(max_length=255)
    Admin_Password = models.CharField(max_length=255) 
