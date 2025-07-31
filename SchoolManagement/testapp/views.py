from django.shortcuts import render

def testview(request):
    return render(request, 'public/home.html')  # Assure-toi que le fichier s'appelle bien home.html
