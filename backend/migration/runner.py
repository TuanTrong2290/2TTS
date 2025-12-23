"""Migration runner for schema versioning and data migration"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


CURRENT_SCHEMA_VERSION = 2


class MigrationError(Exception):
    """Migration error"""
    pass


class MigrationRunner:
    def __init__(self):
        self.local_appdata = os.environ.get(
            "LOCALAPPDATA", 
            str(Path.home() / "AppData" / "Local")
        )
        self.appdata = os.environ.get(
            "APPDATA",
            str(Path.home() / "AppData" / "Roaming")
        )
        
        self.data_dir = Path(self.local_appdata) / "2TTS"
        self.config_dir = Path.home() / ".2tts"
        self.backup_dir = self.data_dir / "backup"
        self.logs_dir = self.data_dir / "logs"
        
    def check_schema_version(self) -> int:
        """Get current schema version from config"""
        config_file = self.config_dir / "config.json"
        if not config_file.exists():
            return 0
        
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("schema_version", 1)
        except:
            return 1
    
    def check_forward_version(self) -> bool:
        """Check if data is from a newer version (downgrade protection)"""
        current = self.check_schema_version()
        return current > CURRENT_SCHEMA_VERSION
    
    def needs_migration(self) -> bool:
        """Check if migration is needed"""
        current = self.check_schema_version()
        return 0 < current < CURRENT_SCHEMA_VERSION
    
    def create_backup(self) -> Path:
        """Create a backup of all data before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / timestamp
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Backup config directory
        if self.config_dir.exists():
            config_backup = backup_path / "config"
            shutil.copytree(self.config_dir, config_backup)
        
        # Backup data directory (excluding backups)
        for item in self.data_dir.iterdir():
            if item.name != "backup":
                dest = backup_path / "data" / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
        
        return backup_path
    
    def restore_backup(self, backup_path: Path):
        """Restore from a backup"""
        # Restore config
        config_backup = backup_path / "config"
        if config_backup.exists():
            if self.config_dir.exists():
                shutil.rmtree(self.config_dir)
            shutil.copytree(config_backup, self.config_dir)
        
        # Restore data
        data_backup = backup_path / "data"
        if data_backup.exists():
            for item in data_backup.iterdir():
                dest = self.data_dir / item.name
                if dest.exists():
                    if dest.is_dir():
                        shutil.rmtree(dest)
                    else:
                        dest.unlink()
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
    
    def run_migration(self, from_version: int, to_version: int) -> bool:
        """Run migrations from one version to another"""
        migrations = {
            (1, 2): self._migrate_v1_to_v2,
        }
        
        current = from_version
        while current < to_version:
            migration_key = (current, current + 1)
            if migration_key in migrations:
                migrations[migration_key]()
            current += 1
        
        # Update schema version in config
        self._set_schema_version(to_version)
        return True
    
    def _set_schema_version(self, version: int):
        """Set schema version in config"""
        config_file = self.config_dir / "config.json"
        config = {}
        
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        
        config["schema_version"] = version
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    
    def _migrate_v1_to_v2(self):
        """Migration from v1 to v2: Add schema_version field"""
        # This is a placeholder migration
        # In v2, we just add the schema_version field which is done by _set_schema_version
        pass
    
    def migrate(self) -> Dict[str, Any]:
        """Run full migration process with backup and rollback support"""
        result = {
            "success": False,
            "from_version": 0,
            "to_version": CURRENT_SCHEMA_VERSION,
            "backup_path": None,
            "error": None
        }
        
        # Check for forward version (downgrade)
        if self.check_forward_version():
            result["error"] = (
                f"Data is from a newer version (schema v{self.check_schema_version()}). "
                f"This version only supports up to schema v{CURRENT_SCHEMA_VERSION}. "
                "Please upgrade the application."
            )
            return result
        
        current_version = self.check_schema_version()
        result["from_version"] = current_version
        
        if not self.needs_migration():
            if current_version == 0:
                # Fresh install
                self._set_schema_version(CURRENT_SCHEMA_VERSION)
            result["success"] = True
            return result
        
        # Create backup
        try:
            backup_path = self.create_backup()
            result["backup_path"] = str(backup_path)
        except Exception as e:
            result["error"] = f"Failed to create backup: {e}"
            return result
        
        # Run migration
        try:
            self.run_migration(current_version, CURRENT_SCHEMA_VERSION)
            result["success"] = True
        except Exception as e:
            result["error"] = f"Migration failed: {e}"
            # Rollback
            try:
                self.restore_backup(backup_path)
                result["error"] += " (rolled back successfully)"
            except Exception as re:
                result["error"] += f" (rollback also failed: {re})"
        
        return result
