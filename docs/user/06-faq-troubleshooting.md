# 📘 Janus User Manual - FAQ & Troubleshooting

**[← Previous: Personalization](05-personalization.md)** | **[Back to Index](README.md)**

---

# 📘 Janus User Manual - FAQ & Troubleshooting

**[← Previous: Personalization](05-personalization.md)** | **[Back to Index](README.md)**

---

# 6. FAQ & Troubleshooting

## "Janus doesn't hear me well"

### **Symptoms:**
- Low recognition accuracy (< 80%)
- Frequent misheard words
- Commands not triggering
- "I didn't catch that" errors

---

### **Solution 1: Recalibrate Microphone**

**Steps:**
1. Find a quiet location
2. Open Settings → Audio → Calibrate Microphone
3. Complete all 5 calibration phrases
4. Test with a command

**Expected improvement:** 10-20% accuracy increase

---

### **Solution 2: Check Microphone Settings**

**Verify:**
```
Settings → Audio → Microphone Selection

Current: Built-in Microphone
Quality: █████░░░░░ 50% ⚠️ Low

Issue detected: Input volume too low

[Increase Volume] [Switch Microphone] [Test]
```

**Fix:**
- macOS: System Preferences → Sound → Input → Increase volume slider
- Windows: Settings → Sound → Input → Increase volume

**Target:** 70-85% of maximum

---

### **Solution 3: Reduce Background Noise**

**Noise levels:**
- **< 40 dB:** Excellent
- **40-50 dB:** Good
- **50-60 dB:** Moderate (may affect accuracy)
- **> 60 dB:** Poor (significant accuracy loss)

**Fixes:**
- Close windows
- Turn off fans/AC temporarily
- Move away from noisy equipment
- Use noise-canceling microphone
- Enable Settings → Audio → Noise Suppression

---

### **Solution 4: Adjust Silence Threshold**

If Janus cuts you off mid-sentence:

Settings → Audio → Silence Threshold → **Long (3.0s)**

```
Before: 2.0s - "Open Safari and go to You—" [cut off]
After:  3.0s - "Open Safari and go to YouTube" ✓
```

---

### **Solution 5: Use Larger Model**

If accuracy is still poor:

Settings → Audio → Model → **Medium** or **Large**

```
Current: Small (460MB)
Accuracy: 92%

Try: Medium (1.5GB)
Expected: 95-96% accuracy

[Download & Switch] [Cancel]
```

**Trade-off:** Slower processing (2-3x) but higher accuracy

---

## "The agent is slow"

### **Symptoms:**
- Commands take > 5 seconds
- Lag between speech and action
- System feels sluggish
- High CPU/RAM usage

---

### **Solution 1: Use Faster Model**

If using Medium/Large models:

Settings → Audio → Model → **Small** or **Base**

```
Current: Medium (1.5GB)
Processing time: 2.8s per command

Switch to: Small (460MB)
Expected time: 0.9s per command (3x faster)

Accuracy trade-off: -2% (95% → 93%)

[Switch Model] [Cancel]
```

---

### **Solution 2: Enable GPU Acceleration**

Settings → Advanced → GPU Acceleration

```
GPU Acceleration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current: Disabled
CPU: 100% usage, slow

○ Disabled
◉ Enabled  ⭐ Recommended

GPU detected:
✓ Apple M2 Pro (16 cores) - Metal supported
✓ NVIDIA RTX 3060 - CUDA supported

Expected speedup: 4-6x faster

[Enable] [Test Performance]
```

**Before:**
```
Speech recognition: 2.1s
Vision processing: 3.4s
Total: 5.5s
```

**After (GPU):**
```
Speech recognition: 0.4s (5x faster)
Vision processing: 0.7s (5x faster)
Total: 1.1s
```

---

### **Solution 3: Close Unused Applications**

**Check system resources:**

```
📊 System Resources
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CPU Usage: 87% ⚠️ High
RAM: 14.2 / 16 GB (89%) ⚠️ High

Top consumers:
1. Chrome (43 tabs) - 4.2 GB RAM, 35% CPU
2. Slack - 1.8 GB RAM, 12% CPU
3. Docker - 2.1 GB RAM, 8% CPU

Janus needs:
• 2-4 GB RAM
• 20-40% CPU (during processing)

Recommendation: Close unused apps or tabs

[Close Chrome Tabs] [Quit Slack] [Ignore]
```

