# Generated by Django 4.2.7 on 2023-12-14 15:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Index', '0002_auto_20231208_0456'),
    ]

    operations = [
        migrations.CreateModel(
            name='Logo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('logo', models.FileField(upload_to='logo')),
            ],
        ),
    ]
