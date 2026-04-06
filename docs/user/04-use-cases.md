# �� Janus User Manual - Mastering Janus: Use Cases

**[← Previous: Getting Started](03-getting-started.md)** | **[Back to Index](README.md)** | **[Next: Personalization →](05-personalization.md)**

---

# 📘 Janus User Manual - Mastering Janus: Use Cases

**[← Previous: Getting Started](03-getting-started.md)** | **[Back to Index](README.md)** | **[Next: Personalization →](05-personalization.md)**

---

# 4. Mastering Janus: Use Cases

## Web Navigation

### **Intelligent Search**

**Simple Search:**

*"Search for healthy breakfast recipes"*

**What Janus does:**
1. Opens your default browser (if not open)
2. Navigates to your default search engine
3. Types "healthy breakfast recipes"
4. Presses Enter
5. Waits for results to load

**Advanced Search:**

*"Search for Python tutorials published in the last year"*

Janus understands time constraints and can add qualifiers to the search.

---

### **Video Playback**

**Examples:**
- *"Play relaxing piano music on YouTube"*
- *"Put on some jazz"*
- *"Show me cooking tutorials"*
- *"Play the latest news"*

**What Janus does:**
1. Opens YouTube (browser or app)
2. Searches for the content
3. Clicks on first video (or best match)
4. Starts playback
5. Optionally: full screen, adjust volume

---

### **Page Summarization**

**Command:** *"Summarize this article"* or *"What's this page about?"*

**What Janus does:**
1. Captures visible page content
2. Extracts main text (ignoring ads, navigation)
3. Sends to AI for summarization
4. Presents concise summary

**Example Output:**
```
📄 Page Summary

Source: TechCrunch article
Title: "The Future of AI Assistants"

Summary (200 words):
This article discusses the evolution of AI assistants from
simple command-response systems to intelligent agents capable
of multi-step reasoning. Key points include:

• Privacy concerns with cloud-based systems
• Advantages of local processing
• Integration with computer vision
• Predictions for 2025 and beyond

Main takeaway: Local AI assistants will become mainstream
as privacy concerns grow and hardware capabilities improve.

[Read Full Article] [Ask Questions]
```

---

## Productivity Workflows

### **Email Management**

**Opening Email:**
- *"Open Outlook"* / *"Open Mail"*
- *"Check my email"*

**Composing:**
- *"Compose email to john@company.com"*
- *"Write new email"*
- *"Reply to this email"*

**Complex Example:**

*"Open Outlook, find emails from Sarah this week, and mark them all as read"*

**What Janus does:**
1. Launches Outlook
2. Uses search to filter: from:sarah@company.com date:thisweek
3. Selects all results
4. Marks as read
5. Reports: "Marked 7 emails as read"

---

### **Document Creation & Editing**

**Creating Documents:**
- *"Create new Word document called Q4 Report"*
- *"Make a new spreadsheet named Budget 2024"*
- *"Open blank presentation"*

**Editing:**
- *"Bold this text"*
- *"Change font to Arial size 14"*
- *"Insert image from Desktop"*
- *"Create table with 5 rows and 3 columns"*

**Complex Workflow:**

*"Create a Word document, write 'Meeting Notes' as the title in Heading 1 style, then create a bulleted list"*

---

### **File Organization**

**Creating Folders:**
- *"Create folder named Project Alpha in Documents"*
- *"Make new folder here"*

**Moving Files:**
- *"Move this file to Desktop"*
- *"Move all PDFs from Downloads to Documents"*

**Organizing:**
- *"Sort files by date modified"*
- *"Group files by type"*
- *"Find all documents containing 'budget'"*

**Complex Example:**

*"Move all files from Downloads older than 30 days to Archive folder"*

---

## Direct SaaS Application Access (Deep Links)

**TICKET-BIZ-003: Generic Deep Linker**

Janus can open SaaS applications directly using deep links, bypassing browser dialogs and "Open in app?" prompts. This provides seamless access to Zoom meetings, Spotify tracks, Notion pages, and many other applications.

### **Joining Meetings**

**Zoom:**
- *"Lance le call Zoom 123-456-789"*
- *"Open Zoom meeting 987654321"*
- *"Join Zoom 555-444-333"*

**Microsoft Teams:**
- *"Open Teams meeting 19%3ameeting_abc123"*
- *"Join Teams call"*

**What Janus does:**
1. Opens the application directly (no browser)
2. Joins the meeting immediately
3. Avoids "Open Zoom?" dialogs

---

### **Music & Media**