---

### **Solution 4: Restart Janus**

Sometimes memory leaks or cached data slow things down:

**Steps:**
1. Quit Janus completely
2. Wait 5 seconds
3. Relaunch

**If problem persists:**
Settings → Advanced → Clear Cache

```
🗑️ Clear Cache
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cache size: 847 MB

Includes:
• Model cache (512 MB)
• Vision cache (215 MB)
• Command history (120 MB)

Clearing will:
✓ Free up space
✓ May improve performance
✗ Models will reload (slower first use)

[Clear Cache] [Cancel]
```

---

### **Solution 5: Disable Voice Feedback**

If using Text-to-Speech (TTS):

Settings → General → Voice Feedback → **Disabled**

```
Voice Feedback
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◉ Disabled  ⭐ Faster
  Visual feedback only

○ Enabled
  Janus speaks responses
  Adds 1-2s per command

Time saved: ~1.5s per command

[Apply]
```

---

## "Janus can't click"

### **Symptoms:**
- Error: "Unable to interact with UI element"
- "Permissions denied"
- Commands execute but don't click buttons
- Vision finds elements but can't click them

---

### **Solution 1: Grant Accessibility Permission (macOS)**

**Critical for automation!**

**Steps:**
1. Open **System Preferences**
2. **Security & Privacy** → **Privacy** → **Accessibility**
3. Click 🔒 lock icon, enter password
4. **Check the box** next to **Janus**
5. **Restart Janus**

**Verification:**
```
Permissions Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Microphone:        ✅ Granted
Accessibility:     ❌ Denied  ⚠️
Screen Recording:  ✅ Granted

Issue: Accessibility permission required for clicking

[Open System Preferences] [Help]
```

---

### **Solution 2: Grant Screen Recording Permission (macOS)**

**Needed for vision-based clicking:**

**Steps:**
1. **System Preferences** → **Security & Privacy** → **Privacy** → **Screen Recording**
2. Click 🔒 lock, enter password
3. **Check box** next to **Janus**
4. **Restart Janus**

---

### **Solution 3: Run as Administrator (Windows)**

**For system-level automation:**

**Steps:**
1. **Right-click** Janus shortcut
2. Select **"Run as Administrator"**
3. Click **Yes** on UAC prompt

**When needed:**
- Installing software
- Modifying system settings
- Automating elevated programs

---

### **Solution 4: Enable Vision Fallback**

If direct API clicking fails:

Settings → Execution → Vision Verification → **Enabled**

```
Vision-Based Clicking
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

◉ Enabled  ⭐ Recommended
  Uses computer vision to locate and click
  Works with any application (even old software)

Methods:
✓ OCR text matching
✓ Visual template matching
✓ Button detection
✓ Coordinate calculation

Fallback chain:
1. Accessibility API (fastest)
2. Vision + coordinate click
3. Manual request

[Apply]
```

---

### **Solution 5: Be More Specific**

Instead of generic commands, be specific:

**❌ Vague:**
- *"Click the button"* (which button?)

**✅ Specific:**
- *"Click the Submit button"*
- *"Click the blue button at the bottom"*
- *"Click OK"*

---

## Additional Common Issues

### **"Commands not recognized"**

**Possible causes:**
- Microphone muted
- Wrong language selected
- Background noise too high
- Model not loaded

**Quick fix:**
1. Check microphone isn't muted (system settings)
2. Verify: Settings → Audio → Language = English (US)
3. Recalibrate microphone
4. Restart Janus

---

### **"Vision can't find elements"**

**Symptoms:**
- "Could not locate [element]"
- Timeouts looking for UI components

**Solutions:**
1. **Ensure app is visible** - Element must be on screen
2. **Wait for loading** - Let pages/apps fully load
3. **Be specific** - "Click the red Send button" not just "click"
4. **Check Screen Recording permission** - Needed for vision

---

### **"Janus keeps activating accidentally"**

**Problem:** Background noise triggers Janus

