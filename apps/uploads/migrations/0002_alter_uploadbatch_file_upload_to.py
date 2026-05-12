import apps.uploads.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('uploads', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadbatch',
            name='file',
            field=models.FileField(upload_to=apps.uploads.models.upload_batch_path),
        ),
    ]
