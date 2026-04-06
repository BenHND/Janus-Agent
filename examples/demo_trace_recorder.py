"""
Demo: Flight Recorder (Trace Recorder)
TICKET-DEV-001

This example demonstrates how to use the trace recorder to capture
a complete session trace for debugging purposes.

Usage:
    python examples/demo_trace_recorder.py

This will:
1. Enable trace recording with PII masking
2. Simulate a command execution with screenshots
3. Save the trace to a .janus_trace file
4. Show how to replay it with the replay script
"""

import tempfile
from pathlib import Path

# Try to import PIL, otherwise create dummy images
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("⚠️  PIL/Pillow not installed. Install with: pip install pillow")
    print("   Demo will continue without actual screenshots.\n")

from janus.logging.trace_recorder import TraceRecorder, TraceRecorderManager


def create_demo_screenshot(text: str, color: str = "white", bg_color: str = "blue") -> 'Image.Image':
    """Create a demo screenshot with text"""
    if not HAS_PIL:
        return None
    
    # Create a simple colored image with text
    img = Image.new("RGB", (800, 600), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    # Draw text
    try:
        # Try to use a default font
        font = ImageFont.load_default()
    except:
        font = None
    
    draw.text((50, 50), text, fill=color, font=font)
    return img


def demo_basic_usage():
    """Demonstrate basic trace recorder usage"""
    print("=" * 60)
    print("Demo 1: Basic Trace Recorder Usage")
    print("=" * 60)
    
    # Create a trace recorder for a session
    session_id = "demo_session_001"
    temp_dir = tempfile.mkdtemp()
    
    recorder = TraceRecorder(
        session_id=session_id,
        trace_dir=temp_dir,
        enable_pii_masking=False,  # Disable for demo
        jpeg_quality=50,
    )
    
    print(f"\n✅ Created TraceRecorder for session: {session_id}")
    print(f"   Trace directory: {temp_dir}")
    
    # Record some steps
    print("\n📝 Recording pipeline steps...")
    
    # Step 1: Initial state
    screenshot1 = create_demo_screenshot("Step 1: Initial State", bg_color="lightblue")
    recorder.record_step(
        step_name="initial_state",
        screenshot=screenshot1,
        metadata={"command": "open Calculator"}
    )
    print("   ✓ Step 0: initial_state")
    
    # Step 2: Vision detection
    screenshot2 = create_demo_screenshot("Step 2: Vision Detection", bg_color="lightgreen")
    elements = [
        {"type": "button", "text": "Calculator", "bbox": [100, 200, 150, 40]},
        {"type": "window", "title": "Finder", "bbox": [0, 0, 800, 600]},
    ]
    recorder.record_step(
        step_name="vision",
        screenshot=screenshot2,
        elements=elements,
        metadata={"detected_elements": len(elements)}
    )
    print("   ✓ Step 1: vision (2 elements detected)")
    
    # Step 3: LLM reasoning
    recorder.record_step(
        step_name="reasoning",
        llm_prompt="What should I do to open Calculator?",
        llm_response="I should click the Calculator button at position [175, 220]",
        metadata={"confidence": 0.95}
    )
    print("   ✓ Step 2: reasoning (LLM interaction)")
    
    # Step 4: Execution
    screenshot3 = create_demo_screenshot("Step 3: After Execution", bg_color="lightcoral")
    recorder.record_step(
        step_name="execution",
        screenshot=screenshot3,
        metadata={"action": "click", "target": "Calculator"}
    )
    print("   ✓ Step 3: execution")
    
    # Step 5: Final state
    screenshot4 = create_demo_screenshot("Step 4: Final State - Calculator Open", bg_color="lightyellow")
    recorder.record_step(
        step_name="final_state",
        screenshot=screenshot4,
        metadata={"success": True}
    )
    print("   ✓ Step 4: final_state")
    
    # Add session metadata
    recorder.add_metadata("user", "developer")
    recorder.add_metadata("environment", "development")
    
    # Save trace
    print("\n💾 Saving trace...")
    trace_path = recorder.save_trace()
    
    print(f"\n✅ Trace saved successfully!")
    print(f"   Location: {trace_path}")
    print(f"   Size: {trace_path.stat().st_size / 1024:.1f} KB")
    
    # Get summary
    summary = recorder.get_trace_summary()
    print(f"\n📊 Trace Summary:")
    print(f"   Session ID: {summary['session_id']}")
    print(f"   Total Steps: {summary['total_steps']}")
    print(f"   PII Masking: {'Enabled' if summary['pii_masking_enabled'] else 'Disabled'}")
    print(f"   JPEG Quality: {summary['jpeg_quality']}%")
    
    # Show how to replay
    print(f"\n🎬 To replay this trace, run:")
    print(f"   python scripts/replay_session.py {trace_path}")
    print(f"   python scripts/replay_session.py {trace_path} demo_report.html")
    
    return trace_path


def demo_manager_usage():
    """Demonstrate TraceRecorderManager usage"""
    print("\n" + "=" * 60)
    print("Demo 2: TraceRecorderManager Usage")
    print("=" * 60)
    
    # Enable trace recording globally
    print("\n✅ Enabling trace recording globally...")
    TraceRecorderManager.enable(enable_pii_masking=True)
    
    print(f"   Trace recording enabled: {TraceRecorderManager.is_enabled()}")
    
    # Simulate multiple sessions
    sessions = ["session_001", "session_002", "session_003"]
    
    print("\n📝 Recording multiple sessions...")
    for session_id in sessions:
        recorder = TraceRecorderManager.get_recorder(session_id)
        
        # Record a simple step
        screenshot = create_demo_screenshot(f"Session: {session_id}", bg_color="lavender")
        recorder.record_step(
            step_name="test_step",
            screenshot=screenshot,
            metadata={"session": session_id}
        )
        print(f"   ✓ Recorded step for {session_id}")
    
    # Finalize all sessions
    print("\n💾 Finalizing all sessions...")
    TraceRecorderManager.finalize_all()
    
    print("✅ All sessions finalized and saved")
    
    # Disable trace recording
    TraceRecorderManager.disable()
    print(f"\n🛑 Trace recording disabled: {not TraceRecorderManager.is_enabled()}")


def demo_pii_masking():
    """Demonstrate PII masking integration"""
    print("\n" + "=" * 60)
    print("Demo 3: PII Masking Integration")
    print("=" * 60)
    
    print("\n📝 Creating trace recorder with PII masking enabled...")
    
    temp_dir = tempfile.mkdtemp()
    recorder = TraceRecorder(
        session_id="pii_demo",
        trace_dir=temp_dir,
        enable_pii_masking=True,  # Enable PII masking
        jpeg_quality=50,
    )
    
    print("✅ PII masking enabled")
    print("   Screenshots will be automatically masked before saving")
    print("   Detected PII patterns: emails, IBANs, credit cards, phone numbers")
    
    # Create a screenshot with "sensitive" data
    if HAS_PIL:
        screenshot = create_demo_screenshot(
            "Email: demo@example.com\nPhone: 0123456789\nThis data would be masked",
            bg_color="pink"
        )
        
        recorder.record_step(
            step_name="sensitive_data",
            screenshot=screenshot,
            metadata={"note": "PII regions will be blurred"}
        )
        print("\n✓ Recorded step with screenshot containing sensitive data")
        print("  (Note: Actual masking requires OCR engine to detect text)")
    else:
        print("\n⚠️  Skipping screenshot example (PIL not installed)")
    
    trace_path = recorder.save_trace()
    print(f"\n✅ Trace saved with PII masking: {trace_path}")


def main():
    """Main entry point"""
    print("\n" + "🎬" * 30)
    print("Flight Recorder Demo - TICKET-DEV-001")
    print("🎬" * 30 + "\n")
    
    try:
        # Demo 1: Basic usage
        trace_path = demo_basic_usage()
        
        # Demo 2: Manager usage
        demo_manager_usage()
        
        # Demo 3: PII masking
        demo_pii_masking()
        
        print("\n" + "=" * 60)
        print("✅ All demos completed successfully!")
        print("=" * 60)
        
        if HAS_PIL:
            print(f"\n💡 Next steps:")
            print(f"   1. Open the trace file to inspect: {trace_path}")
            print(f"   2. Generate HTML report: python scripts/replay_session.py {trace_path}")
            print(f"   3. View the report in your browser")
        else:
            print(f"\n💡 To see screenshots in traces:")
            print(f"   Install PIL: pip install pillow")
            print(f"   Then run this demo again")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
