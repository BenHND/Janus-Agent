# 📅 Microsoft 365 / Outlook Integration

**[← Back to Index](README.md)**

---

# 📅 Microsoft 365 / Outlook Integration

**[← Back to Index](README.md)**

---

## What You Can Do

Once configured, Janus can access your Microsoft 365 calendar and email **instantly**, without opening Outlook or taking screenshots:

### **📅 Calendar Commands**
- *"What's my next meeting?"* - Instant response with meeting details
- *"Do I have any meetings today?"* - Quick calendar overview
- *"When is my meeting with John?"* - Search for specific meetings
- *"Am I free this afternoon?"* - Check availability

### **📧 Email Commands**
- *"Summarize my unread emails"* - Get email summaries even if Outlook is closed
- *"Did I get any important emails?"* - Priority inbox check
- *"Read my latest email from Sarah"* - Search and read specific emails
- *"How many unread emails do I have?"* - Quick inbox count

---

## Setup Overview

Setting up Microsoft 365 integration requires **3 simple steps**:

1. **Register an app in Microsoft Azure** (one-time, 5 minutes)
2. **Enter credentials in Janus Settings** (copy & paste)
3. **Authorize Janus** (one-time login)

**Time Required:** About 10 minutes total

**What You Need:**
- Microsoft 365 account (work, school, or personal)
- Your Microsoft 365 email address
- 10 minutes of time

---

---

## Step 1: Register Your App in Microsoft Azure

**Why?** Microsoft requires all apps accessing your data to be registered for security.

**How long?** 5 minutes (one-time setup)

### 1.1 Open Azure Portal