**Spotify:**
- *"Play Spotify track 3n3Ppam7vgaVa1iaRUc9Lp"*
- *"Open Spotify playlist 37i9dQZF1DXcBWIGoYBM5M"*
- *"Play album on Spotify 1DFixLWuPkv3KT3TnV35m3"*

**What Janus does:**
1. Opens Spotify application
2. Navigates directly to the track/album/playlist
3. Starts playback

---

### **Workspace & Documentation**

**Notion:**
- *"Ouvre la page Notion My-Project"*
- *"Open Notion page Team-Meeting-Notes"*
- *"Show Notion workspace myworkspace/page-id-123"*

**Figma:**
- *"Open Figma file abc123"*
- *"Show design file in Figma"*

**What Janus does:**
1. Opens the native application
2. Navigates directly to the page/file
3. No browser tabs needed

---

### **Team Communication**

**Slack:**
- *"Open Slack channel General"*
- *"Go to Slack team T123ABC channel C456DEF"*
- *"Show DM with [person]"*

**Discord:**
- *"Open Discord server 123456789"*
- *"Go to Discord channel 987654321"*

---

### **Development Tools**

**GitHub:**
- *"Open GitHub repo microsoft/vscode"*
- *"Show issue 123 on GitHub"*

**VS Code:**
- *"Open file in VS Code /Users/username/project/file.js"*
- *"Open workspace in Code"*

**Jira:**
- *"Open Jira issue PROJ-123"*
- *"Show ticket PROJ-456"*

**Trello:**
- *"Open Trello card abc123def"*
- *"Show Trello board"*

---

### **Supported Applications**

Janus supports deep links for:
- ✅ **Zoom** - Video meetings
- ✅ **Microsoft Teams** - Meetings and chats
- ✅ **Spotify** - Music streaming
- ✅ **Notion** - Workspace pages
- ✅ **Slack** - Team communication
- ✅ **Discord** - Community servers
- ✅ **Figma** - Design collaboration
- ✅ **GitHub** - Code repositories
- ✅ **Jira** - Issue tracking
- ✅ **Trello** - Project boards
- ✅ **VS Code** - Code editor
- ✅ **Calendar** - Calendar events (macOS/iOS)

For complete documentation and examples, see [Deep Links Guide](11-deep-links.md).

---

## Smart Clipboard (Context Copié)

### **🎯 The Power of "This" and "That"**

Janus can automatically understand what you're referring to when you say "this", "that", "it", or "ça" by capturing your clipboard content. Simply copy something (Ctrl+C / Cmd+C), then give your command!

**How it works:**
1. Copy any text or code (Ctrl+C)
2. Say "Janus" (wake word)
3. Give your command using "this", "that", "it", etc.
4. ✨ Janus automatically knows you're referring to the clipboard!

---

### **Code Explanation**

**Scenario:** You're reading code and want to understand it.

**Steps:**
1. Select a function/code snippet
2. Copy it (Ctrl+C)
3. Say: *"Janus, explique ce code"* or *"Janus, explain this code"*

**Example:**

```python
# You copy this function:
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
```

**You say:** *"Janus, explique ce code"*

**Janus responds:**
```
📝 Code Explanation

This is a quicksort algorithm implementation in Python. It's a
divide-and-conquer sorting algorithm that:

1. Chooses a pivot element (middle of array)
2. Partitions the array into three parts:
   • left: elements smaller than pivot
   • middle: elements equal to pivot
   • right: elements greater than pivot
3. Recursively sorts left and right partitions
4. Combines results

Time complexity: O(n log n) average, O(n²) worst case
Space complexity: O(n) due to list comprehensions

This implementation is clear but not the most memory-efficient.
```

---

### **Error Debugging**

**Scenario:** You encounter an error and need help understanding it.

**Steps:**
1. Copy the error message
2. Say: *"Janus, que signifie cette erreur ?"* or *"Janus, what does this error mean?"*

**Example:**

```
# You copy this error:
TypeError: unsupported operand type(s) for +: 'int' and 'str'
    at line 42: result = age + name
```

**You say:** *"Janus, que signifie cette erreur ?"*

**Janus responds:**
```
⚠️ Error Explanation

This is a TypeError occurring because you're trying to add (use the +
operator) between an integer and a string, which Python doesn't allow.

In your code:
• `age` is an integer (number)
• `name` is a string (text)
• Python can't add these different types together

To fix this:
1. If concatenating: result = str(age) + name
2. If doing math: result = age + int(name)
3. Use f-strings: result = f"{age}{name}"

The error is at line 42, so check that line in your code.
```

---

### **Text Translation**

**Scenario:** You need to translate text quickly.

**Steps:**
1. Copy the text to translate
2. Say: *"Janus, traduis ça en anglais"* or *"Janus, translate this to English"*

