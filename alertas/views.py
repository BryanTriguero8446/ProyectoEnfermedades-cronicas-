from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Alerta


def _alertas_qs(user):
    """Querysey de alertas según el rol del usuario."""
    if user.rol == 'administrador':
        # Admins ven sus propias alertas + altas y bajas de usuarios
        return Alerta.objects.filter(
            Q(paciente=user) | Q(tipo='nuevo_usuario') | Q(tipo='cuenta_eliminada')
        ).distinct().select_related('paciente')
    return Alerta.objects.filter(paciente=user)


@login_required(login_url='usuarios:login')
def lista_alertas(request):
    alertas = _alertas_qs(request.user)
    no_leidas = alertas.filter(leida=False).count()
    return render(request, 'alertas/lista.html', {
        'alertas': alertas,
        'no_leidas': no_leidas,
        'es_admin': request.user.rol == 'administrador',
    })


@login_required(login_url='usuarios:login')
@require_POST
def marcar_leida(request, pk):
    if request.user.rol == 'administrador':
        alerta = get_object_or_404(Alerta, pk=pk)
    else:
        alerta = get_object_or_404(Alerta, pk=pk, paciente=request.user)
    alerta.leida = True
    alerta.save()
    return JsonResponse({'ok': True})


@login_required(login_url='usuarios:login')
@require_POST
def marcar_todas_leidas(request):
    _alertas_qs(request.user).filter(leida=False).update(leida=True)
    return JsonResponse({'ok': True})


@login_required(login_url='usuarios:login')
def api_alertas_count(request):
    count = _alertas_qs(request.user).filter(leida=False).count()
    return JsonResponse({'count': count})


# ═══════════════════════════════════════════════════════════════════════════
# API REST — Nuevos registros de usuarios (solo administradores)
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_nuevos_usuarios(request):
    """
    Devuelve alertas de tipo 'nuevo_usuario' generadas desde la marca de agua
    indicada. Solo accesible por administradores.

    Autenticación: Cookie de sesión Django (dashboard) o Bearer JWT.

    Query params:
      desde  — ISO 8601 datetime (ej. 2026-05-27T10:00:00Z). Solo se devuelven
               alertas posteriores a este instante. Si se omite, se devuelven
               las 20 más recientes.

    Respuesta 200:
    {
        "count": 2,
        "alertas": [
            {
                "pk": 5,
                "mensaje": "Nuevo usuario registrado: Ana López",
                "paciente_nombre": "Ana López",
                "fecha": "2026-05-27T10:15:32.123456+00:00",
                "leida": false
            },
            ...
        ],
        "server_time": "2026-05-27T10:30:00.000000+00:00"
    }

    Errores:
      403 — El usuario autenticado no tiene rol de administrador.
    """
    if request.user.rol != 'administrador':
        return Response(
            {'error': 'Acceso denegado. Este endpoint es exclusivo para administradores.'},
            status=status.HTTP_403_FORBIDDEN
        )

    qs = Alerta.objects.filter(tipo='nuevo_usuario').select_related('paciente')

    desde_str = request.query_params.get('desde', '').strip()
    if desde_str:
        desde_dt = parse_datetime(desde_str)
        if desde_dt:
            qs = qs.filter(fecha_creacion__gt=desde_dt)
        else:
            return Response(
                {'error': "Parámetro 'desde' inválido. Usa formato ISO 8601."},
                status=status.HTTP_400_BAD_REQUEST
            )
    else:
        # Sin marca de agua: últimas 20 alertas
        qs = qs[:20]

    alertas_data = [
        {
            'pk':             a.pk,
            'mensaje':        a.mensaje,
            'paciente_nombre': (
                f"{a.paciente.nombre} {a.paciente.apellido}"
                if a.paciente else '—'
            ),
            'fecha':  a.fecha_creacion.isoformat(),
            'leida':  a.leida,
        }
        for a in qs
    ]

    return Response({
        'count':       len(alertas_data),
        'alertas':     alertas_data,
        'server_time': timezone.now().isoformat(),
    }, status=status.HTTP_200_OK)