**Solutions:**
1. **Increase VAD threshold:**
   Settings → Audio → Voice Activation → Sensitivity → Low

2. **Use Push-to-Talk:**
   Settings → Controls → Activation Mode → Push-to-Talk
   Set hotkey (e.g., Ctrl+Space)

3. **Add wake word:**
   Settings → Controls → Wake Word → Enable
   Choose: "Hey Janus", "Computer", "Jarvis", etc.

---

### **"Multi-step commands fail midway"**

**Problem:** Complex workflows stop at step 3/5

**Causes & Fixes:**

**1. Timeout:**
- Settings → Execution → Step Timeout → Increase to 30s

**2. Network issue:**
- Check internet for web-based steps
- Use: *"Do [command] when online"*

**3. Permission denied:**
- Grant required permissions
- Run as Admin (Windows) if needed

**4. Element not found:**
- Enable vision verification
- Make target application active/visible

---

## Performance Optimization Matrix

Choose settings based on your priority:

### **⚡ Maximum Speed**

```
Goal: Fastest possible execution

Settings:
• Model: Base or Small
• GPU Acceleration: Enabled
• Vision Verification: Selective only
• Voice Feedback: Disabled
• Execution Speed: Fast
• Cache: Enabled

Expected: < 1s for simple commands

Trade-off: -5-10% accuracy
```

---

### **🎯 Maximum Accuracy**

```
Goal: Highest recognition accuracy

Settings:
• Model: Large
• GPU Acceleration: Enabled
• Vision Verification: Always
• Silence Threshold: Long (3.0s)
• Confirmation: Ask for high-risk
• Regular recalibration: Weekly

Expected: 97-99% accuracy

Trade-off: 2-3x slower
```

---

### **⚖️ Balanced (Recommended)**

```
Goal: Best overall experience

Settings:
• Model: Small ⭐
• GPU Acceleration: Enabled
• Vision Verification: Enabled
• Silence Threshold: Medium (2.5s)
• Execution Speed: Normal
• Confirmation: High-risk only

Expected: 94-96% accuracy, <2s commands

Best for: 90% of users
```

---

## Getting Additional Help

### **Documentation**

- **This User Manual** - You're reading it!
- **Architecture Docs:** `docs/architecture/` - Technical deep dive
- **Developer Docs:** `docs/developer/` - API and development
- **Examples:** `examples/` - Code samples and use cases

### **Community Support**

