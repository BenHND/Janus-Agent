# 🎯 Salesforce CRM Integration

**[← Back to Index](README.md)**

---

## What You Can Do

Once configured, Janus can access your Salesforce CRM data **instantly**, without opening a browser or clicking through Salesforce:

### **👤 Contact Commands**
- *"Who is the main contact at Acme Corp?"* - Instant response with contact details
- *"Find contact Jane Smith"* - Search for specific contacts
- *"What's the title of John Doe?"* - Get contact information
- *"Show me contacts at TechCorp"* - Search by company name

### **💼 Opportunity Commands**
- *"What's the status of opportunity 006XXX?"* - Get opportunity details
- *"Show opportunities for Acme Corp"* - List deals by account
- *"What deals are in negotiation?"* - Search by stage

### **🏢 Account Commands**
- *"Tell me about Acme Corporation"* - Get account information
- *"What's the industry for TechCorp?"* - Account details

---

## Setup Overview

Setting up Salesforce integration requires **2 simple steps**:

1. **Get your Salesforce credentials** (5 minutes)
2. **Enter credentials in Janus Settings** (copy & paste)

**Time Required:** About 10 minutes total

**What You Need:**
- Salesforce account (Professional, Enterprise, or Developer edition)
- Your Salesforce username (email)
- Your Salesforce password
- Your Security Token
- 10 minutes of time

---

## Step 1: Get Your Salesforce Security Token

**Why?** Salesforce requires a security token in addition to your password when accessing the API from external applications.

**How long?** 5 minutes

### 1.1 Log in to Salesforce

