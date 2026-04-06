# Task Scheduler - Delayed and Recurring Actions

**TICKET-FEAT-002: Scheduler & Actions Différées (Cron)**

Janus now supports scheduling tasks to run at specific times or on a recurring basis. This enables powerful time-based automation without needing external cron jobs or task schedulers.

## Features

The Task Scheduler provides:

- ⏰ **Delayed Tasks**: Schedule actions to run after a delay (e.g., "remind me in 5 minutes")
- 🔄 **Recurring Tasks**: Schedule actions to repeat on a schedule (e.g., "remind me every hour")
- 💾 **Persistent Storage**: Tasks survive application restarts
- 📊 **Dashboard View**: See all scheduled tasks in the dashboard
- 🎯 **TTS Notifications**: Use text-to-speech for reminders and alerts

## Basic Usage

### One-Time Reminders

Schedule a task to run once after a delay:

```
"Rappelle-moi de partir dans 5 minutes"
"Remind me to leave in 5 minutes"
```

This creates a task that will activate the TTS system after 5 minutes with the reminder message.

### Recurring Reminders

Schedule a task to repeat on a schedule:

```
"Rappelle-moi de boire de l'eau toutes les heures"
"Remind me to drink water every hour"
```

Supported schedule expressions:
- `every N minutes` - Run every N minutes
- `every N hours` - Run every N hours  
- `every day at HH:MM` - Run daily at specific time
- `every monday at HH:MM` - Run weekly on specific day

### Examples

#### Simple Reminders
```
"Rappelle-moi dans 10 minutes" → Reminder in 10 minutes
"Rappelle-moi de partir dans 30 secondes" → Reminder in 30 seconds
"Rappelle-moi dans 2 heures" → Reminder in 2 hours
```

#### Scheduled Actions
```
"Envoie-moi un rappel tous les vendredis à 17h" → Weekly Friday reminder at 5 PM
"Rappelle-moi de faire une pause toutes les 2 heures" → Break reminder every 2 hours
"Lance la sauvegarde tous les jours à 22h" → Daily backup at 10 PM
```

## How It Works

### Architecture

The Task Scheduler consists of several components:

1. **TaskScheduler** (`janus/core/scheduler.py`): Core scheduler engine
   - Manages task lifecycle (create, execute, cancel)
   - Persists tasks to database
   - Runs in background thread

2. **SchedulerAgent** (`janus/agents/scheduler_agent.py`): Action handler
   - Processes `schedule_task` actions from reasoner
   - Creates and manages scheduled tasks
   - Integrates with lifecycle service

3. **Database Storage**: SQLite table for persistence
   - Stores task metadata, schedule, and status
   - Enables tasks to survive application restarts

4. **Lifecycle Service**: Manages scheduler lifecycle
   - Starts/stops scheduler with application
   - Provides access to scheduler for other components

### Task Execution

When a scheduled task triggers:

1. Scheduler detects it's time to run the task
2. Task status changes to "running"
3. Scheduler executes the configured action:
   - **TTS Notification**: Speaks the reminder message via TTS
   - **Command Execution**: Runs a command through the pipeline (future)
4. Task status updates based on result:
   - **One-time tasks**: Marked as "completed" and removed
   - **Recurring tasks**: Status returns to "pending", next run calculated

### Database Schema

Tasks are stored in the `scheduled_tasks` table:

```sql
CREATE TABLE scheduled_tasks (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,           -- 'one_time' or 'recurring'
    command TEXT NOT NULL,              -- Original user command
    action TEXT NOT NULL,               -- JSON action definition
    schedule_time TEXT,                 -- When to run (one-time)
    schedule_expression TEXT,           -- Cron expression (recurring)
    status TEXT NOT NULL,               -- 'pending', 'running', 'completed', etc.
    created_at TEXT NOT NULL,
    last_run TEXT,
    next_run TEXT,
    run_count INTEGER DEFAULT 0,
    metadata TEXT
);
```

## Dashboard Integration

View and manage scheduled tasks through the Dashboard:

1. Open Dashboard (press configured keyboard shortcut or use command)
2. Navigate to "⏰ Scheduled Tasks" tab
3. View all tasks with:
   - Task ID and type
   - Original command
   - Current status
   - Next scheduled run time
   - Management actions (cancel, etc.)

The dashboard auto-refreshes every 5 seconds to show current task status.

## Technical Details

### Supported Action Types

Currently supported task actions:

1. **TTS Notification**
   ```json
   {
     "type": "tts_notification",
     "message": "Reminder message"
   }
   ```