**GitHub Discussions:**
- [github.com/BenHND/Janus/discussions](https://github.com/BenHND/Janus/discussions)
- Ask questions, share tips, get community help

**GitHub Issues:**
- [github.com/BenHND/Janus/issues](https://github.com/BenHND/Janus/issues)
- Report bugs, request features, track progress

---

### **Reporting Bugs**

When reporting issues, please include:

**1. System Information:**
```
• OS: macOS 14.2 / Windows 11 / Ubuntu 22.04
• Processor: Apple M2 / Intel i7-12700K / AMD Ryzen 7
• RAM: 16 GB
• Janus Version: 1.2.0 (check: Help → About)
```

**2. Steps to Reproduce:**
```
1. Launch Janus
2. Say: "Open Chrome and go to YouTube"
3. Observe: [describe what happened]
4. Expected: [describe what should happen]
```

**3. Error Messages:**
- Screenshot of error dialog
- Relevant log file entries (Help → Open Log File)

**4. Configuration:**
- Settings → Advanced → Export Configuration → Share config.json

**Template:**
```markdown
**Bug Report**

**System:** macOS 14.2, M2 Pro, 16GB RAM
**Version:** Janus 1.2.0

**Issue:** Voice commands not recognized after sleep

**Steps:**
1. Put Mac to sleep
2. Wake Mac
3. Try voice command
4. Janus shows "Microphone not available"

**Expected:** Commands should work after wake

**Logs:** [attach log file]

**Workaround:** Restart Janus
```

---

## Advanced Tips & Power User Features

### **Custom Voice Commands**

Create shortcuts for complex workflows:

**Command:** *"Create custom command called 'morning routine'"*

**Janus:** "What should 'morning routine' do?"

**You:** *"Open Mail, Calendar, and Slack, then check the weather"*

**Saved!** Now *"morning routine"* executes all steps instantly.

---

### **Keyboard Shortcuts Reference**

| Shortcut | Action |
|----------|--------|
| **⌘ + ⇧ + J** (Mac)<br>**Ctrl + Shift + J** (Windows) | Toggle Janus ON/OFF |
| **⌘ + .** (Mac)<br>**Ctrl + C** (Windows) | Emergency stop |
| **⌘ + ,** (Mac)<br>**Ctrl + ,** (Windows) | Open settings |
| **⌘ + L** (Mac)<br>**Ctrl + L** (Windows) | View log |
| **⌘ + H** (Mac)<br>**Ctrl + H** (Windows) | Show/hide overlay |

---

### **Voice Command Shortcuts**

Quick phrases that save time:

- *"Repeat"* - Repeat last command
- *"Undo"* - Undo last action (where supported)
- *"What's this?"* - Describe current screen
- *"Help"* - Show available commands
- *"Settings"* - Open settings
- *"Version"* - Show version info
- *"Quit"* - Exit Janus

---

### **Productivity Workflows**

**Email Triage:**
```
"Show me unread emails from today"
"Mark all as read except from Sarah"
"Move newsletters to folder"
```

**Research:**
```
"Search for [topic], save top 5 to Reading List"
"Summarize current article and add to notes"
```

**File Management:**
```
"Organize Downloads by type"
"Move old files to Archive"
"Find duplicate photos"
```

---

## Conclusion

**Congratulations! You're now a Janus power user!**

You've learned:
- ✅ What Janus is and why it's revolutionary
- ✅ How to install and configure Janus for optimal performance
- ✅ Understanding the interface and visual states
- ✅ Giving simple and complex multi-step commands
- ✅ Using conversation mode and vision features
- ✅ Personalizing Janus to match your workflow
- ✅ Troubleshooting common issues
- ✅ Performance optimization strategies

---

## Next Steps

1. **Practice Daily** - Use Janus for routine tasks to build muscle memory
2. **Experiment** - Try combining commands in creative ways
3. **Teach Janus** - Correct mistakes so it learns your preferences
4. **Share Feedback** - Help improve Janus by reporting issues and suggesting features
5. **Join Community** - Connect with other users on GitHub Discussions

---

## The Future is Voice-Controlled

**With Janus, your voice becomes your most powerful tool.**

No more:
- ❌ Endless clicking through menus
- ❌ Repetitive copy-paste workflows
- ❌ Context switching between apps
- ❌ Memorizing keyboard shortcuts
- ❌ Manual multi-step processes

Instead:
- ✅ Speak naturally and get instant results
- ✅ Automate complex workflows with a sentence
- ✅ Stay focused on your work, not your tools
- ✅ Complete privacy with local processing
- ✅ Continuous improvement through learning

**Welcome to the future of computing!** 🎤✨

---

## Appendix: Quick Reference

### **Most Common Commands**

```
Applications:
• "Open [app]" / "Launch [app]"
• "Close [app]" / "Quit [app]"
• "Switch to [app]"

Web:
• "Go to [website]"
• "Search for [query]"
• "Open [url] in new tab"

Files:
• "Create folder [name]"
• "Move this to [location]"
• "Delete [file]"

Text:
• "Copy" / "Paste"
• "Select all"
• "Undo"

System:
• "Stop" / "Cancel"
• "Help"
• "Settings"
```

---

### **Emergency Contacts**

**Critical Issues:**
- GitHub Issues (bugs): github.com/BenHND/Janus/issues
- Security Issues: security@janusai.dev (if applicable)

**Community:**
- Discussions: github.com/BenHND/Janus/discussions
- Discord: [link if available]

---

## Document Information

**Document Version:** 1.0  
**Last Updated:** December 2025  
**Janus Version:** 1.x  
**Language:** English  
**Format:** Markdown  

**Authors:** Janus Team  
**License:** See LICENSE file  
**Repository:** [github.com/BenHND/Janus](https://github.com/BenHND/Janus)

---

**🎤 Thank you for using Janus!**

*Your feedback and contributions make Janus better for everyone.*

---

**End of User Manual**

