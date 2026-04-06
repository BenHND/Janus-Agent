# 📘 Janus User Manual - Getting Started Guide

**[← Previous: Installation](02-installation.md)** | **[Back to Index](README.md)** | **[Next: Use Cases →](04-use-cases.md)**

---

# 📘 Janus User Manual - Getting Started Guide

**[← Previous: Installation](02-installation.md)** | **[Back to Index](README.md)** | **[Next: Use Cases →](04-use-cases.md)**

---

# 3. Getting Started Guide

## Understanding the Interface (Overlay)

Janus features a minimal, non-intrusive overlay that appears in the corner of your screen (customizable position).

### **The Overlay Window**

```
┌─────────────────────────────┐
│   🎤 Janus                  │
│   ● Listening...            │
│   ────────────────          │
│   Last: Opened Safari       │
│   [Settings] [Stop]         │
└─────────────────────────────┘
```

**Components:**
- **Status Icon** - Shows current state (● ◐ ⚡ ✓ ✗)
- **Status Text** - What Janus is doing
- **Last Action** - Your previous command
- **Quick Buttons** - Settings and emergency stop

### **Visual States Explained**

#### **🎤 Listening (Green)**

```
┌─────────────────────────────┐
│   🎤 Janus                  │
│   ● Listening...            │
└─────────────────────────────┘
```

**Meaning:** Janus is ready and waiting for your voice command.

**What to do:** Speak your command clearly and naturally.

**Visual:** Green pulsing circle, soft glow effect.

**Sound:** Subtle "ready" chime (optional, can be disabled).

---

#### **🔊 Processing (Blue)**

```
┌─────────────────────────────┐
│   🎤 Janus                  │
│   ◐ Processing...           │
│   "Open Safari and..."      │
└─────────────────────────────┘
```

**Meaning:** Janus heard you and is converting speech to text.

**What to do:** Wait briefly (usually <1 second). You'll see your words appear.

**Visual:** Blue spinning indicator, shows recognized text as it processes.

**Duration:** Typically 0.5-2 seconds depending on command length.

---

#### **⚡ Executing (Yellow/Orange)**

```
┌─────────────────────────────┐
│   🎤 Janus                  │
│   ⚡ Executing (Step 2/3)   │
│   Navigating to YouTube...  │
│   [Stop]                    │
└─────────────────────────────┘
```

**Meaning:** Janus is performing the requested action(s).

**What to do:** Watch as your command is executed. You can stop anytime by clicking [Stop] or saying "Stop".

**Visual:** Orange/yellow progress indicator, shows current step, displays detailed status.

**Duration:** Varies by command complexity (instant to several seconds).

---

#### **✅ Done (Green)**

```
┌─────────────────────────────┐
│   🎤 Janus                  │
│   ✓ Done!                   │
│   Opened Safari             │
└─────────────────────────────┘
```

**Meaning:** Command completed successfully!

**What to do:** The overlay auto-returns to Listening state after 2 seconds.

**Visual:** Green checkmark, brief success animation.

**Sound:** Success chime (optional).

---

#### **❌ Error (Red)**

```
┌─────────────────────────────┐
│   🎤 Janus                  │
│   ✗ Error                   │
│   Could not find Safari     │
│   [Retry] [Cancel]          │
└─────────────────────────────┘
```

**Meaning:** Something went wrong.

**What to do:** Read the error message, click [Retry] to try again or [Cancel] to dismiss.

**Visual:** Red X icon, error details displayed.

**Common errors:**
- Application not found
- Permissions denied
- Network timeout (for web commands)
- Vision failed to locate element

---

## Customizing the Overlay

### **Position:**
- Drag the overlay to any corner or edge
- Settings → Interface → Overlay Position
- Options: Top-left, Top-right, Bottom-left, Bottom-right, Center

### **Size:**
- Small (compact) - minimal space
- Medium (default) - balanced
- Large (detailed) - shows more info

### **Opacity:**
- Adjustable from 50% to 100%
- Auto-hide when not in use (optional)

### **Always on Top:**
- Enabled (default) - overlay stays visible
- Disabled - can be hidden by other windows

---

## Your First Commands

Let's practice with progressively complex commands.

### **Level 1: Simple Commands**

These execute instantly and teach you the basics.

**Opening Applications:**
- *"Open Safari"* / *"Open Chrome"*
- *"Launch Microsoft Word"*
- *"Start Spotify"*
- *"Open Calculator"*

