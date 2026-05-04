from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Alerta


@login_required(login_url='usuarios:login')
def lista_alertas(request):
    alertas = Alerta.objects.filter(paciente=request.user)
    no_leidas = alertas.filter(leida=False).count()
    return render(request, 'alertas/lista.html', {
        'alertas': alertas,
        'no_leidas': no_leidas,
    })


@login_required(login_url='usuarios:login')
@require_POST
def marcar_leida(request, pk):
    alerta = get_object_or_404(Alerta, pk=pk, paciente=request.user)
    alerta.leida = True
    alerta.save()
    return JsonResponse({'ok': True})


@login_required(login_url='usuarios:login')
@require_POST
def marcar_todas_leidas(request):
    Alerta.objects.filter(paciente=request.user, leida=False).update(leida=True)
    return JsonResponse({'ok': True})


@login_required(login_url='usuarios:login')
def api_alertas_count(request):
    count = Alerta.objects.filter(paciente=request.user, leida=False).count()
    return JsonResponse({'count': count})
