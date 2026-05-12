from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0002_add_assignment_export_token'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='assignment',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='assignment',
            constraint=models.UniqueConstraint(
                condition=models.Q(status='active'),
                fields=['participant', 'enumerator'],
                name='unique_active_assignment_per_enumerator',
            ),
        ),
    ]