**Closing Applications:**
- *"Close Safari"*
- *"Quit Chrome"*
- *"Exit Word"*

**Switching Applications:**
- *"Switch to Chrome"*
- *"Focus Safari"*
- *"Go to Mail"*

**System Commands:**
- *"Show desktop"*
- *"Minimize all windows"*
- *"Take a screenshot"*

---

### **Level 2: Navigation Commands**

These involve going places and finding things.

**Web Navigation:**
- *"Go to google.com"*
- *"Navigate to youtube.com"*
- *"Open reddit.com in a new tab"*

**File System:**
- *"Open Documents folder"*
- *"Show Downloads"*
- *"Go to Desktop"*

**Application Navigation:**
- *"Go to next tab"*
- *"Switch to previous tab"*
- *"Scroll down"*
- *"Scroll to top"*

---

### **Level 3: Action Commands**

These perform specific actions.

**Text Operations:**
- *"Copy"* / *"Copy this"*
- *"Paste"*
- *"Cut this text"*
- *"Select all"*

**Window Management:**
- *"Maximize this window"*
- *"Minimize Chrome"*
- *"Close this tab"*

**Search:**
- *"Search for cat videos"*
- *"Find [query]"*
- *"Look up [topic]"*

---

### **Level 4: Multi-Step Commands**

Chain multiple actions together.

**Examples:**
- *"Open Chrome and go to Gmail"*
- *"Copy this and paste it there"*
- *"Close all tabs except this one"*
- *"Search for pizza places and open the first result"*

**What Makes This Special:**
Janus intelligently plans and executes each step in sequence, handling timing, errors, and verification automatically.

---

## Interrupting the Agent (Emergency Stop)

Sometimes you need to stop Janus immediately.

### **Method 1: Voice Command (Recommended)**

**Say:** *"Stop"* or *"Cancel"* or *"Abort"*

**When to use:** Anytime you want to halt execution verbally.

**Advantage:** Fastest if Janus is listening.

**Triggers:** "stop", "cancel", "abort", "halt", "cease", "quit"

---

### **Method 2: Mouse Corner (Fastest Emergency Stop)**

**Action:** Quickly move your mouse cursor to any screen corner.

**How it works:**
1. Move cursor to corner (any corner)
2. Janus detects rapid corner hit
3. Immediately cancels all actions
4. Returns to listening state

**When to use:** Emergency situations, when you can't speak.

**Configuration:** Settings → Controls → Corner Stop
- Enable/disable
- Choose which corners are active
- Adjust sensitivity

**Visual Feedback:**
```
Corner Hit Detected!
🛑 Stopping all actions...
✓ Cancelled

Returning to listening state...
```

---

### **Method 3: Keyboard Shortcut**

**macOS:** Press **⌘ + . (Command + Period)**

**Windows:** Press **Ctrl + C**

**When to use:** Quick stop without moving mouse or speaking.

**Customizable:** Settings → Keyboard → Stop Shortcut

---

### **Method 4: Click the Overlay**

**Action:**
1. Click on the Janus overlay window
2. A **[Stop]** button appears
3. Click **[Stop]** to halt execution

**When to use:** When overlay is visible and accessible.

**Visual:**
```
┌─────────────────────────────┐
│   ⚡ Executing...           │
│   Step 3/5                  │
│   [  Stop Execution  ]      │
└─────────────────────────────┘
```

---

### **What Happens When You Stop**

```
⚡ Executing: Step 3 of 5 - Downloading file...
         ↓
🛑 Stopped by user (Method: Voice "Stop")
         ↓
Cleanup:
✓ Cancelled pending actions (2 steps)
✓ Closed intermediate windows
✓ Returned focus to original app
         ↓
🎤 Ready for new command
```

**Important Notes:**
- **Completed steps are NOT reversed** - If Janus already opened Chrome, it stays open
- **Pending steps are cancelled** - Remaining actions won't execute
- **Safe cleanup** - Janus tidies up any intermediate state
- **Immediate response** - Stop is prioritized over everything

---

## Getting Help

### **Ask Janus for Help**

**Commands:**
- *"Help"* - General help menu
- *"What can you do?"* - Lists capabilities
- *"Show me examples"* - Common command examples
- *"How do I [task]?"* - Specific help

---

