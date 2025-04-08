from django.core.management.base import BaseCommand
from savesphere_app.models import UserProfile

class Command(BaseCommand):
    help = 'Assigns admin role to a user based on their email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the user to make admin')

    def handle(self, *args, **options):
        email = options['email']
        try:
            user_profile = UserProfile.objects.get(email=email)
            user_profile.role = 'admin'
            user_profile.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully assigned admin role to {email}'))
        except UserProfile.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User with email {email} does not exist')) 