2. **Command Execution** (future enhancement)
   ```json
   {
     "type": "execute_command",
     "command": "Command to execute"
   }
   ```

### Schedule Expressions

The scheduler uses the `schedule` library for timing. Supported expressions:

- `every N minutes` - e.g., "every 5 minutes"
- `every N hours` - e.g., "every 2 hours"
- `every day at HH:MM` - e.g., "every day at 10:30"
- `every WEEKDAY at HH:MM` - e.g., "every friday at 17:00"

Weekdays: monday, tuesday, wednesday, thursday, friday, saturday, sunday

### Task States

Tasks progress through these states:

- **pending**: Waiting to run
- **running**: Currently executing
- **completed**: Finished successfully (one-time tasks only)
- **failed**: Execution failed
- **cancelled**: User cancelled the task

### Persistence

Tasks are automatically saved to the database:

- On creation
- After execution (status update)
- On cancellation

When Janus restarts:
- Pending tasks are loaded from database
- Tasks are re-registered with scheduler
- Execution continues as scheduled

## Limitations

Current limitations (may be addressed in future updates):

1. **Action Types**: Only TTS notifications currently supported
2. **Complex Schedules**: No support for complex cron expressions (e.g., "every 3rd Tuesday")
3. **Task Editing**: Cannot edit existing tasks (must cancel and recreate)
4. **Execution Context**: Limited context available during scheduled execution
5. **Error Recovery**: Failed tasks are not automatically retried

## Future Enhancements

Planned improvements:

- [ ] Support for executing arbitrary commands
- [ ] Rich task editing in dashboard
- [ ] Task templates and presets
- [ ] Advanced scheduling (complex cron expressions)
- [ ] Task dependencies and chains
- [ ] Conditional execution
- [ ] Error handling and retry logic
- [ ] Task categories and tags
- [ ] Export/import task configurations

## Troubleshooting

### Tasks Not Executing

If scheduled tasks are not running:

1. **Check Scheduler Status**: Verify scheduler is running in logs
2. **Check Task Status**: Open Dashboard → Scheduled Tasks tab
3. **Verify TTS**: Ensure TTS service is enabled and working
4. **Check Logs**: Look for scheduler errors in application logs

### Tasks Not Persisting

If tasks disappear after restart:

1. **Check Database**: Ensure database file exists and is writable
2. **Check Migrations**: Verify migration 003 was applied successfully
3. **Check Logs**: Look for database errors during startup

### Incorrect Timing

If tasks run at wrong times:

1. **Check System Clock**: Ensure system time is correct
2. **Check Expression**: Verify schedule expression is valid
3. **Check Timezone**: Scheduler uses system local time

## Examples

### Morning Standup Reminder
```
"Rappelle-moi du standup tous les jours ouvrables à 9h"
```

### Hydration Reminders
```
"Rappelle-moi de boire de l'eau toutes les 30 minutes"
```

### End of Day Reminder
```
"Rappelle-moi de sauvegarder mon travail tous les jours à 18h"
```

### Meeting Preparation
```
"Rappelle-moi de préparer la réunion dans 15 minutes"
```

### Weekly Report
```
"Rappelle-moi d'envoyer le rapport tous les vendredis à 16h"
```

## API Reference

For developers integrating with the scheduler:

### SchedulerAgent Actions

**schedule_task**
```python
{
    "action": "schedule_task",
    "args": {
        "delay_seconds": 300,  # OR
        "schedule_expression": "every 1 hour",
        "message": "Reminder text"  # OR
        "command": "Command to execute"
    }
}
```

**cancel_task**
```python
{
    "action": "cancel_task",
    "args": {
        "task_id": "uuid-of-task"
    }
}
```

**list_tasks**
```python
{
    "action": "list_tasks",
    "args": {}
}
```

### TaskScheduler Methods

```python
from janus.core.scheduler import TaskScheduler

scheduler = TaskScheduler(db_connection, tts_service, pipeline)

# Schedule a task
task = scheduler.schedule_task(
    task_id="my_task",
    command="Original command",
    action={"type": "tts_notification", "message": "Reminder"},
    delay_seconds=300
)

# Cancel a task
scheduler.cancel_task("my_task")

# Get task status
task = scheduler.get_task("my_task")

# List pending tasks
pending_tasks = scheduler.get_pending_tasks()
```

## See Also

- [Use Cases](04-use-cases.md) - More automation examples
- [Personalization](05-personalization.md) - Customize Janus behavior
- [Deep Links](11-deep-links.md) - Application integration
