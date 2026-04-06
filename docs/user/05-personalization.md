# �� Janus User Manual - Personalization

**[← Previous: Use Cases](04-use-cases.md)** | **[Back to Index](README.md)** | **[Next: FAQ & Troubleshooting →](06-faq-troubleshooting.md)**

---

# 📘 Janus User Manual - Personalization

**[← Previous: Use Cases](04-use-cases.md)** | **[Back to Index](README.md)** | **[Next: FAQ & Troubleshooting →](06-faq-troubleshooting.md)**

---

# 5. Personalization

## Settings & Configuration

### **Accessing Settings**

**Methods:**
1. **Voice:** *"Open settings"* or *"Open preferences"*
2. **Menu:** Click Janus menu bar icon → Preferences
3. **Keyboard:** ⌘+, (Mac) or Ctrl+, (Windows)
4. **Overlay:** Click overlay → ⚙️ Settings icon

---

### **Audio Settings**

#### **Microphone Selection**

Choose which microphone Janus uses:

```
🎤 Microphone Selection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◉ Built-in Microphone
   Quality: Good | Noise: Moderate

○ USB Microphone (Blue Yeti)
   Quality: Excellent | Noise: Low

○ AirPods Pro (Bluetooth)
   Quality: Good | Latency: 150ms

○ Headset Microphone (Logitech)
   Quality: Very Good | Noise: Low

[Test Selected] [Apply]
```

**Tips:**
- External microphones usually provide better quality
- Noise-canceling mics improve accuracy in loud environments
- Bluetooth has slight latency (100-200ms)

---

#### **Speech Recognition Model**

Choose the Whisper model based on your priorities:

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| **Tiny** | 40MB | ⚡⚡⚡⚡ | ⭐⭐⭐ | Testing, very old hardware |
| **Base** | 140MB | ⚡⚡⚡ | ⭐⭐⭐⭐ | Fast, casual use |
| **Small** | 460MB | ⚡⚡ | ⭐⭐⭐⭐⭐ | **Recommended balance** |
| **Medium** | 1.5GB | ⚡ | ⭐⭐⭐⭐⭐ | High accuracy needs |
| **Large** | 3GB | 🐌 | ⭐⭐⭐⭐⭐ | Maximum accuracy |

**🎯 Recommendation:** **Small** for 95% of users - best speed/accuracy trade-off.

**When to choose:**
- **Base:** Older computers, speed priority
- **Small:** Default recommendation
- **Medium:** Professional use, important commands
- **Large:** Mission-critical accuracy, willing to wait

---

#### **Silence Threshold**

How long Janus waits after you stop speaking before processing:

```
⏱️ Silence Threshold
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

○ Short (2.0 seconds)
  Fast response, may cut you off mid-sentence

◉ Medium (2.5 seconds)  ⭐ Recommended
  Balanced - works for most speaking styles

○ Long (3.0 seconds)
  Patient, good for slow speakers

○ Very Long (3.5 seconds)
  Never cuts you off, but slower response

Current: 2.5 seconds

[Test with Sample] [Apply]
```

**Tips:**
- Fast speakers → Short
- Normal pace → Medium
- Slow or thoughtful speakers → Long
- Non-native speakers → Long

---

#### **Background Noise Suppression**

```
🔇 Noise Suppression
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◉ Enabled  ⭐ Recommended
  Filters ambient noise (AC, traffic, typing)
  May slightly affect voice quality

○ Disabled
  Raw audio input, no filtering
  Best for very quiet environments only

Noise level detected: 38 dB (Moderate)

[Test Suppression] [Apply]
```

---

### **Execution Settings**

#### **Confirmation for Risky Actions**

Choose when Janus asks for confirmation:

```
⚠️ Confirmation Level
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

○ Always Ask
  Confirms every action (safest, slowest)

◉ Ask for High-Risk Only  ⭐ Recommended
  Confirms deletions, emails, purchases

○ Never Ask
  No confirmations (fastest, least safe)

High-risk actions include:
✓ Deleting files or folders
✓ Sending emails
✓ Making purchases
✓ Running system commands
✓ Modifying important files

[Configure Risk List] [Apply]
```

---

#### **Execution Speed**

```
⚡ Execution Speed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

○ Fast
  Minimal delays between actions (300ms)

◉ Normal  ⭐ Recommended
  Balanced timing (500ms)

○ Slow
  More time to observe each step (1000ms)

○ Step-by-Step
  Pauses after each action, requires manual continue

Delay between actions: 500ms

[Test Speed] [Apply]
```

---

#### **Vision Verification**

