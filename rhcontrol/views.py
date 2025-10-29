from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.

def dashboard(request):
    return render(request, 'dashboard/pages/dashboard.html')

def employees(request):
    return render(request, 'dashboard/pages/employee-list.html')