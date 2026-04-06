# 📘 Janus User Manual - Installation & Quick Start

**[← Previous: Introduction](01-introduction.md)** | **[Back to Index](README.md)** | **[Next: Getting Started →](03-getting-started.md)**

---

# 📘 Janus User Manual - Installation & Quick Start

**[← Previous: Introduction](01-introduction.md)** | **[Back to Index](README.md)** | **[Next: Getting Started →](03-getting-started.md)**

---

# 2. Installation & Quick Start

## System Requirements

### **For macOS:**

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Operating System** | macOS 10.14 (Mojave) | macOS 12 (Monterey) or newer |
| **Processor** | Intel Core i5 (2015+) | Apple Silicon (M1/M2/M3/M4) |
| **RAM** | 8GB | 16GB or more |
| **Storage** | 5GB free | 10GB free (for larger models) |
| **GPU** | Integrated | Dedicated or Apple Silicon |
| **Microphone** | Built-in or USB | External noise-canceling |

**🎯 Optimal Experience:** M-series Mac with 16GB+ RAM

### **For Windows:**

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Operating System** | Windows 10 (1809+) | Windows 11 22H2 or newer |
| **Processor** | Intel Core i5 / Ryzen 5 | Intel Core i7 / Ryzen 7 or better |
| **RAM** | 8GB | 16GB or more |
| **Storage** | 5GB free | 10GB free (for larger models) |
| **GPU** | Integrated | NVIDIA RTX 20xx+ or AMD RX 6000+ |
| **Microphone** | Built-in or USB | External noise-canceling |

**🎯 Optimal Experience:** Modern PC with discrete NVIDIA GPU and 16GB+ RAM

---

## Installation Methods

### **Option 1: Installer (Recommended for Most Users)**

#### **macOS Installation:**