```
👁️ Vision Verification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◉ Enabled  ⭐ Recommended
  Verifies actions succeeded using computer vision
  Slightly slower but much more reliable

○ Selective
  Only for critical actions

○ Disabled
  No verification (faster but less reliable)

Verification methods:
✓ Screenshot comparison
✓ Element detection
✓ OCR text matching
✓ Error dialog detection

[Configure] [Apply]
```

---

### **Privacy Settings**

#### **Audio Logging**

```
🎤 Audio Logging
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

○ Enabled
  Saves audio recordings for debugging
  Storage: ~/Library/Janus/audio_logs/

◉ Disabled  ⭐ Recommended for privacy
  No audio saved (more private)

○ Short-term Only
  Keeps last 24 hours, auto-deletes older

Current storage used: 0 MB

[Delete All Logs] [Apply]
```

---

#### **Command History**

```
📝 Command History
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◉ Enabled
  Maintains log of commands for learning
  Storage: ~/Library/Janus/history.db (encrypted)

○ Disabled
  No history saved

○ Limited (30 days)
  Auto-delete history older than 30 days

Commands logged: 1,247
Oldest: 45 days ago

[Export History] [Clear History] [Apply]
```

---

#### **Analytics**

```
📊 Analytics
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◉ Disabled  ⭐ Default
  No usage data collected

○ Local Only
  Collects stats locally (not sent anywhere)
  Helps optimize performance

○ Anonymous Sharing
  Shares anonymized usage data to improve Janus
  No personal info included

Privacy guarantee: We never collect personal data

[View Privacy Policy] [Apply]
```

---

## Learning & Correction

### **How Janus Learns**

Janus uses three learning mechanisms:

1. **Explicit Corrections** - When you correct mistakes
2. **Preference Detection** - Notices patterns in your choices
3. **Context Learning** - Remembers successful workflows

---

### **Correcting Mistakes**

#### **Example 1: Wrong Application**

**You say:** *"Open the browser"*

**Janus opens:** Microsoft Edge

**But you wanted:** Google Chrome

**You say:** *"No, I meant Chrome"*

**What happens:**
```
🧠 Learning from Correction
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Understood: You prefer Chrome when you say "browser"

Closing: Microsoft Edge
Opening: Google Chrome

Preference saved:
"browser" → Google Chrome (confidence: 80%)

After 3 more confirmations, this will become
your default "browser" application.

[Undo] [Confirm]
```

---

#### **Example 2: Wrong Interpretation**

**You say:** *"Search for Python"*

**Janus searches:** "Python snake"

**But you meant:** Python programming language

**You say:** *"I meant Python programming"*

**What happens:**
```
🧠 Context Learning
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ah, you meant programming context!

Updated understanding:
"Python" in your context typically refers to:
→ Programming language (90%)
→ Snake (10%)

Redoing search with: "Python programming"

[Correct] [Cancel]
```

---

### **Teaching Explicit Preferences**

You can directly teach Janus your preferences:

**Commands:**
- *"When I say email, always open Outlook"*
- *"Use DuckDuckGo for all web searches"*
- *"Always save documents to my Projects folder"*
- *"When I say browser, use Chrome"*

**Janus Response:**
```
✓ Preference Saved
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Rule created:
Trigger: "email"
Action: Launch Microsoft Outlook

This will apply to future commands matching:
• "open email"
• "check email"
• "email client"
• etc.

[Edit Rule] [Delete Rule] [OK]
```

---

### **Viewing Learned Preferences**

Access: Settings → Learning → View Preferences

```
📚 Learned Preferences
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Applications:
✓ "browser" → Google Chrome (95% confidence)
✓ "email" → Microsoft Outlook (100% confidence)
✓ "text editor" → VS Code (88% confidence)

Search Engines:
✓ Default: Google
✓ Privacy-focused: DuckDuckGo

File Locations:
✓ Documents → ~/Projects/ (preferred 80%)
✓ Downloads → ~/Desktop/ (occasionally)

Workflows:
✓ "morning routine" → Check email, calendar, news
✓ "end of day" → Close apps, backup, shutdown

Commands learned: 47
Total adaptations: 156

[Export] [Reset Learning] [Close]
```

---

### **Resetting Learned Behavior**

If Janus learned incorrect patterns:

**Voice Command:** *"Reset my preferences"* or *"Forget everything"*

**Or:** Settings → Learning → Reset Learning Data

```
⚠️ Reset Learning Data
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This will erase all learned preferences:
• Application preferences (47 rules)
• Workflow patterns (12 workflows)
• Correction history (156 corrections)
• Context associations

Janus will return to default behavior.

You cannot undo this action.

[Cancel] [Reset All Learning]
```

---

