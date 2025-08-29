#!/usr/bin/env python3
"""
Backup and Recovery System for Model Realignment
Automated backups, versioning, and disaster recovery
"""

import os
import json
import shutil
import tarfile
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import threading
import time

from state_manager import StateManager
from email_system import EmailSystem


class BackupSystem:
    """
    Comprehensive backup and recovery system for Model Realignment data
    """
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        self.state_manager = StateManager()
        self.email_system = EmailSystem()
        self.logger = logging.getLogger(__name__)
        
        # Backup configuration
        self.config = {
            "hourly_backups_keep": 24,    # Keep 24 hourly backups
            "daily_backups_keep": 30,     # Keep 30 daily backups  
            "weekly_backups_keep": 12,    # Keep 12 weekly backups
            "monthly_backups_keep": 12,   # Keep 12 monthly backups
            "compress_backups": True,     # Use compression
            "verify_backups": True,       # Verify backup integrity
            "auto_backup_interval": 3600, # Auto backup every hour
        }
        
        # Files to backup
        self.backup_files = [
            "realignment_state.json",
            "data/chroma_db",
            "logs",
            "dashboard/templates",
            "applescript"
        ]
        
        # Automatic backup thread
        self.auto_backup_active = False
        self.auto_backup_thread = None
        
        self.logger.info("Backup system initialized")
    
    def create_backup(self, backup_type: str = "manual") -> Dict[str, Any]:
        """
        Create a complete system backup
        
        Args:
            backup_type: Type of backup (manual, hourly, daily, weekly, monthly)
            
        Returns:
            Backup results dictionary
        """
        timestamp = datetime.now(timezone.utc)
        backup_name = f"{backup_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / f"{backup_name}.tar.gz"
        
        self.logger.info(f"Creating {backup_type} backup: {backup_name}")
        
        try:
            # Create temporary directory for staging
            temp_backup_dir = self.backup_dir / f"temp_{backup_name}"
            temp_backup_dir.mkdir(exist_ok=True)
            
            # Collect all files to backup
            backed_up_files = []
            total_size = 0
            
            for item in self.backup_files:
                source_path = Path(item)
                if source_path.exists():
                    if source_path.is_file():
                        # Copy individual file
                        dest_path = temp_backup_dir / source_path.name
                        shutil.copy2(source_path, dest_path)
                        size = dest_path.stat().st_size
                        backed_up_files.append({
                            "path": str(source_path),
                            "type": "file",
                            "size": size
                        })
                        total_size += size
                    else:
                        # Copy directory recursively
                        dest_path = temp_backup_dir / source_path.name
                        shutil.copytree(source_path, dest_path, dirs_exist_ok=True)
                        size = sum(f.stat().st_size for f in dest_path.rglob('*') if f.is_file())
                        backed_up_files.append({
                            "path": str(source_path),
                            "type": "directory", 
                            "size": size
                        })
                        total_size += size
                else:
                    self.logger.warning(f"Backup item not found: {item}")
            
            # Create metadata file
            metadata = {
                "backup_name": backup_name,
                "backup_type": backup_type,
                "timestamp": timestamp.isoformat(),
                "files": backed_up_files,
                "total_size": total_size,
                "system_info": {
                    "current_score": self.state_manager.get_current_score(),
                    "total_violations": self.state_manager.get_full_state().get("total_violations", 0),
                    "hours_clean": self.state_manager.get_hours_since_last_violation()
                }
            }
            
            metadata_file = temp_backup_dir / "backup_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create compressed archive
            with tarfile.open(backup_path, 'w:gz' if self.config["compress_backups"] else 'w') as tar:
                tar.add(temp_backup_dir, arcname=backup_name)
            
            # Clean up temporary directory
            shutil.rmtree(temp_backup_dir)
            
            # Verify backup if enabled
            verification_result = None
            if self.config["verify_backups"]:
                verification_result = self._verify_backup(backup_path)
            
            # Calculate backup file hash
            backup_hash = self._calculate_file_hash(backup_path)
            
            backup_result = {
                "success": True,
                "backup_name": backup_name,
                "backup_path": str(backup_path),
                "backup_type": backup_type,
                "timestamp": timestamp.isoformat(),
                "files_count": len(backed_up_files),
                "total_size": total_size,
                "compressed_size": backup_path.stat().st_size,
                "compression_ratio": round((1 - backup_path.stat().st_size / total_size) * 100, 1) if total_size > 0 else 0,
                "hash": backup_hash,
                "verification": verification_result
            }
            
            # Save backup record
            self._save_backup_record(backup_result)
            
            self.logger.info(f"Backup completed: {backup_name} ({backup_result['compressed_size']} bytes)")
            
            return backup_result
            
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            
            # Clean up on error
            if backup_path.exists():
                backup_path.unlink()
            
            return {
                "success": False,
                "error": str(e),
                "backup_type": backup_type,
                "timestamp": timestamp.isoformat()
            }
    
    def restore_backup(self, backup_name: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Restore from a backup
        
        Args:
            backup_name: Name of backup to restore
            confirm: Confirmation flag (safety check)
            
        Returns:
            Restoration results
        """
        if not confirm:
            return {
                "success": False,
                "error": "Restoration requires explicit confirmation (confirm=True)"
            }
        
        # Find backup file
        backup_files = list(self.backup_dir.glob(f"{backup_name}.tar.gz"))
        if not backup_files:
            return {
                "success": False,
                "error": f"Backup not found: {backup_name}"
            }
        
        backup_path = backup_files[0]
        
        self.logger.warning(f"Starting restoration from backup: {backup_name}")
        
        try:
            # Create backup of current state before restoration
            pre_restore_backup = self.create_backup("pre_restore")
            if not pre_restore_backup["success"]:
                return {
                    "success": False,
                    "error": "Failed to create pre-restoration backup"
                }
            
            # Extract backup to temporary location
            temp_restore_dir = self.backup_dir / f"restore_{backup_name}"
            temp_restore_dir.mkdir(exist_ok=True)
            
            with tarfile.open(backup_path, 'r:gz' if backup_path.suffix == '.gz' else 'r') as tar:
                tar.extractall(temp_restore_dir)
            
            # Find the extracted backup directory
            extracted_dirs = [d for d in temp_restore_dir.iterdir() if d.is_dir()]
            if not extracted_dirs:
                return {
                    "success": False,
                    "error": "No backup data found in archive"
                }
            
            backup_data_dir = extracted_dirs[0]
            
            # Read backup metadata
            metadata_file = backup_data_dir / "backup_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    backup_metadata = json.load(f)
            else:
                backup_metadata = {"files": []}
            
            # Restore files
            restored_files = []
            
            for item in backup_data_dir.iterdir():
                if item.name == "backup_metadata.json":
                    continue
                
                # Determine destination path
                dest_path = Path(item.name)
                
                # Backup existing file/directory if it exists
                if dest_path.exists():
                    backup_dest = dest_path.with_suffix(dest_path.suffix + '.backup')
                    if dest_path.is_file():
                        shutil.copy2(dest_path, backup_dest)
                    else:
                        shutil.copytree(dest_path, backup_dest, dirs_exist_ok=True)
                
                # Restore from backup
                if item.is_file():
                    shutil.copy2(item, dest_path)
                else:
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(item, dest_path)
                
                restored_files.append(str(dest_path))
            
            # Clean up temporary directory
            shutil.rmtree(temp_restore_dir)
            
            restoration_result = {
                "success": True,
                "backup_name": backup_name,
                "backup_metadata": backup_metadata,
                "restored_files": restored_files,
                "pre_restore_backup": pre_restore_backup["backup_name"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.warning(f"Restoration completed: {backup_name}")
            
            # Send email notification
            try:
                self.email_system.send_system_health_alert(
                    "warning",
                    f"System restoration completed from backup: {backup_name}"
                )
            except:
                pass
            
            return restoration_result
            
        except Exception as e:
            self.logger.error(f"Restoration failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "backup_name": backup_name
            }
    
    def list_backups(self) -> Dict[str, Any]:
        """List all available backups with metadata"""
        backups = []
        
        # Find all backup files
        backup_files = sorted(self.backup_dir.glob("*.tar.gz"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        for backup_file in backup_files:
            try:
                # Extract basic info from filename
                name = backup_file.stem
                parts = name.split('_')
                backup_type = parts[0] if parts else "unknown"
                
                # Get file stats
                stat = backup_file.stat()
                
                # Try to read metadata if available
                metadata = None
                try:
                    with tarfile.open(backup_file, 'r:gz' if backup_file.suffix == '.gz' else 'r') as tar:
                        metadata_member = None
                        for member in tar.getmembers():
                            if member.name.endswith('backup_metadata.json'):
                                metadata_member = member
                                break
                        
                        if metadata_member:
                            metadata_file = tar.extractfile(metadata_member)
                            if metadata_file:
                                metadata = json.loads(metadata_file.read().decode())
                except:
                    pass  # Metadata not available
                
                backup_info = {
                    "name": name,
                    "file": str(backup_file),
                    "type": backup_type,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "age_days": (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days,
                    "metadata": metadata
                }
                
                backups.append(backup_info)
                
            except Exception as e:
                self.logger.warning(f"Failed to read backup info for {backup_file}: {e}")
        
        return {
            "backups": backups,
            "total_count": len(backups),
            "total_size": sum(b["size"] for b in backups),
            "oldest_backup": backups[-1]["created"] if backups else None,
            "newest_backup": backups[0]["created"] if backups else None
        }
    
    def cleanup_old_backups(self) -> Dict[str, Any]:
        """Clean up old backups according to retention policy"""
        now = datetime.now()
        deleted_backups = []
        kept_backups = []
        
        backups_info = self.list_backups()
        
        for backup in backups_info["backups"]:
            backup_date = datetime.fromisoformat(backup["created"])
            age_days = (now - backup_date).days
            age_hours = (now - backup_date).total_seconds() / 3600
            
            backup_type = backup["type"]
            should_delete = False
            
            # Apply retention policies
            if backup_type == "hourly" and age_hours > self.config["hourly_backups_keep"]:
                should_delete = True
            elif backup_type == "daily" and age_days > self.config["daily_backups_keep"]:
                should_delete = True
            elif backup_type == "weekly" and age_days > (self.config["weekly_backups_keep"] * 7):
                should_delete = True
            elif backup_type == "monthly" and age_days > (self.config["monthly_backups_keep"] * 30):
                should_delete = True
            
            if should_delete:
                try:
                    Path(backup["file"]).unlink()
                    deleted_backups.append(backup["name"])
                    self.logger.info(f"Deleted old backup: {backup['name']}")
                except Exception as e:
                    self.logger.error(f"Failed to delete backup {backup['name']}: {e}")
            else:
                kept_backups.append(backup["name"])
        
        return {
            "deleted_count": len(deleted_backups),
            "deleted_backups": deleted_backups,
            "kept_count": len(kept_backups),
            "kept_backups": kept_backups
        }
    
    def start_auto_backup(self):
        """Start automatic backup service"""
        if self.auto_backup_active:
            return {"status": "already_running"}
        
        self.auto_backup_active = True
        self.auto_backup_thread = threading.Thread(target=self._auto_backup_loop, daemon=True)
        self.auto_backup_thread.start()
        
        self.logger.info("Automatic backup service started")
        return {"status": "started"}
    
    def stop_auto_backup(self):
        """Stop automatic backup service"""
        if not self.auto_backup_active:
            return {"status": "not_running"}
        
        self.auto_backup_active = False
        if self.auto_backup_thread and self.auto_backup_thread.is_alive():
            self.auto_backup_thread.join(timeout=10)
        
        self.logger.info("Automatic backup service stopped")
        return {"status": "stopped"}
    
    def _auto_backup_loop(self):
        """Background thread for automatic backups"""
        while self.auto_backup_active:
            try:
                # Create hourly backup
                backup_result = self.create_backup("hourly")
                
                if backup_result["success"]:
                    self.logger.info(f"Automatic backup completed: {backup_result['backup_name']}")
                else:
                    self.logger.error(f"Automatic backup failed: {backup_result.get('error')}")
                
                # Clean up old backups
                self.cleanup_old_backups()
                
                # Sleep for the configured interval
                time.sleep(self.config["auto_backup_interval"])
                
            except Exception as e:
                self.logger.error(f"Auto backup loop error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    def _verify_backup(self, backup_path: Path) -> Dict[str, Any]:
        """Verify backup integrity"""
        try:
            with tarfile.open(backup_path, 'r:gz' if backup_path.suffix == '.gz' else 'r') as tar:
                # Check if we can list all members
                members = tar.getmembers()
                
                # Verify each member can be read
                for member in members[:10]:  # Check first 10 files
                    if member.isfile():
                        data = tar.extractfile(member)
                        if data:
                            data.read(1024)  # Read first KB
                
                return {
                    "verified": True,
                    "members_count": len(members),
                    "verification_time": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "verified": False,
                "error": str(e)
            }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def _save_backup_record(self, backup_result: Dict[str, Any]):
        """Save backup record to history"""
        records_file = self.backup_dir / "backup_records.json"
        
        try:
            if records_file.exists():
                with open(records_file, 'r') as f:
                    records = json.load(f)
            else:
                records = []
            
            records.append(backup_result)
            
            # Keep only last 100 records
            records = records[-100:]
            
            with open(records_file, 'w') as f:
                json.dump(records, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save backup record: {e}")


def main():
    """Test and manage the backup system"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Model Realignment Backup System")
    parser.add_argument("--create", choices=["manual", "hourly", "daily", "weekly", "monthly"], 
                        help="Create a backup")
    parser.add_argument("--list", action="store_true", help="List all backups")
    parser.add_argument("--cleanup", action="store_true", help="Clean up old backups")
    parser.add_argument("--restore", type=str, help="Restore from backup (requires --confirm)")
    parser.add_argument("--confirm", action="store_true", help="Confirm restoration")
    parser.add_argument("--auto-start", action="store_true", help="Start automatic backup service")
    parser.add_argument("--auto-stop", action="store_true", help="Stop automatic backup service")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    backup_system = BackupSystem()
    
    if args.create:
        print(f"Creating {args.create} backup...")
        result = backup_system.create_backup(args.create)
        print(json.dumps(result, indent=2))
    
    elif args.list:
        result = backup_system.list_backups()
        print("📦 Available Backups:")
        print(json.dumps(result, indent=2))
    
    elif args.cleanup:
        result = backup_system.cleanup_old_backups()
        print("🧹 Backup Cleanup Results:")
        print(json.dumps(result, indent=2))
    
    elif args.restore:
        if not args.confirm:
            print("❌ Restoration requires --confirm flag for safety")
            return
        
        print(f"⚠️  Restoring from backup: {args.restore}")
        result = backup_system.restore_backup(args.restore, confirm=True)
        print(json.dumps(result, indent=2))
    
    elif args.auto_start:
        result = backup_system.start_auto_backup()
        print(f"🤖 Auto-backup service: {result['status']}")
    
    elif args.auto_stop:
        result = backup_system.stop_auto_backup()
        print(f"⏹️  Auto-backup service: {result['status']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()