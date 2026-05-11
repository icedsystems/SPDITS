"""
Populate the database with realistic demo data for ICED SPDITS.
Run: python manage.py seed_demo_data
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

COUNTIES = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Thika', 'Kitale', 'Machakos']
GENDERS = ['Male', 'Female']

PARTNER_DATA = [
    {'name': 'Amref Health Africa', 'code': 'AMREF', 'contact_email': 'data@amref.org', 'sftp_username': 'amref_sftp'},
    {'name': 'Médecins Sans Frontières', 'code': 'MSF', 'contact_email': 'data@msf.org', 'sftp_username': 'msf_sftp'},
    {'name': 'Kenya Red Cross', 'code': 'KRC', 'contact_email': 'data@redcross.or.ke', 'sftp_username': 'krc_sftp'},
]


class Command(BaseCommand):
    help = 'Create demo data for testing ICED SPDITS'

    def add_arguments(self, parser):
        parser.add_argument('--participants', type=int, default=50, help='Number of participants to create')
        parser.add_argument('--clear', action='store_true', help='Clear existing demo data first')

    def handle(self, *args, **kwargs):
        n_participants = kwargs['participants']

        from apps.accounts.models import Partner, Role
        from apps.participants.models import Participant, IdentityMap, ParticipantStatus
        from apps.participants.utils import generate_pseudocode
        from apps.uploads.models import UploadBatch, BatchStatus
        from apps.tracing.models import TracingLog
        from apps.assignments.models import Assignment, AssignmentStatus
        from apps.interviews.models import Interview, InterviewStatus

        # --- Partners ---
        partners = []
        for pd in PARTNER_DATA:
            p, created = Partner.objects.get_or_create(code=pd['code'], defaults=pd)
            partners.append(p)
            if created:
                self.stdout.write(f'  Partner: {p.name}')

        # --- Users ---
        admin = User.objects.filter(role=Role.SYSTEM_ADMIN).first()
        if not admin:
            admin = User.objects.create_superuser(
                username='admin', email='admin@iced.org', password='spdits@2024!',
                first_name='System', last_name='Admin', role=Role.SYSTEM_ADMIN
            )
            self.stdout.write('  Admin created: admin@iced.org / spdits@2024!')

        partner_users = []
        for i, partner in enumerate(partners):
            pu, _ = User.objects.get_or_create(
                email=f'partner{i+1}@iced.org',
                defaults=dict(
                    username=f'partner{i+1}', first_name='Partner', last_name=f'User {i+1}',
                    role=Role.IMPLEMENTING_PARTNER, partner=partner, is_active=True
                )
            )
            if _: pu.set_password('spdits@2024!'); pu.save()
            partner_users.append(pu)

        supervisor, _ = User.objects.get_or_create(
            email='supervisor@iced.org',
            defaults=dict(username='supervisor', first_name='Sarah', last_name='Kamau',
                          role=Role.SUPERVISOR, is_active=True)
        )
        if _: supervisor.set_password('spdits@2024!'); supervisor.save()

        enumerators = []
        for i in range(3):
            e, _ = User.objects.get_or_create(
                email=f'enumerator{i+1}@iced.org',
                defaults=dict(username=f'enumerator{i+1}', first_name=f'Enum', last_name=f'{i+1}',
                              role=Role.ENUMERATOR, supervisor=supervisor, is_active=True)
            )
            if _: e.set_password('spdits@2024!'); e.save()
            enumerators.append(e)

        tracer, _ = User.objects.get_or_create(
            email='tracer@iced.org',
            defaults=dict(username='tracer1', first_name='Tom', last_name='Ochieng',
                          role=Role.TRACER, is_active=True)
        )
        if _: tracer.set_password('spdits@2024!'); tracer.save()

        compliance, _ = User.objects.get_or_create(
            email='compliance@iced.org',
            defaults=dict(username='compliance1', first_name='Carol', last_name='Mutua',
                          role=Role.COMPLIANCE_OFFICER, is_active=True)
        )
        if _: compliance.set_password('spdits@2024!'); compliance.save()

        # --- Upload Batch ---
        partner = partners[0]
        batch, _ = UploadBatch.objects.get_or_create(
            partner=partner,
            original_filename='demo_participants.csv',
            defaults=dict(
                uploaded_by=partner_users[0],
                file='uploads/demo/demo_participants.csv',
                file_size=10240,
                file_type='CSV',
                status=BatchStatus.APPROVED,
                source='web',
                total_records=n_participants,
                valid_records=n_participants,
                checksum_md5='abc123demo',
            )
        )
        self.stdout.write(f'  Batch: {batch.batch_id}')

        # --- Participants ---
        statuses_dist = (
            [ParticipantStatus.UPLOADED] * (n_participants // 5) +
            [ParticipantStatus.TRACING] * (n_participants // 5) +
            [ParticipantStatus.TRACED] * (n_participants // 5) +
            [ParticipantStatus.ASSIGNED] * (n_participants // 5) +
            [ParticipantStatus.INTERVIEWED] * (n_participants // 5)
        )
        random.shuffle(statuses_dist)

        first_names = ['James', 'Mary', 'John', 'Grace', 'Peter', 'Jane', 'David', 'Susan', 'Paul', 'Lucy']
        last_names = ['Omondi', 'Wanjiku', 'Kamau', 'Achieng', 'Mwangi', 'Otieno', 'Njoroge', 'Oloo']

        created_count = 0
        for i in range(n_participants):
            status = statuses_dist[i] if i < len(statuses_dist) else ParticipantStatus.UPLOADED
            pseudo = generate_pseudocode()
            data = {
                'county': random.choice(COUNTIES),
                'gender': random.choice(GENDERS),
                'age': str(random.randint(18, 65)),
                'sub_county': f'Sub-County {random.randint(1, 5)}',
                'ward': f'Ward {random.randint(1, 10)}',
            }
            p = Participant.objects.create(
                pseudo_code=pseudo,
                partner=random.choice(partners),
                upload_batch=batch,
                status=status,
                data=data,
                row_number=i + 2,
            )
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            phone = f'+2547{random.randint(10000000, 99999999)}'
            identity = IdentityMap(participant=p)
            identity.set_identifiers({
                'name': f'{fname} {lname}',
                'national_id': f'{random.randint(10000000, 40000000)}',
                'phone': phone,
                'address': f'Plot {random.randint(1, 500)}, {data["county"]}',
            })
            identity.save()

            # Tracing log
            if status not in [ParticipantStatus.UPLOADED]:
                TracingLog.objects.create(
                    participant=p, updated_by=tracer,
                    previous_status=ParticipantStatus.UPLOADED,
                    new_status=status,
                    notes='Demo tracing note',
                    contact_method=random.choice(['phone', 'visit', 'sms']),
                )

            # Assignment
            if status in [ParticipantStatus.ASSIGNED, ParticipantStatus.INTERVIEWED]:
                enum = random.choice(enumerators)
                a = Assignment.objects.create(
                    participant=p, enumerator=enum, supervisor=supervisor,
                    status=AssignmentStatus.ACTIVE if status == ParticipantStatus.ASSIGNED else AssignmentStatus.COMPLETED,
                )
                if status == ParticipantStatus.INTERVIEWED:
                    Interview.objects.create(
                        participant=p, assignment=a, enumerator=enum,
                        status=InterviewStatus.COMPLETED,
                    )

            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Seed data created successfully!\n'
            f'  Partners: {len(partners)}\n'
            f'  Participants: {created_count}\n\n'
            f'Test accounts (password: spdits@2024!):\n'
            f'  admin@iced.org       → System Admin\n'
            f'  partner1@iced.org    → Partner (Amref)\n'
            f'  supervisor@iced.org  → Supervisor\n'
            f'  enumerator1@iced.org → Enumerator\n'
            f'  tracer@iced.org      → Tracer\n'
            f'  compliance@iced.org  → Compliance Officer\n'
        ))
