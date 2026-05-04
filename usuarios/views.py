from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Usuario
from .serializers import UsuarioSerializer
from .forms import RegistroForm


def get_client_ip(request):
    """Obtener IP del cliente."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ============= VISTAS HTML =============

def index_view(request):
    """Página de inicio."""
    if request.user.is_authenticated:
        return redirect('usuarios:dashboard')
    return redirect('usuarios:login')


def login_view(request):
    """Login de usuario."""
    if request.method == 'POST':
        correo = request.POST.get('correo')
        password = request.POST.get('password')
        
        try:
            # Buscar usuario por correo
            usuario = Usuario.objects.get(correo=correo)
            
            # Verificar contraseña
            if usuario.check_password(password):
                login(request, usuario)
                
                # Registrar acceso exitoso
                try:
                    from clinico.models import HistorialAccesos
                    HistorialAccesos.objects.create(
                        id_usuario=usuario,
                        accion='login_ok',
                        ip=get_client_ip(request)
                    )
                except:
                    pass
                
                return redirect('usuarios:dashboard')
            else:
                # Contraseña incorrecta
                try:
                    from clinico.models import HistorialAccesos
                    HistorialAccesos.objects.create(
                        id_usuario=usuario,
                        accion='login_fail',
                        ip=get_client_ip(request)
                    )
                except:
                    pass
                
                return render(request, 'auth/login.html', 
                             {'error': 'Correo o contraseña incorrectos'})
        except Usuario.DoesNotExist:
            return render(request, 'auth/login.html',
                         {'error': 'Correo o contraseña incorrectos'})
    
    return render(request, 'auth/login.html')


def logout_view(request):
    """Logout de usuario."""
    try:
        from clinico.models import HistorialAccesos
        HistorialAccesos.objects.create(
            id_usuario=request.user,
            accion='logout',
            ip=get_client_ip(request)
        )
    except:
        pass
    
    logout(request)
    return redirect('usuarios:index')


def registro_view(request):
    """Registro de nuevo usuario."""
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            login(request, usuario)
            return redirect('usuarios:dashboard')
        else:
            return render(request, 'auth/registro.html', {'form': form})
    else:
        form = RegistroForm()
    
    return render(request, 'auth/registro.html', {'form': form})


@login_required(login_url='usuarios:login')
def dashboard_view(request):
    """Panel principal del usuario."""
    from clinico.models import DatosClinico
    from prediccion.models import Prediccion
    from alertas.models import Alerta

    es_admin = request.user.rol == 'administrador'

    context = {
        'usuario': request.user,
        'es_admin': es_admin,
    }

    if es_admin:
        context.update({
            'total_pacientes': Usuario.objects.filter(rol='paciente', activo=True).count(),
            'total_registros': DatosClinico.objects.count(),
            'total_predicciones': Prediccion.objects.count(),
            'alertas_pendientes': Alerta.objects.filter(leida=False).count(),
            'ultimos_registros': DatosClinico.objects.select_related('paciente').order_by('-fecha_registro')[:10],
        })
    else:
        ultimo_registro = DatosClinico.objects.filter(paciente=request.user).first()
        ultima_prediccion = Prediccion.objects.filter(paciente=request.user).first()
        alertas_no_leidas = Alerta.objects.filter(paciente=request.user, leida=False).count()
        total_registros = DatosClinico.objects.filter(paciente=request.user).count()

        context.update({
            'ultimo_registro': ultimo_registro,
            'ultima_prediccion': ultima_prediccion,
            'alertas_no_leidas': alertas_no_leidas,
            'total_registros': total_registros,
        })

    return render(request, 'dashboard/index.html', context)


# ============= VISTAS API REST =============

@api_view(['GET'])
def obtener_perfil(request):
    """API: Obtener perfil del usuario actual."""
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data)