import json
import random
import string
from datetime import timedelta
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Usuario
from .serializers import UsuarioSerializer
from .forms import RegistroForm


def _generar_codigo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _enviar_codigo_verificacion(user):
    codigo = _generar_codigo()
    user.codigo_verificacion = codigo
    user.codigo_verificacion_expira = timezone.now() + timedelta(hours=24)
    user.save(update_fields=['codigo_verificacion', 'codigo_verificacion_expira'])
    send_mail(
        subject='Tu código de verificación - ClinicalLens',
        message=(
            f"Hola {user.nombre},\n\n"
            f"Tu código de verificación es:\n\n"
            f"        {codigo}\n\n"
            f"Ingresa este código en la aplicación para activar tu cuenta.\n"
            f"El código es válido por 24 horas.\n\n"
            f"Si no creaste esta cuenta, ignora este mensaje.\n\n"
            f"— Equipo ClinicalLens"
        ),
        from_email=django_settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.correo],
        fail_silently=False,
    )


def _crear_alerta_nuevo_usuario(new_user):
    """Crea una alerta de tipo 'nuevo_usuario' visible para todos los admins."""
    from alertas.models import Alerta
    Alerta.objects.create(
        paciente=new_user,
        tipo='nuevo_usuario',
        severidad='info',
        mensaje=(
            f"Nuevo usuario registrado: {new_user.nombre} {new_user.apellido} "
            f"({new_user.correo})"
        ),
    )


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
            usuario = Usuario.objects.get(correo=correo)

            if usuario.check_password(password):
                # Cuenta no verificada → bloquear y ofrecer reenvío
                if not usuario.email_verificado:
                    return render(request, 'auth/login.html', {
                        'error_verificacion': True,
                        'correo_pendiente': correo,
                    })

                login(request, usuario)
                try:
                    from clinico.models import HistorialAccesos
                    HistorialAccesos.objects.create(
                        id_usuario=usuario,
                        accion='login_ok',
                        ip=get_client_ip(request)
                    )
                except Exception:
                    pass
                return redirect('usuarios:dashboard')
            else:
                try:
                    from clinico.models import HistorialAccesos
                    HistorialAccesos.objects.create(
                        id_usuario=usuario,
                        accion='login_fail',
                        ip=get_client_ip(request)
                    )
                except Exception:
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
    return redirect('usuarios:login')


def registro_view(request):
    """Registro de nuevo usuario con verificación de correo."""
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            usuario.email_verificado = False   # pendiente de verificación
            usuario.save()

            # Guardar sexo en PerfilPaciente
            sexo = form.cleaned_data.get('sexo', '')
            if sexo:
                from pacientes.models import PerfilPaciente
                perfil, _ = PerfilPaciente.objects.get_or_create(usuario=usuario)
                perfil.sexo = sexo
                perfil.save()

            # Crear alerta para administradores
            _crear_alerta_nuevo_usuario(usuario)

            # Enviar código de verificación
            _enviar_codigo_verificacion(usuario)

            request.session['correo_verificacion'] = usuario.correo
            return redirect('usuarios:verificacion_enviada')
        else:
            return render(request, 'auth/registro.html', {'form': form})
    else:
        form = RegistroForm()

    return render(request, 'auth/registro.html', {'form': form})


def verificacion_enviada_view(request):
    """Formulario de ingreso del código de verificación."""
    correo = request.session.get('correo_verificacion')
    if not correo:
        return redirect('usuarios:login')

    error = None
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip().upper()
        try:
            usuario = Usuario.objects.get(correo=correo, email_verificado=False)
            ahora = timezone.now()
            if (usuario.codigo_verificacion == codigo and
                    usuario.codigo_verificacion_expira and
                    ahora < usuario.codigo_verificacion_expira):
                usuario.email_verificado = True
                usuario.codigo_verificacion = ''
                usuario.save(update_fields=['email_verificado', 'codigo_verificacion'])
                request.session.pop('correo_verificacion', None)
                return render(request, 'auth/verificacion_ok.html', {'usuario': usuario})
            else:
                error = 'Código incorrecto o expirado. Revisa tu correo e intenta de nuevo.'
        except Usuario.DoesNotExist:
            error = 'No se encontró la cuenta asociada a este correo.'

    return render(request, 'auth/verificacion_enviada.html', {
        'correo': correo,
        'error': error,
    })


def reenviar_verificacion_view(request):
    """Genera un nuevo código y lo reenvía al correo."""
    if request.method == 'POST':
        correo = request.POST.get('correo', '').strip()
        try:
            usuario = Usuario.objects.get(correo=correo, email_verificado=False)
            _enviar_codigo_verificacion(usuario)
            request.session['correo_verificacion'] = correo
        except Usuario.DoesNotExist:
            pass
    return redirect('usuarios:verificacion_enviada')


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


