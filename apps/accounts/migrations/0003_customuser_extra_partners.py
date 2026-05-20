from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_userrole'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='extra_partners',
            field=models.ManyToManyField(
                blank=True,
                help_text='Extra implementing partners this supervisor can work across.',
                related_name='extra_supervisors',
                to='accounts.partner',
                verbose_name='Additional Partners',
            ),
        ),
    ]
