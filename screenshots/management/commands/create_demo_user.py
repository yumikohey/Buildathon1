from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import IntegrityError


class Command(BaseCommand):
    help = 'Create a demo user account with username and password "demo"'

    def handle(self, *args, **options):
        try:
            # Check if demo user already exists
            if User.objects.filter(username='demo').exists():
                self.stdout.write(
                    self.style.WARNING('Demo user already exists')
                )
                return

            # Create demo user
            user = User.objects.create_user(
                username='demo',
                password='demo',
                email='demo@example.com',
                first_name='Demo',
                last_name='User'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created demo user: {user.username}'
                )
            )
            
        except IntegrityError as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating demo user: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Unexpected error: {e}')
            )