# store/admin.py
from django.contrib import admin
from .models import Book, UserBook
# Register your models here.

# This tells the Admin panel to display these tables
admin.site.register(Book)
admin.site.register(UserBook)