**Example:**

```
# You copy:
Le développement durable est essentiel pour l'avenir de notre planète.
Nous devons agir maintenant pour préserver l'environnement.
```

**You say:** *"Janus, traduis ça en anglais"*

**Janus responds:**
```
🌍 Translation

Original (French):
Le développement durable est essentiel pour l'avenir de notre
planète. Nous devons agir maintenant pour préserver l'environnement.

English Translation:
Sustainable development is essential for the future of our planet.
We must act now to preserve the environment.
```

---

### **Code Improvement**

**Scenario:** You want suggestions to improve your code.

**Steps:**
1. Copy the code snippet
2. Say: *"Janus, améliore ce code"* or *"Janus, improve this code"*

**Example:**

```python
# You copy:
for i in range(len(items)):
    print(items[i])
    
total = 0
for i in range(len(prices)):
    total = total + prices[i]
```

**You say:** *"Janus, améliore ce code"*

**Janus responds:**
```
💡 Code Improvements

Original code can be improved for better Pythonic style:

Suggested improvements:

# More Pythonic iteration
for item in items:
    print(item)

# Use sum() with generator expression
total = sum(prices)

Why these are better:
• More readable and concise
• Faster execution (built-in sum() is optimized)
• Less error-prone (no index mistakes)
• Follows Python's "There should be one obvious way"

Additional tip: If you need the index, use enumerate():
for i, item in enumerate(items):
    print(f"{i}: {item}")
```

---

### **Text Summarization**

**Scenario:** You have a long text and need a quick summary.

**Steps:**
1. Copy the text
2. Say: *"Janus, résume ce texte"* or *"Janus, summarize this"*

**Example:**

```
# You copy a long article excerpt...
```

**You say:** *"Janus, résume ce texte"*

**Janus responds:**
```
📄 Summary

The text discusses artificial intelligence's impact on modern
work environments. Key points:

• AI is automating routine tasks
• Workers need to adapt with new skills
• Human creativity remains essential
• Ethical considerations are important
• Balance between efficiency and employment

Main message: AI is a tool to enhance human work, not replace it
entirely. Adaptation and lifelong learning are crucial.

(Summarized from 850 words to 65 words)
```

---

### **⏱️ Time Window: 10 Seconds**

**Important:** For security and accuracy, Janus only uses clipboard content that was copied within the last **10 seconds**.

**Why?**
- Prevents accidental use of old clipboard data
- Ensures you're referencing what you intend
- Protects against unintended data exposure

**Best Practice:**
Copy → Speak immediately for best results!

If Janus doesn't seem to "see" your clipboard:
1. Copy the content again
2. Say "Janus" right after copying (within 10 seconds)
3. Give your command

---

### **Supported Languages**

Smart Clipboard works in both **French** and **English**:

**French phrases:**
- *"Explique ça"* / *"Explique ce code"*
- *"Corrige ça"* / *"Améliore ce code"*
- *"Traduis ça"*
- *"Résume ce texte"*
- *"Que signifie cette erreur ?"*

**English phrases:**
- *"Explain this"* / *"Explain this code"*
- *"Fix this"* / *"Improve this code"*
- *"Translate this"*
- *"Summarize this"*
- *"What does this error mean?"*

---

## Conversation Mode

### **Asking About Your Screen**

**Command:** *"What do you see on my screen?"*

**Response Example:**
```
🔍 Screen Analysis

I see a web browser (Chrome) displaying a GitHub repository
page. The repository is called "Janus" and appears to be a
voice control automation project.

Key elements visible:
• README.md file showing documentation
• Folder structure on the left (docs/, janus/, tests/)
• Stats: 151 test files, last updated 2 days ago
• The page indicates Python as the primary language

Current URL: github.com/BenHND/Janus
Active window: Google Chrome
```

---

### **Error Detection**

**Command:** *"Is there an error on the screen?"*

**If error found:**
```
⚠️ Error Detected

Yes, I see an error dialog:

Title: "File Not Found"
Message: "The document 'Budget.xlsx' could not be opened
because it does not exist in the specified location."

Buttons available: [OK] [Cancel]

Would you like me to:
1. Search for 'Budget.xlsx' on your computer
2. Check recent files
3. Close this dialog
```

---

### **Getting Contextual Help**

**Command:** *"How do I fix this?"*

Janus analyzes the current error/situation and provides solutions.

