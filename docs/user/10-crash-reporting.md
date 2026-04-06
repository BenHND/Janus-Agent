# Crash Reporting & Privacy

## What is Crash Reporting?

Janus includes an optional feature that can send anonymous crash reports to the developers when the application encounters an error. This helps us identify and fix bugs faster, improving the application for everyone.

**Important:** Crash reporting is **opt-in only**. You must explicitly agree to enable it, and you can disable it at any time.

## Your Privacy Matters

We take your privacy seriously. Here's exactly what we collect and what we don't:

### ✅ What We Collect

- **Error messages** (with sensitive data removed)
- **Stack traces** (technical information about where the error occurred)
- **System information** (your operating system and Python version)
- **Application version** and settings (to help reproduce the issue)

### ❌ What We DON'T Collect

- **Screenshots** or screen captures
- **Your voice commands** or prompts
- **Personal files** or data
- **API keys**, passwords, or tokens
- **Email addresses** or personal information
- **Anything from your clipboard**

**All crash reports are automatically filtered** to remove any sensitive information before being sent.

## First Launch

When you first run Janus, you'll see a prompt like this:

```
==================================================================
🔒 CRASH REPORTING & TELEMETRY
==================================================================

Janus can send anonymous crash reports to help improve the application.

What we collect:
  ✓ Stack traces and error messages (sanitized)
  ✓ System information (OS, Python version)
  ✓ Application version and configuration

What we DON'T collect:
  ✗ Screenshots or screen captures
  ✗ Your voice commands or prompts
  ✗ API keys, passwords, or tokens
  ✗ Personal files or data

All reports are automatically sanitized to remove sensitive information.
You can opt-out at any time by editing config.ini

==================================================================

Allow anonymous crash reports? [y/N]:
```

### Choosing Yes or No

- **Type 'y' and press Enter** to enable crash reporting
- **Type 'n' or just press Enter** to disable it

Your choice is saved and you won't be prompted again unless you delete your `config.ini` file.

## Managing Your Settings

### Checking Current Status

Your crash reporting preference is stored in `config.ini`:

```ini
[telemetry]
crash_reporting_consent = true  # or false
```

### Enabling Crash Reporting

If you initially declined but want to enable it later:

1. Open `config.ini` in a text editor
2. Find the `[telemetry]` section
3. Change `crash_reporting_consent = false` to `crash_reporting_consent = true`
4. Save the file and restart Janus

### Disabling Crash Reporting

To disable crash reporting:

1. Open `config.ini` in a text editor
2. Find the `[telemetry]` section
3. Change `crash_reporting_consent = true` to `crash_reporting_consent = false`
4. Save the file

The change takes effect immediately - no restart needed for disabling.

## What Happens When There's a Crash?

If crash reporting is enabled and Janus encounters an error:

1. **The error is captured** by our crash reporting system
2. **Sensitive data is filtered out** automatically (API keys, passwords, personal info)
3. **An anonymous report is sent** to our error tracking service (Sentry)
4. **Developers are notified** and can investigate the issue
5. **A fix is created** and included in the next update

**You don't need to do anything** - the process is completely automatic and silent.

## Frequently Asked Questions

### Q: Will this slow down my computer?

**A:** No. The crash reporting system only activates when an error occurs, which is rare. It has no performance impact during normal operation.

### Q: Can you see what I'm doing?

**A:** No. We only receive error reports when the application crashes. We never receive information about your normal usage, commands, or activities.

### Q: What if I have sensitive API keys configured?

**A:** All API keys, passwords, and tokens are automatically filtered out before any report is sent. We use multiple filtering patterns to ensure this data never leaves your computer.

### Q: Will my voice commands be sent?

**A:** No. Voice commands, prompts, and user input are explicitly blocked from crash reports. We only receive the technical error information.

### Q: Can I see what data is sent?

**A:** Yes. The crash reporting code is open source and available in the `janus/telemetry/` directory. You can review exactly what data is collected and how it's filtered.

### Q: What if I'm working in a secure environment?

**A:** If you work with sensitive data or in a secure environment, we recommend keeping crash reporting **disabled**. While we filter sensitive data, you may prefer not to send any external data at all.

### Q: How do I know if a report was sent?

**A:** When crash reporting is enabled, error messages will appear in the application logs located in the logs directory. You can also check the Janus log files for entries mentioning "Sentry" or "crash report".

### Q: Who has access to the crash reports?

**A:** Only the Janus development team has access to crash reports. They are stored securely on Sentry's servers and are used solely for debugging and improving the application.

### Q: How long are crash reports kept?

**A:** Crash reports are typically kept for 90 days, after which they are automatically deleted. This follows standard best practices for error tracking.

## Data Security

- All crash reports are transmitted over **encrypted HTTPS connections**
- Reports are stored on **Sentry's secure servers** with industry-standard security
- We follow **GDPR principles** even though crash reports contain no personal data
- The **data sanitization** process runs before reports leave your computer

## Need Help?

If you have questions or concerns about crash reporting:

1. **Check the logs:** Look in the `logs/` directory for detailed information
2. **Review the code:** The crash reporting code is in `janus/telemetry/`
3. **Open an issue:** Create a GitHub issue if you have concerns
4. **Contact us:** Reach out to the development team

## Technical Details

For developers and advanced users who want to understand the implementation:

- **Technology:** Sentry Python SDK (open source)
- **Sanitization:** Pattern-based filtering of sensitive data
- **Exception handlers:** Global handlers for uncaught exceptions, asyncio errors, and Qt crashes
- **Integration points:** Application initialization, logging system
- **Documentation:** See `docs/developer/TICKET-OPS-002-CRASH-REPORTING.md`

## Summary

- ✅ Crash reporting is **optional and opt-in**
- ✅ All reports are **automatically sanitized**
- ✅ **No personal data** is collected
- ✅ You can **enable or disable** it at any time
- ✅ It helps us **fix bugs faster**

Thank you for considering crash reporting. Your contribution helps make Janus better for everyone! 🙏
