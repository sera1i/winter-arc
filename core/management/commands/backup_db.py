import os
import subprocess
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = "Generates a PostgreSQL backup or SQLite copy and documents restoration procedures."

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default='backups',
            help='Directory where backup files should be saved (default: backups/)',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        db_config = settings.DATABASES['default']
        engine = db_config.get('ENGINE', '')

        if 'postgresql' in engine:
            db_name = db_config.get('NAME')
            user = db_config.get('USER')
            host = db_config.get('HOST', 'localhost')
            port = db_config.get('PORT', '5432')
            backup_file = os.path.join(output_dir, f"{db_name}_{timestamp}.sql.gz")

            self.stdout.write(self.style.NOTICE(f"Initiating PostgreSQL backup for database '{db_name}'..."))
            env = os.environ.copy()
            if db_config.get('PASSWORD'):
                env['PGPASSWORD'] = db_config.get('PASSWORD')

            cmd = [
                'pg_dump',
                '-h', str(host),
                '-p', str(port),
                '-U', str(user),
                '-F', 'c',  # Custom format (compressed and suitable for pg_restore)
                '-b',       # Include large objects
                '-v',       # Verbose
                '-f', backup_file,
                db_name,
            ]

            try:
                subprocess.run(cmd, env=env, check=True)
                self.stdout.write(self.style.SUCCESS(f"PostgreSQL backup successfully written to: {backup_file}"))
                self.stdout.write(self.style.NOTICE(f"To restore run: pg_restore -h {host} -U {user} -d {db_name} -c {backup_file}"))
            except FileNotFoundError:
                self.stdout.write(self.style.WARNING("pg_dump binary not found in PATH. Backup command blueprint:"))
                self.stdout.write(f"pg_dump -h {host} -p {port} -U {user} -F c -b -f {backup_file} {db_name}")
            except subprocess.CalledProcessError as err:
                raise CommandError(f"pg_dump failed with exit code {err.returncode}")

        elif 'sqlite3' in engine:
            db_name = db_config.get('NAME')
            backup_file = os.path.join(output_dir, f"sqlite_backup_{timestamp}.sqlite3")
            self.stdout.write(self.style.NOTICE(f"Copying SQLite database '{db_name}'..."))
            import shutil
            try:
                shutil.copy2(db_name, backup_file)
                self.stdout.write(self.style.SUCCESS(f"SQLite backup successfully written to: {backup_file}"))
                self.stdout.write(self.style.NOTICE(f"To restore: copy {backup_file} back to {db_name}"))
            except Exception as exc:
                raise CommandError(f"Failed to copy SQLite database: {exc}")
        else:
            raise CommandError(f"Unsupported database engine for automatic backup: {engine}")