**Example Response:**
```
💡 Suggested Solutions

Based on the "File Not Found" error, here are 3 options:

1. **Search for the file**
   Say: "Search for Budget.xlsx"
   I'll look in common locations (Documents, Downloads, Desktop)

2. **Check if file was moved**
   Say: "Show me recent file movements"
   I'll check if the file was moved to another folder

3. **Restore from backup**
   Say: "Open Time Machine" (Mac) or "Open File History" (Windows)
   You can restore the file if it was backed up

Which would you like to try?
```

---

## Complex Commands (Multi-Step Workflows)

### **Cross-Application Workflow**

**Command:**
```
"Open Chrome, go to Google Drive, download the Budget spreadsheet,
then open it in Excel"
```

**Janus Execution Plan:**
```
📋 Plan Generated (7 steps)

1. Launch/focus Google Chrome
2. Navigate to drive.google.com
3. Wait for Drive to load
4. Search for "Budget" in Drive
5. Use vision to locate spreadsheet
6. Download file (right-click → Download)
7. Open downloaded file in Microsoft Excel
8. Verify file opened successfully

Estimated time: 15-25 seconds
Dependencies: Internet connection, Google account logged in

[Execute Plan] [Modify] [Cancel]
```

**Step-by-Step Execution:**
```
⚡ Step 1/7: Opening Chrome...
✓ Chrome focused

⚡ Step 2/7: Navigating to drive.google.com...
✓ Page loaded (2.1s)

⚡ Step 3/7: Waiting for Drive interface...
✓ Drive ready

⚡ Step 4/7: Searching for 'Budget'...
✓ Search complete (3 results)

⚡ Step 5/7: Locating spreadsheet...
🔍 Using vision to find file...
✓ Found: Budget_Q4.xlsx (modified 3 days ago)

⚡ Step 6/7: Downloading file...
✓ Download started
⏳ Waiting for download... (4.2 MB)
✓ Download complete

⚡ Step 7/7: Opening in Excel...
✓ Excel launched
✓ File opened: Budget_Q4.xlsx

✅ All steps complete!
Total time: 18.7 seconds

The Budget spreadsheet is now open in Excel.
```

---

### **Research Workflow**

**Command:**
```
"Search for articles about renewable energy, open the top 3 results
in separate tabs, then summarize each one"
```

**Execution:**
```
⚡ Step 1: Searching Google for "articles about renewable energy"...
✓ Results loaded

⚡ Step 2: Opening top 3 results in new tabs...
✓ Tab 1: "Solar Power Advances 2024" (nature.com)
✓ Tab 2: "Wind Energy Solutions" (energy.gov)
✓ Tab 3: "Renewable Energy Economics" (forbes.com)

⚡ Step 3: Analyzing Tab 1...
📄 Summary 1:
Article from Nature discussing recent advances in solar panel
efficiency. Key finding: New perovskite cells achieve 29.5%
efficiency, up from 25% in 2023...

⚡ Step 4: Analyzing Tab 2...
📄 Summary 2:
Government report on wind energy capacity. US wind farms
generated 425 TWh in 2024, up 12% from previous year...

⚡ Step 5: Analyzing Tab 3...
📄 Summary 3:
Economic analysis of renewable energy costs. Solar and wind
now cheaper than fossil fuels in most markets...

✅ Complete! All 3 articles summarized.

[Save Summaries] [Continue Research] [Done]
```

---

### **Team Communication Workflow**

**Command:**
```
"Open Teams, find the latest message in Project Alpha channel,
summarize it, and email the summary to sarah@company.com"
```

**Execution:**
```
⚡ Step 1: Opening Microsoft Teams...
✓ Teams launched

⚡ Step 2: Navigating to Project Alpha channel...
✓ Channel found and selected

⚡ Step 3: Finding latest message...
🔍 Using vision to locate most recent message...
✓ Latest message from Mike (2 hours ago)

⚡ Step 4: Extracting message content...
📝 Message captured:
"Hey team, we've completed the frontend redesign and it's
ready for testing. Please review the staging environment at
staging.projectalpha.com. Deadline for feedback is Friday."

⚡ Step 5: Generating summary...
📄 Summary:
Mike reports frontend redesign complete and ready for testing.
Action required: Review staging site by Friday.
Link: staging.projectalpha.com

⚡ Step 6: Opening email client...
✓ Outlook opened

⚡ Step 7: Composing email to sarah@company.com...
✓ New email created
To: sarah@company.com
Subject: Project Alpha Update Summary

Body:
Hi Sarah,

Latest update from Project Alpha channel:

Mike reports the frontend redesign is complete and ready for
testing. The team needs to review the staging environment at
staging.projectalpha.com by Friday.

This is an automated summary from Janus.

[Edit Email] [Send Now] [Cancel]
```

**Result:** Email ready to review and send. You can edit it or say *"Send it"* to send immediately.

---