1. Go to your Salesforce instance
   - Production: [login.salesforce.com](https://login.salesforce.com)
   - Sandbox: [test.salesforce.com](https://test.salesforce.com)
2. Sign in with your username and password

### 1.2 Access Your Settings

1. Click on your **profile icon** in the top-right corner
2. Select **"Settings"** from the dropdown menu
3. Or navigate to **Setup** → Search for "Personal Information"

### 1.3 Reset Your Security Token

1. In the left sidebar, under **"My Personal Information"**, click **"Reset My Security Token"**
2. Click the **"Reset Security Token"** button

   ```
   ┌─────────────────────────────────────────────┐
   │ Security Token                              │
   ├─────────────────────────────────────────────┤
   │                                             │
   │ Your security token has been emailed to:    │
   │ your.email@company.com                      │
   │                                             │
   │ The security token will be sent to the      │
   │ email address associated with your account. │
   │                                             │
   └─────────────────────────────────────────────┘
   ```

3. **Check your email** - You'll receive a message with subject "Your new Salesforce security token"
4. **Copy the security token** from the email (it's a long string like `aBc123XyZ...`)

### 1.4 Save Your Credentials

Keep these three items in a safe place:

1. **Username:** `your.email@company.com`
2. **Password:** `YourPassword123`
3. **Security Token:** `aBc123XyZ...` (from the email)

⚠️ **IMPORTANT:** Keep your security token private and secure!

---

## Step 2: Configure Janus Settings

**Where:** Open Janus → Settings → Salesforce Integration

### 2.1 Open Janus Settings

**Option 1 - Voice:**
- Say: *"Open settings"* or *"Open preferences"*

**Option 2 - Menu:**
- Click the Janus menu icon
- Select "Settings" or "Preferences"

**Option 3 - Keyboard:**
- Press `⌘+,` (Mac) or `Ctrl+,` (Windows)

### 2.2 Navigate to Salesforce Integration

Scroll down to find the **"Salesforce Integration"** section:

```
┌──────────────────────────────────────────────────────┐
│ Salesforce CRM Integration                           │
├──────────────────────────────────────────────────────┤
│                                                       │
│ Configure Salesforce credentials for CRM access.     │
│                                                       │
│ Username:         [                    ]             │
│                                                       │
│ Password:         [********************] [Show]      │
│                                                       │
│ Security Token:   [********************] [Show]      │
│                                                       │
│ Domain:           ◉ Production (login)               │
│                   ○ Sandbox (test)                   │
│                                                       │
│ Status: Not configured  [Setup Guide] [Test]         │
│                                                       │
│ 🔒 Credentials are stored securely                   │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### 2.3 Enter Your Credentials

1. **Username field:**
   - Enter your Salesforce username (email)
   - Example: `your.name@company.com`

2. **Password field:**
   - Enter your Salesforce password
   - It will appear as `********************` (hidden for security)

3. **Security Token field:**
   - Paste the security token you received by email
   - It will appear as `********************` (hidden for security)

4. **Domain:**
   - Select **"Production (login)"** for regular Salesforce
   - Select **"Sandbox (test)"** if using a test environment

### 2.4 Test Connection

Click the **"Test Connection"** button:

**If successful:**
```
Status: ✅ Connected to Salesforce
Instance: https://yourcompany.my.salesforce.com
```

**If error:**
```
Status: ⚠️ simple-salesforce library not installed
```
→ See [Troubleshooting](#troubleshooting) section below

**If authentication failed:**
```
Status: ❌ Authentication failed
```
→ Double-check your username, password, and security token

### 2.5 Save Settings

1. Scroll to the bottom of the Settings window
2. Click **"Save"** button
3. Your credentials are now saved securely

---

## Using Salesforce Features

### **Contact Commands**

Once configured, try these voice commands:

| Command | What Janus Does |
|---------|----------------|
| *"Who is the contact at Acme Corp?"* | Searches for and displays contact information |
| *"Find Jane Smith in Salesforce"* | Shows Jane's title, email, phone, and account |
| *"What's John's email address?"* | Retrieves contact email from CRM |
| *"Show me the contact for TechCorp"* | Finds the main contact at that account |

**Response Time:** < 3 seconds (10x faster than browser automation!)

---

### **Opportunity Commands**

| Command | What Janus Does |
|---------|----------------|
| *"Show opportunity 006XXX"* | Displays opportunity details (stage, amount, close date) |
| *"What opportunities are there for Acme?"* | Lists all opportunities for that account |
| *"What's the deal value for opportunity 006XXX?"* | Shows opportunity amount and probability |

---

### **Account Commands**

| Command | What Janus Does |
|---------|----------------|
| *"Tell me about Acme Corporation"* | Shows account details (industry, website, phone) |
| *"What industry is TechCorp in?"* | Retrieves account industry information |

---

### **Hybrid Mode: Viewing vs. Editing**

Janus uses a **smart hybrid approach**:

**📖 Reading (via API - Fast):**
- Contact searches
- Opportunity details
- Account information
- **No browser needed** - instant structured data

**✏️ Editing (via Browser - Safe):**
- To edit a contact, Janus generates a direct URL
- Opens Salesforce in your browser
- You or Janus can make changes safely

**Example:**
```
You: "Edit contact Jane Smith"

Janus: "Opening Jane Smith's contact page in Salesforce..."
→ Browser opens to: https://yourcompany.my.salesforce.com/lightning/r/Contact/003XXX/view
→ You can now edit safely in the familiar Salesforce interface
```

This keeps your data safe while making reads super fast!

---

## Troubleshooting

### "simple-salesforce library not installed"

**Problem:** Janus can't find the Salesforce connector library.

**Solution:**
1. Close Janus completely
2. Open a terminal/command prompt
3. Run: `pip install janus[salesforce]`
4. Restart Janus
5. Go back to Settings → Salesforce Integration
6. Click "Test Connection" again

---

### "Status: Authentication failed"

**Problem:** Your credentials might be incorrect.

**Solution:**
1. **Check your username** - It should be your Salesforce email
2. **Verify your password** - Try logging into Salesforce web to confirm
3. **Reset your security token:**
   - Log into Salesforce
   - Settings → Reset My Security Token
   - Check your email for the new token
   - Update in Janus Settings
4. **Check domain selection:**
   - Production for regular Salesforce (login.salesforce.com)
   - Sandbox for test environments (test.salesforce.com)

---

### "Invalid username, password, security token"

**Problem:** One of your credentials is wrong.

**Common Issues:**
- **Password changed?** If you recently changed your Salesforce password, you need a new security token
- **Security token missing?** The security token is required and is separate from your password
- **Extra spaces?** Make sure there are no extra spaces when copying/pasting

**Solution:**
1. Log into Salesforce web to verify your password works
2. Reset your security token (see Step 1.3)
3. Copy credentials carefully (no extra spaces)
4. Re-enter in Janus Settings
5. Click "Test Connection"

---

### "No data returned" or "Contact not found"

**Problem:** The contact, opportunity, or account doesn't exist or you don't have access.

**Solution:**
1. Verify the record exists in Salesforce
2. Check your Salesforce permissions - you can only access data you have permission to see
3. Try searching with different terms:
   - Use full names for contacts
   - Use account names for opportunities
   - Use exact IDs when available

---

### Commands not working

**Problem:** Janus doesn't recognize Salesforce commands.

**Checklist:**
- ✅ Did you complete both setup steps?
- ✅ Did you click "Save" after entering credentials?
- ✅ Did you test the connection successfully?
- ✅ Is your internet connection working?
- ✅ Can you access Salesforce web normally?

**Still not working?**
1. Open Janus Settings
2. Salesforce Integration section
3. Click "Test Connection"
4. Check the status message for specific errors

---

## Privacy & Security

### What Janus Can Access

**✅ Janus CAN:**
- Read contact information (name, title, email, phone, account)
- Read opportunity data (name, stage, amount, close date)
- Read account information (name, industry, website)
- Search for records you have permission to view

**❌ Janus CANNOT:**
- Create, edit, or delete records via API (use browser for safety)
- Access records you don't have permission to see
- See data from other Salesforce orgs
- Access anything outside of standard Salesforce objects

### How Data is Stored

- **Credentials:** Saved locally in Janus configuration file (encrypted)
- **API responses:** Fetched on-demand, **not stored permanently**
- **No cloud sync:** Everything stays on your device
- **No logging:** CRM data is never logged to files

### Hybrid Mode Security

For editing operations, Janus opens Salesforce in your browser:
- You maintain full control
- Changes happen in the familiar Salesforce UI
- No risk of accidental API modifications
- All Salesforce validation rules apply

### Revoking Access

If you want to remove Janus's access:

1. Open Janus Settings
2. Salesforce Integration section
3. Clear all credential fields
4. Click "Save"
5. Or change your Salesforce password (will require new security token)

---

## Advanced Configuration

### Using with Multiple Salesforce Orgs

If you have access to multiple Salesforce organizations:

1. Janus can only connect to one org at a time
2. To switch orgs:
   - Go to Settings → Salesforce Integration
   - Enter credentials for the other org
   - Click "Save"

### Sandbox vs. Production

**Sandbox (for testing):**
- Domain: `test.salesforce.com`
- Select "Sandbox (test)" in Domain field
- Use sandbox credentials

**Production (for real data):**
- Domain: `login.salesforce.com`
- Select "Production (login)" in Domain field
- Use production credentials

### API Rate Limits

Salesforce has API rate limits based on your license:
- Janus makes minimal API calls (typically 1-2 per command)
- Contact searches, opportunity lookups are very lightweight
- You're unlikely to hit limits with normal usage
- If you do, wait a few minutes and try again

---

## Additional Help

### Need More Assistance?

- **User Manual:** See [USER_MANUAL.md](USER_MANUAL.md) for general Janus help
- **Architecture:** See [docs/architecture/23-salesforce-crm-integration.md](../architecture/23-salesforce-crm-integration.md) for technical details
- **Community:** Join the Janus user community

### Providing Feedback

Encountered a bug or have a suggestion?
1. Note the exact command you used
2. What you expected vs. what happened
3. Any error messages shown
4. Report through your Janus support channel

---

## Quick Reference Card

### One-Time Setup
```
1. Get Salesforce security token (email)
2. Open Janus Settings
3. Enter: Username, Password, Security Token
4. Select domain (Production/Sandbox)
5. Click Test → Save
```

### Common Commands
```
"Who is the contact at Acme Corp?"
"Find Jane Smith in Salesforce"
"Show opportunity 006XXX"
"What opportunities for Acme?"
"Tell me about TechCorp account"
"Edit contact John Doe" → Opens browser
```

### Performance
- Contact search: < 3 seconds
- 10x faster than browser automation
- No screenshots needed
- Works even when Salesforce is closed

---

**[← Back to Index](README.md)**
