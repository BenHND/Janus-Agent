# Database Upgrade Guide

## What is This?

Starting with version 0.2, Janus includes an automatic database migration system that preserves your data when upgrading to new versions.

## Do I Need to Do Anything?

**No!** Database upgrades happen automatically when you start Janus after updating to a new version.

## What Happens During an Upgrade?

When you start Janus after updating, you'll see messages like this:

```
[INFO] Database migration required: v1 -> v2
[INFO] Applying migration 002: Add risk_level to history
[INFO] ✓ Migration 002 completed
[INFO] ✓ All migrations completed. Database is now at version 2
```

This means:
- Your database is being upgraded from version 1 to version 2
- New features or improvements are being added to the database
- **Your data is being preserved** - history, sessions, and settings remain intact

## Upgrade Process

1. **Backup** (automatic): Janus automatically backs up your database
2. **Version Check**: Checks if your database needs upgrading
3. **Apply Changes**: Applies necessary schema changes
4. **Verify**: Confirms the upgrade was successful
5. **Continue**: Starts normally with your preserved data

## What Gets Preserved?

Everything! Including:
- ✅ Command history
- ✅ Session data
- ✅ User preferences
- ✅ Conversation history
- ✅ Stored context
- ✅ Action logs

## Troubleshooting

### "Migration failed" Error

If you see a migration failure message:

1. **Don't panic** - your data is safe
2. **Check the logs** for details: `python main.py --logs`
3. **Restart Janus** - sometimes a retry works
4. **Report the issue** on GitHub if it persists

### Slow First Startup

If the first startup after an update is slower than usual:
- This is normal for large databases
- Migrations are being applied (one-time operation)
- Future startups will be normal speed
- Don't interrupt the process

### "Schema verification failed" Warning

This warning is informational and usually safe to ignore. It means:
- The database structure is newer than expected
- This can happen if you're testing development versions
- Your data is still safe and accessible

## Manual Backup (Optional)

While Janus handles upgrades automatically, you can manually backup your database:

### macOS/Linux

```bash
# Navigate to Janus directory
cd /path/to/Janus

# Backup database
cp janus_memory.db janus_memory.db.backup.$(date +%Y%m%d)

# List backups
ls -lh janus_memory.db*
```

### Windows

```powershell
# Navigate to Janus directory
cd C:\path\to\Janus

# Backup database
copy janus_memory.db janus_memory.db.backup
```

## Restore from Backup

If you need to restore from a backup:

1. **Stop Janus** completely
2. **Replace database**:
   ```bash
   # Remove current database
   rm janus_memory.db
   rm janus_memory.db-wal
   rm janus_memory.db-shm
   
   # Restore backup
   cp janus_memory.db.backup janus_memory.db
   ```
3. **Start Janus** - migrations will be re-applied if needed

## Version History

### Version 0.1 → 0.2
- ✨ Added database migration system
- ✨ Added `risk_level` field to action history
- 📊 Schema version: 1 → 2

### Future Versions
Check [CHANGELOG.md](../../CHANGELOG.md) for details on database changes in each release.

## FAQ

### Will upgrading delete my data?
No! The migration system is designed to preserve all your data while updating the database structure.

### Can I downgrade to an older version?
Not recommended. Older versions won't understand the new database structure. If you must downgrade, restore from a backup made before upgrading.

### How long does migration take?
Usually less than a second. Large databases (>1GB) may take a few seconds.

### Can I skip a version?
Yes! You can upgrade from any old version to the latest. Migrations are applied sequentially.

### What if migration fails?
Your original database remains unchanged. Check the error message and report the issue on GitHub.

### Can I disable automatic migration?
Not currently, as it's essential for compatibility. But migrations only run when needed.

## Getting Help

If you encounter issues during upgrade:

1. **Check logs**: `python main.py --logs`
2. **Search issues**: [GitHub Issues](https://github.com/BenHND/Janus/issues)
3. **Create issue**: Include error message and database version
4. **Discord/Support**: Community can help troubleshoot

## Technical Details

For developers and advanced users:

- **Migration System**: SQLite `PRAGMA user_version`
- **Database Location**: `janus_memory.db` (in Janus root directory)
- **Migration Code**: `janus/core/db_migrations.py`
- **Documentation**: See archived developer documentation in `docs/archive/development/DATABASE_MIGRATIONS.md`

## Best Practices

1. **Keep backups** before major version updates (v0.x → v1.0)
2. **Don't interrupt** the migration process
3. **Update regularly** to avoid multiple migration steps
4. **Report issues** to help improve the system

---

**Questions or issues?** Open an issue on [GitHub](https://github.com/BenHND/Janus/issues) or check the archived developer documentation at `docs/archive/development/DATABASE_MIGRATIONS.md`.