@login_required(login_url='usuarios:login')
def estadisticas_view(request):
    """Estadísticas de diagnósticos — solo administradores."""
    if request.user.rol != 'administrador':
        return redirect('usuarios:dashboard')

    from prediccion.models import Prediccion

    predicciones = Prediccion.objects.select_related(
        'datos_clinicos', 'paciente'
    ).prefetch_related('paciente__perfil').all()

    ENFERMEDADES = [
        ('diabetes',     'Diabetes Tipo 2',       '#EF4444'),
        ('hipertension', 'Hipertensión Arterial',  '#F97316'),
        ('renal',        'Enf. Renal Crónica',     '#8B5CF6'),
        ('nafld',        'Hígado Graso (NAFLD)',   '#10B981'),
        ('cardiaco',     'Insuf. Cardíaca',         '#DC2626'),
    ]

    def grupo_edad(edad):
        if edad is None:
            return None
        if edad <= 12:  return 'Niño'
        if edad <= 30:  return 'Joven'
        if edad <= 60:  return 'Adulto'
        return 'Viejo'

    total = predicciones.count()

    # ── Top enfermedades ─────────────────────────────────────────────────────
    top_enf = []
    for campo, label, color in ENFERMEDADES:
        alto  = predicciones.filter(**{f'nivel_{campo}': 'alto'}).count()
        medio = predicciones.filter(**{f'nivel_{campo}': 'medio'}).count()
        bajo  = predicciones.filter(**{f'nivel_{campo}': 'bajo'}).count()
        top_enf.append({
            'campo': campo, 'label': label, 'color': color,
            'alto': alto, 'medio': medio, 'bajo': bajo,
        })
    top_enf.sort(key=lambda x: x['alto'], reverse=True)

    # ── Por sexo ─────────────────────────────────────────────────────────────
    por_sexo = {
        'M': {c: {'alto': 0, 'medio': 0, 'bajo': 0} for c, _, _ in ENFERMEDADES},
        'F': {c: {'alto': 0, 'medio': 0, 'bajo': 0} for c, _, _ in ENFERMEDADES},
        '?': {c: {'alto': 0, 'medio': 0, 'bajo': 0} for c, _, _ in ENFERMEDADES},
    }
    for p in predicciones:
        try:
            sexo = p.paciente.perfil.sexo or '?'
            if sexo not in por_sexo:
                sexo = '?'
        except Exception:
            sexo = '?'
        for campo, _, _ in ENFERMEDADES:
            nivel = getattr(p, f'nivel_{campo}', 'bajo')
            por_sexo[sexo][campo][nivel] += 1

    # ── Por grupo de edad ────────────────────────────────────────────────────
    GRUPOS = ['Niño', 'Joven', 'Adulto', 'Viejo']
    por_edad = {g: {c: {'alto': 0, 'medio': 0, 'bajo': 0} for c, _, _ in ENFERMEDADES}
                for g in GRUPOS}
    for p in predicciones:
        edad  = p.datos_clinicos.edad if p.datos_clinicos else None
        grupo = grupo_edad(edad)
        if grupo is None:
            continue
        for campo, _, _ in ENFERMEDADES:
            nivel = getattr(p, f'nivel_{campo}', 'bajo')
            por_edad[grupo][campo][nivel] += 1

    total_pacientes = predicciones.values('paciente').distinct().count()

    context = {
        'top_enf':          top_enf,
        'top_enf_json':     json.dumps(top_enf),
        'por_sexo_json':    json.dumps(por_sexo),
        'por_edad_json':    json.dumps(por_edad),
        'enfermedades':     ENFERMEDADES,
        'grupos':           GRUPOS,
        'total_predicciones': total,
        'total_pacientes':  total_pacientes,
    }
    return render(request, 'admin/estadisticas.html', context)


@login_required(login_url='usuarios:login')
def eliminar_cuenta_view(request):
    """
    Permite al usuario eliminar su propia cuenta.
    Requiere confirmación con contraseña actual.
    """
    if request.method == 'POST':
        password = request.POST.get('password', '')
        confirmar = request.POST.get('confirmar', '')

        if confirmar != 'ELIMINAR':
            messages.error(request, 'Debes escribir ELIMINAR para confirmar.')
            return render(request, 'auth/eliminar_cuenta.html')

        if not request.user.check_password(password):
            messages.error(request, 'La contraseña es incorrecta.')
            return render(request, 'auth/eliminar_cuenta.html')

        # Desactivar cuenta (soft delete) en lugar de borrar permanentemente
        usuario = request.user
        usuario.activo = False
        usuario.is_active = False
        usuario.save(update_fields=['activo', 'is_active'])

        # Registrar acción en historial
        try:
            from clinico.models import HistorialAccesos
            HistorialAccesos.objects.create(
                id_usuario=usuario,
                accion='cuenta_eliminada',
                ip=get_client_ip(request)
            )
        except Exception:
            pass

        logout(request)
        messages.success(request, 'Tu cuenta ha sido eliminada exitosamente.')
        return redirect('usuarios:login')

    return render(request, 'auth/eliminar_cuenta.html')


# ============= VISTAS API REST =============

@api_view(['GET'])
def obtener_perfil(request):
    """API: Obtener perfil del usuario actual."""
    serializer = UsuarioSerializer(request.user)
    return Response(serializer.data)