1. **Download the Installer**
   - Visit [github.com/BenHND/Janus/releases](https://github.com/BenHND/Janus/releases)
   - Download `Janus-Installer-vX.X.X.dmg` (latest version)
   - File size: ~500MB

2. **Mount the DMG**
   - Double-click the downloaded DMG file
   - A new window will open showing the Janus icon

3. **Install Janus**
   - Drag the **Janus** icon to the **Applications** folder
   - Wait for the copy to complete (~30 seconds)

4. **First Launch**
   - Open **Applications** folder
   - Double-click **Janus**
   - macOS may show: *"Janus is an app downloaded from the Internet. Are you sure you want to open it?"*
   - Click **Open**

5. **Grant Permissions** (Critical!)
   - Janus will request permissions (see Permissions section below)

#### **Windows Installation:**

1. **Download the Installer**
   - Visit [github.com/BenHND/Janus/releases](https://github.com/BenHND/Janus/releases)
   - Download `Janus-Setup-vX.X.X.exe` (latest version)
   - File size: ~450MB

2. **Run the Installer**
   - **Right-click** the downloaded EXE file
   - Select **"Run as Administrator"** (important!)
   - User Account Control (UAC) will prompt: Click **Yes**

3. **Installation Wizard**
   - **Welcome Screen** → Click **Next**
   - **License Agreement** → Accept and click **Next**
   - **Installation Location** → Default is `C:\Program Files\Janus` → **Next**
   - **Start Menu Folder** → Default is fine → **Next**
   - **Ready to Install** → Click **Install**
   - Wait for installation (~2-3 minutes)

4. **Complete Installation**
   - Click **Finish**
   - Check "Launch Janus" if you want to start immediately

5. **Grant Permissions**
   - Windows will ask for microphone access → Click **Allow**

---

### **Option 2: From Source (Advanced Users/Developers)**

If you prefer to build from source or want the latest development version:

```bash
# 1. Clone the repository
git clone https://github.com/BenHND/Janus.git
cd Janus

# 2. Run the unified installation script
chmod +x install.sh
./install.sh

# The script will:
# - Check system requirements
# - Create Python virtual environment
# - Install base dependencies
# - Install LLM dependencies
# - Install vision dependencies
# - Install TTS (text-to-speech) dependencies
# - Download required AI models
# - Set up configuration files
# - Verify installation

# 3. Activate the virtual environment (if not auto-activated)
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# 4. Launch Janus
python main.py
```

**⏱️ Installation Time:** 15-45 minutes depending on:
- Internet connection speed (downloading models)
- CPU speed (building dependencies)
- Whether you have Python/pip already installed

---

## First Launch: Permissions Setup

### **macOS Permissions (Required)**

Janus needs specific permissions to function. macOS will prompt you for each one.

#### **1. Microphone Access** ✅ Required

**Why:** To hear your voice commands.

**How to Grant:**
1. On first launch, macOS shows: *"Janus would like to access the microphone"*
2. Click **OK** or **Allow**

**Manual Grant (if needed):**
1. Open **System Preferences** → **Security & Privacy**
2. Click **Privacy** tab
3. Select **Microphone** from left sidebar
4. Check the box next to **Janus**

**Testing:**
- Say "Test microphone" after granting permission
- Janus should respond: "Microphone working correctly"

#### **2. Accessibility Access** ✅ Required

**Why:** To control applications, click buttons, type text, and automate actions.

**How to Grant:**
1. macOS will prompt: *"Janus would like to control this computer using accessibility features"*
2. Click **Open System Preferences**
3. System Preferences → Security & Privacy → Privacy → Accessibility
4. Click the **🔒 lock icon** (bottom left)
5. Enter your Mac password
6. Check the box next to **Janus**
7. **Restart Janus** (important!)

**What This Allows:**
- Clicking buttons and UI elements
- Typing text in any application
- Moving and resizing windows
- Simulating keyboard shortcuts
- Dragging and dropping items

**Security Note:** This is a standard macOS permission. Popular apps like TextExpander, Keyboard Maestro, and BetterTouchTool require it too. Janus only uses it for your explicit voice commands.

#### **3. Screen Recording** ✅ Required for Vision Features

**Why:** To "see" your screen using computer vision for verification and error detection.

**How to Grant:**
1. System Preferences → Security & Privacy → Privacy → Screen Recording
2. Click the **🔒 lock icon**
3. Enter your Mac password
4. Check the box next to **Janus**
5. **Restart Janus** (important!)

**What This Allows:**
- Capturing screenshots for vision analysis
- Verifying that actions completed successfully
- Detecting error messages and dialogs
- Finding UI elements by appearance
- OCR (reading text from screen)

**Privacy Note:** All screenshots are processed locally and deleted immediately. Nothing is saved or transmitted.

---

### **Windows Permissions (Required)**

Windows permissions are simpler but still critical.

#### **1. Microphone Access** ✅ Required

**How to Grant:**
1. On first launch, Windows shows: *"Do you want to allow Janus to access your microphone?"*
2. Click **Yes**

**Manual Grant (if needed):**
1. Windows Settings → Privacy → Microphone
2. Ensure "Allow apps to access your microphone" is **On**
3. Scroll to "Choose which apps can access your microphone"
4. Find **Janus** and toggle to **On**

#### **2. Administrator Privileges** ⚠️ Some Features Need This

**Why:** Some automation features require elevated privileges.

**How to Use:**
- For most tasks, run Janus normally
- For system-level tasks (e.g., installing software), run as Administrator:
  - Right-click Janus shortcut
  - Select "Run as Administrator"

---

## Microphone Calibration Wizard

**🎯 Critical for Accuracy:** Calibration adapts Janus to your voice and environment.

### **Why Calibrate?**

Every user has a unique voice (accent, pitch, pace) and environment (ambient noise, room acoustics). Calibration personalizes Janus for optimal performance.

**What Gets Calibrated:**
- ✅ Your voice characteristics (pitch, pace, accent)
- ✅ Ambient noise levels in your space
- ✅ Silence detection thresholds
- ✅ Voice Activity Detection (VAD) sensitivity
- ✅ Phonetic adaptation for better recognition

### **Starting Calibration**

**On First Launch:**
- Janus automatically starts the calibration wizard
- You'll see: *"Welcome! Let's calibrate your microphone for optimal performance."*

**Manual Recalibration (Later):**
- Voice command: *"Recalibrate microphone"*
- Menu: **Janus → Preferences → Audio → Calibrate Microphone**
- Keyboard: Open settings (⌘+,) → Audio → Calibrate

### **The 5-Phrase Calibration Process**

You'll be asked to read 5 different phrases that represent typical command patterns.

```
🎙️ Janus Microphone Calibration Wizard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1 of 5

Please read the following phrase clearly and naturally:

"Open Chrome and go to Wikipedia"

[          Ready - Click to Start Recording          ]

Tips:
• Speak at your normal volume
• Use your regular speaking pace
• Stay 1-2 feet from the microphone
• Minimize background noise
```

#### **The 5 Calibration Phrases:**

1. **"Open Chrome and go to Wikipedia"**
   - Tests: Application launching + web navigation

2. **"Search for machine learning tutorials"**
   - Tests: Search commands + complex terminology

3. **"Copy this text and paste it in the document"**
   - Tests: Action chains + context references

4. **"Switch to the next tab and close the window"**
   - Tests: Navigation + sequential actions

5. **"Create a new folder called Project Files"**
   - Tests: File operations + naming

### **During Recording:**

```
🎙️ Recording: "Open Chrome and go to Wikipedia"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[████████████████████░░░░░░░░░░░░░░] 2.3s

Waveform: ▁▂▃▅▇█▇▅▃▂▁▂▃▅▇█▇▅▃▂▁

Volume: ██████████████████░░ 85%  ✅ Good
Noise:  ████░░░░░░░░░░░░░░░░ 22dB ✅ Quiet

Processing...
```

### **After Each Phrase:**

```
✅ Phrase 1 Complete!

Recognized: "open chrome and go to wikipedia"
Accuracy: 98%
Confidence: High

Continue to next phrase...

Progress: [█████░░░░░░░░░░] 1/5 phrases
```

### **Calibration Tips for Best Results:**

#### **🔇 Environment:**
- Find a **quiet space** - Close windows, turn off fans/AC
- **Minimize background noise** - Pause music, mute notifications
- **Choose consistent location** - Calibrate where you'll typically use Janus

#### **🗣️ Speaking:**
- **Use your normal voice** - Don't shout or whisper
- **Speak naturally** - Don't over-enunciate or speak robotically
- **Maintain consistent pace** - Not too fast, not too slow
- **Speak clearly** - But naturally, as you would in conversation

#### **📏 Distance:**
- **Stay 1-2 feet from microphone** - Closer picks up mouth noise, farther loses clarity
- **Keep consistent distance** - Don't move closer/farther between phrases
- **Face the microphone** - Don't speak to the side

#### **🎤 Microphone:**
- **Use a quality microphone** - Built-in often works fine, external is better
- **Check microphone selection** - Ensure correct mic is selected in settings
- **Adjust input volume** - Not too high (distortion) or too low (quiet)

### **Calibration Complete:**

```
✓ Calibration Successful!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Profile: User_Voice_Profile_2025-12-06_14-30

Environment Analysis:
✓ Ambient noise: 32 dB (Quiet - Excellent)
✓ Room acoustics: Low reverb
✓ Microphone quality: Very Good

Voice Profile:
✓ Accent: North American English
✓ Speaking pace: Moderate (115 WPM)
✓ Pitch: Medium range
✓ Clarity: Excellent

Optimized Settings:
✓ Silence threshold: 2.5 seconds
✓ VAD sensitivity: Medium
✓ Noise suppression: Enabled
✓ Model selection: Small (optimal balance)

Estimated Accuracy: 96%

Your personalized voice profile is saved and ready!
You can recalibrate anytime if you change location
or if recognition accuracy decreases.

[       Continue to Initial Configuration       ]
```

### **When to Recalibrate:**

- **🏠 Changed environment** - Moved to different room or location
- **🔊 Background noise changed** - AC/fan turned on, moved near window
- **🎤 New microphone** - Switched from built-in to external or vice versa
- **📉 Accuracy decreased** - Noticing more recognition errors
- **🗣️ Voice changed** - Illness, fatigue, or long-term voice changes

**Pro Tip:** Recalibrate monthly for optimal performance, or whenever you notice accuracy issues.

---

## Initial Configuration

After calibration, Janus performs initial setup.

### **Model Downloads (First Time Only)**

Janus needs to download AI models. This happens automatically on first launch.

```
🎤 Janus - Initial Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Python environment verified
✓ Dependencies installed
✓ Microphone calibrated

⏳ Downloading AI Models...

[1/3] Speech Recognition (Whisper Small)
      ████████████████████░░ 85% (390/460 MB)
      Speed: 8.5 MB/s | ETA: 8 seconds

[2/3] Vision Models (BLIP-2 + CLIP)
      ░░░░░░░░░░░░░░░░░░░░░░  0% (Waiting...)

[3/3] LLM (Optional - You can skip this)
      ░░░░░░░░░░░░░░░░░░░░░░  0% (Not started)
```

#### **Downloaded Components:**

1. **Whisper Speech Recognition**
   - Small: 460MB (Recommended - balanced)
   - Base: 140MB (Faster but less accurate)
   - Medium: 1.5GB (More accurate but slower)
   - Large: 3GB (Best accuracy, slowest)

2. **Vision Models** (~500MB)
   - BLIP-2: Image captioning and understanding
   - CLIP: Visual-semantic matching
   - OCR Models: Text recognition

3. **LLM (Optional)**
   - Can skip if using cloud LLMs
   - Ollama models (4-7GB) for local reasoning
   - Or connect to OpenAI/Anthropic later

**⏱️ Download Time:** 
- Fast internet (50+ Mbps): 5-10 minutes
- Moderate (20-50 Mbps): 15-25 minutes
- Slow (<20 Mbps): 30-60 minutes

### **Language Selection**

Choose your preferred language for voice commands:

```
🌐 Language Selection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Select your primary language:

◉ English (US)          Most tested
○ English (UK)
○ French (Français)
○ Spanish (Español)
○ German (Deutsch)
○ Italian (Italiano)
○ Portuguese (Português)
○ Japanese (日本語)
○ Chinese Simplified (简体中文)
○ [Show all 90+ languages...]

Note: You can change this anytime in settings.

[              Continue              ]
```

**Supported Languages:** 90+ languages thanks to Whisper's multilingual support.

**Note on Accuracy:** English (US) has the highest accuracy due to extensive testing. Other languages work well but may have slightly lower recognition rates.

### **System Verification**

Janus verifies all components are working:

```
✓ System Verification Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hardware Detection:
✓ Processor: Apple M2 Pro (10 cores)
✓ RAM: 16 GB available
✓ GPU: Apple M2 Pro (16 cores) - Metal supported
✓ Storage: 45 GB free

Software Verification:
✓ Speech recognition: Ready (Whisper Small loaded)
✓ Vision system: Ready (BLIP-2 + CLIP loaded)
✓ Automation engine: Ready (Accessibility APIs available)
✓ Database: Created (~/Library/Application Support/Janus/)
✓ Configuration: Loaded (default settings applied)

Permissions:
✓ Microphone: Granted
✓ Accessibility: Granted
✓ Screen Recording: Granted

Network:
✓ Internet: Connected (for cloud LLM if desired)
ⓘ Local mode: Available (works offline)

[     🎤 Ready to Start - Click to Begin     ]
```

### **Quick Start Tutorial (Optional)**

First-time users are offered a 2-minute interactive tutorial:

```
Would you like a quick tutorial?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Learn Janus basics in 2 minutes:
• Understanding the interface
• Your first voice command
• How to stop or cancel
• Finding help

[   Yes, show me   ]    [   No, I'll explore   ]
```

**Tutorial Covers:**
1. Interface overview (overlay states)
2. Speaking your first command
3. Interrupting/stopping actions
4. Accessing settings
5. Getting help

---

## Your First Command!

After setup, you're ready to use Janus. Let's start with something simple.

### **Example 1: Open an Application**

**Say clearly:** *"Open Safari"*

(Windows users: *"Open Chrome"* or *"Open Edge"*)

**What Happens:**

```
🎤 Janus - Listening
━━━━━━━━━━━━━━━━━━━━━
You: "Open Safari"

🔊 Processing...
Recognized: "open safari"
Confidence: 98%

⚡ Executing...
Action: launch_application
Target: Safari
Status: Launching...

✓ Done!
Safari opened successfully.
Time: 0.8 seconds

🎤 Ready for next command...
```

**Visual Feedback:**
- Overlay turns **green** → Listening
- Turns **blue** → Processing speech
- Turns **yellow** → Executing action
- Shows **✓** → Success!
- Returns to **green** → Ready

**Congratulations! You just used Janus for the first time!**

---

Now let me continue with the rest of the sections. I'll save this and create part 2:


### **Example 2: Multi-Step Command**

Now let's try something more advanced:

**Say:** *"Open Safari and go to YouTube"*

**What Happens:**

```
�� Listening: "Open Safari and go to YouTube"

🧠 Planning...
Analyzed intent: Launch Safari + Navigate to YouTube.com
Plan: 2 steps
1. Launch/focus Safari
2. Navigate to youtube.com

⚡ Step 1/2: Launching Safari...
✓ Safari opened

⚡ Step 2/2: Navigating to YouTube...
✓ Page loaded

✅ All steps complete!
Total time: 3.2 seconds

🎤 Ready...
```

**This is where Janus shines—intelligent multi-step execution!**

---

