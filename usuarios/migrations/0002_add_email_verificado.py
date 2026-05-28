from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        # default=True para que los usuarios ya existentes queden verificados
        migrations.AddField(
            model_name='usuario',
            name='email_verificado',
            field=models.BooleanField(default=True),
        ),
        # Una vez agregada la columna, cambiamos el default a False
        # (solo afecta inserciones futuras desde la DB; Python usa model.default=False)
        migrations.AlterField(
            model_name='usuario',
            name='email_verificado',
            field=models.BooleanField(default=False),
        ),
    ]