1. Go to [portal.azure.com](https://portal.azure.com)
2. Sign in with your Microsoft 365 account
3. In the search bar at the top, type **"App registrations"**
4. Click on **"App registrations"** in the results

### 1.2 Create New Registration

1. Click the **"+ New registration"** button at the top
2. Fill in the form:

   ```
   Name: Janus Voice Assistant
   
   Supported account types:
   ◉ Accounts in this organizational directory only (your organization)
   ○ Accounts in any organizational directory
   ○ Personal Microsoft accounts
   
   Redirect URI: (Leave blank for now)
   ```

3. Click **"Register"** button at the bottom

### 1.3 Copy Your Client ID

After registration, you'll see the Overview page:

```
┌─────────────────────────────────────────────┐
│ Janus Voice Assistant                       │
├─────────────────────────────────────────────┤
│ Application (client) ID:                    │
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃ 12345678-1234-1234-1234-123456789012  ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│ [📋 Copy]                                   │
└─────────────────────────────────────────────┘
```

**⚠️ IMPORTANT:** Click the **Copy** button next to your Application (client) ID and **save it in a note** - you'll need it soon!

### 1.4 Create a Client Secret

1. In the left sidebar, click **"Certificates & secrets"**
2. Click **"+ New client secret"** button
3. Fill in:
   - **Description:** `Janus desktop app`
   - **Expires:** `24 months` (recommended)
4. Click **"Add"**
5. **⚠️ CRITICAL:** You'll see a screen like this:

   ```
   ┌─────────────────────────────────────────────┐
   │ Client secrets                              │
   ├─────────────────────────────────────────────┤
   │ Description: Janus desktop app              │
   │ Value:                                      │
   │ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
   │ ┃ abc123xyz...NEVER_SEE_THIS_AGAIN     ┃ │
   │ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
   │ [📋 Copy]                                   │
   └─────────────────────────────────────────────┘
   ```

   **Click the Copy button immediately!** You can **NEVER** see this value again after leaving this page. Save it in your note with the Client ID.

### 1.5 Add Permissions

1. In the left sidebar, click **"API permissions"**
2. Click **"+ Add a permission"**
3. Click **"Microsoft Graph"**
4. Click **"Delegated permissions"** (NOT Application permissions)
5. In the search box, type: `Calendars.Read`
6. Check the box next to **Calendars.Read**
7. In the search box, type: `Mail.Read`
8. Check the box next to **Mail.Read**
9. Click **"Add permissions"** at the bottom

Your permissions should now look like:

```
✅ Calendars.Read    (Delegated)
✅ Mail.Read         (Delegated)
```

**Optional:** If you're an admin, click **"Grant admin consent"** to skip the authorization step later.

---

## Step 2: Configure Janus Settings

**Where:** Open Janus → Settings → Microsoft 365 Integration

### 2.1 Open Janus Settings

**Option 1 - Voice:**
- Say: *"Open settings"* or *"Open preferences"*

**Option 2 - Menu:**
- Click the Janus menu icon
- Select "Settings" or "Preferences"

**Option 3 - Keyboard:**
- Press `⌘+,` (Mac) or `Ctrl+,` (Windows)

### 2.2 Navigate to Microsoft 365 Integration

Scroll down to find the **"Microsoft 365 Integration"** section:

```
┌──────────────────────────────────────────────────────┐
│ Microsoft 365 Integration                            │
├──────────────────────────────────────────────────────┤
│                                                       │
│ Configure Microsoft 365 credentials for calendar     │
│ and email integration.                               │
│                                                       │
│ Client ID:        [                    ] [Show]      │
│                                                       │
│ Client Secret:    [********************] [Show]      │
│                                                       │
│ Email (optional): [                    ]             │
│                                                       │
│ Status: Not configured  [Setup Guide] [Test]         │
│                                                       │
│ 🔒 Credentials are stored securely                   │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### 2.3 Enter Your Credentials

1. **Client ID field:**
   - Paste the Application (client) ID you saved from Step 1.3
   - Example: `12345678-1234-1234-1234-123456789012`

2. **Client Secret field:**
   - Paste the secret value you saved from Step 1.4
   - It will appear as `********************` (hidden for security)

3. **Email field (optional):**
   - Enter your Microsoft 365 email address
   - Example: `your.name@company.com`
   - This helps if you have multiple accounts

### 2.4 Test Connection

Click the **"Test Connection"** button:

**If successful:**
```
Status: ✅ Credentials valid
```

**If error:**
```
Status: ⚠️ O365 library not installed
```
→ See [Troubleshooting](#troubleshooting) section below

### 2.5 Save Settings

1. Scroll to the bottom of the Settings window
2. Click **"Save"** button
3. Your credentials are now saved securely

---

## Step 3: First-Time Authorization

**When:** The first time you use a calendar or email command

**What happens:** Janus will open your web browser and ask you to sign in to Microsoft 365.

### 3.1 Use a Calendar or Email Command

Try one of these commands:
- *"What's my next meeting?"*
- *"Check my email"*
- *"Do I have meetings today?"*

### 3.2 Follow the Browser Prompt

Janus will:
1. Open your web browser automatically
2. Show a Microsoft login page
3. Ask you to sign in (if not already signed in)
4. Ask you to authorize Janus to access your calendar and email

### 3.3 Grant Permission

You'll see a screen like this:

```
┌─────────────────────────────────────────────┐
│ Janus Voice Assistant wants to:             │
│                                             │
│ ✓ Read your calendar                       │
│ ✓ Read your email                          │
│                                             │
│ [Cancel]  [Accept]                          │
└─────────────────────────────────────────────┘
```

Click **"Accept"**

### 3.4 Done!

Janus will save your authorization. You **won't** need to do this again unless:
- The authorization expires (typically after months)
- You change your Microsoft 365 password
- You revoke access

---

---

## Using Microsoft 365 Features

### **Calendar Commands**

Once configured, try these voice commands:

| Command | What Janus Does |
|---------|----------------|
| *"What's my next meeting?"* | Shows your upcoming meeting with time and attendees |
| *"Do I have meetings today?"* | Lists all meetings scheduled for today |
| *"Am I free at 3pm?"* | Checks if you have conflicts at that time |
| *"When is my meeting with Sarah?"* | Searches for meetings with specific people |
| *"What's on my calendar tomorrow?"* | Shows tomorrow's schedule |

**Response Time:** Instant (no need to open Outlook!)

---

### **Email Commands**

| Command | What Janus Does |
|---------|----------------|
| *"Summarize my unread emails"* | Provides a summary of recent unread messages |
| *"How many unread emails?"* | Quick count of inbox messages |
| *"Read my latest email"* | Reads the most recent message |
| *"Did I get email from John?"* | Searches for emails from specific senders |
| *"Any important emails?"* | Checks for high-priority messages |

**Works even if Outlook is closed or minimized!**

---

## Troubleshooting

### "O365 library not installed"

**Problem:** Janus can't find the Microsoft 365 connector library.

**Solution:**
1. Close Janus completely
2. Open a terminal/command prompt
3. Run: `pip install janus[office365]`
4. Restart Janus
5. Go back to Settings → Microsoft 365 Integration
6. Click "Test Connection" again

---

### "Status: Authentication failed"

**Problem:** Your Client ID or Secret might be incorrect.

**Solution:**
1. Go back to [Azure Portal](https://portal.azure.com)
2. Navigate to **App registrations** → **Janus Voice Assistant**
3. Verify your **Application (client) ID** matches what you entered
4. If Client Secret expired:
   - Go to **Certificates & secrets**
   - Create a new client secret
   - Copy the new value
   - Update in Janus Settings

---

### "No calendar/mailbox found"

**Problem:** Your Microsoft 365 account might not have a calendar or mailbox set up.

**Solution:**
1. Open Outlook on the web ([outlook.office.com](https://outlook.office.com))
2. Verify you can see your calendar and inbox
3. If empty or error, contact your IT administrator
4. Once working in Outlook web, try Janus again

---

### Authorization expired

**Problem:** The authorization token has expired (typically after several months).

**Solution:**
1. Just use any calendar or email command
2. Janus will automatically prompt you to re-authorize
3. Follow the browser prompt to sign in again
4. Click "Accept" when asked
5. Done! Authorization renewed

---

### Commands not working

**Problem:** Janus doesn't recognize calendar/email commands.

**Checklist:**
- ✅ Did you complete all 3 setup steps?
- ✅ Did you click "Save" after entering credentials?
- ✅ Did you authorize Janus in the browser?
- ✅ Is your internet connection working?
- ✅ Can you access [outlook.office.com](https://outlook.office.com)?

**Still not working?**
1. Open Janus Settings
2. Microsoft 365 Integration section
3. Click "Test Connection"
4. Check the status message for specific errors

---

## Privacy & Security

### What Janus Can Access

**✅ Janus CAN:**
- Read your calendar events (title, time, attendees, location)
- Read your emails (subject, sender, body text)
- Count unread messages
- Search for specific emails

**❌ Janus CANNOT:**
- Send emails on your behalf
- Create or modify calendar events
- Delete anything
- Access files in OneDrive/SharePoint
- Access Teams messages
- See anything outside calendar and email

### How Data is Stored

- **Credentials:** Saved locally in Janus configuration file
- **Authorization token:** Cached on your computer
- **Calendar/Email data:** Fetched on-demand, **not stored permanently**
- **No cloud sync:** Everything stays on your device

### Revoking Access

If you want to remove Janus's access:

1. Go to [Microsoft Account Apps & Permissions](https://account.microsoft.com/privacy/app-permissions)
2. Find "Janus Voice Assistant" in the list
3. Click "Remove"
4. Janus will no longer be able to access your data

To re-enable later, just use a calendar/email command and re-authorize.

---

## Additional Help

### Need More Assistance?

- **Email support:** Check your Janus installation for support contact
- **Community:** Join the Janus user community
- **Documentation:** See other user guides in `docs/user/`

### Providing Feedback

Encountered a bug or have a suggestion?
1. Note the exact command you used
2. What you expected vs. what happened
3. Any error messages shown
4. Report through your Janus support channel

---

**[← Back to Index](README.md)**
