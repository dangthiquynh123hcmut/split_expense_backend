from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("group", "0013_transferconfirmtoken"),
    ]

    operations = [
        migrations.AddField(
            model_name="group",
            name="debt_optimization",
            field=models.CharField(
                choices=[("GROUP", "Group"), ("EVENT", "Event")],
                default="GROUP",
                max_length=10,
            ),
        ),
    ]
