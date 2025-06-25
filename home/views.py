from django.shortcuts import render

# Create your views here.
def homeView(request):
    return render(request, 'home/home.html')

from django.shortcuts import render

def etapa_3_view(request):
    return render(request, 'home/etapa3.html')  # o la ruta correcta a tu template

def etapa4_view(request):
    return render(request, 'home/etapa4.html')

