#!/usr/bin/env python3
"""
Session Replay Script
TICKET-DEV-001: Replay and visualize .janus_trace files

This script reads a .janus_trace file and generates an interactive HTML report
showing the complete execution timeline with:
- Screenshots at each step
- Detected elements (Set-of-Marks) overlaid on screenshots
- LLM prompts and responses
- Pipeline metadata and timing

Usage:
    python scripts/replay_session.py <trace_file.janus_trace> [output.html]
    
Example:
    python scripts/replay_session.py logs/traces/session_abc123_20250101_120000.janus_trace
    python scripts/replay_session.py trace.janus_trace report.html
"""

import argparse
import base64
import json
import sys
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional


def parse_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    except Exception:
        return timestamp_str


def extract_step_number(filename: str) -> str:
    """Extract step number from filename (e.g., 'screenshots/step_001.jpg' -> '001')"""
    return filename.split("_")[1].split(".")[0]


def load_trace(trace_path: Path) -> Dict[str, Any]:
    """
    Load trace data from .janus_trace file
    
    Args:
        trace_path: Path to .janus_trace file
        
    Returns:
        Dictionary with trace data and file contents
    """
    if not trace_path.exists():
        raise FileNotFoundError(f"Trace file not found: {trace_path}")
    
    if not trace_path.suffix == ".janus_trace":
        raise ValueError(f"Invalid trace file extension: {trace_path.suffix}")
    
    trace_data = {
        "metadata": None,
        "screenshots": {},
        "elements": {},
        "llm": {},
    }
    
    with zipfile.ZipFile(trace_path, "r") as zf:
        # Load main trace JSON
        with zf.open("trace.json") as f:
            trace_data["metadata"] = json.load(f)
        
        # Load screenshots
        for name in zf.namelist():
            if name.startswith("screenshots/"):
                image_data = zf.read(name)
                # Convert to base64 for HTML embedding
                b64_data = base64.b64encode(image_data).decode("utf-8")
                step_num = extract_step_number(name)
                trace_data["screenshots"][step_num] = b64_data
        
        # Load elements JSON
        for name in zf.namelist():
            if name.startswith("elements/"):
                with zf.open(name) as f:
                    elements_data = json.load(f)
                step_num = extract_step_number(name)
                trace_data["elements"][step_num] = elements_data
        
        # Load LLM interactions
        for name in zf.namelist():
            if name.startswith("llm/"):
                with zf.open(name) as f:
                    llm_data = json.load(f)
                step_num = extract_step_number(name)
                trace_data["llm"][step_num] = llm_data
    
    return trace_data


def generate_html_report(trace_data: Dict[str, Any], output_path: Path):
    """
    Generate HTML report from trace data
    
    Args:
        trace_data: Loaded trace data
        output_path: Path to save HTML report
    """
    metadata = trace_data["metadata"]
    
    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Janus Session Replay - {metadata['session_id']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        
        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .metadata-item {{
            background: #f8f9fa;
            padding: 10px 15px;
            border-radius: 4px;
        }}
        
        .metadata-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        
        .metadata-value {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
        }}
        
        .timeline {{
            position: relative;
            padding-left: 40px;
        }}
        
        .timeline::before {{
            content: '';
            position: absolute;
            left: 20px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #ddd;
        }}
        
        .step {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            position: relative;
        }}
        
        .step::before {{
            content: '';
            position: absolute;
            left: -28px;
            top: 30px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #3498db;
            border: 3px solid white;
            box-shadow: 0 0 0 2px #3498db;
        }}
        
        .step-header {{
            padding: 20px 30px;
            border-bottom: 1px solid #eee;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px 8px 0 0;
        }}
        
        .step-title {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        
        .step-info {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .step-content {{
            padding: 30px;
        }}
        
        .screenshot-container {{
            margin-bottom: 20px;
            text-align: center;
        }}
        
        .screenshot {{
            max-width: 100%;
            border-radius: 4px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .elements-container {{
            margin-top: 20px;
        }}
        
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
            padding-bottom: 5px;
            border-bottom: 2px solid #3498db;
        }}
        
        .elements-list {{
            background: #f8f9fa;
            border-radius: 4px;
            padding: 15px;
        }}
        
        .element-item {{
            background: white;
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        
        .llm-container {{
            margin-top: 20px;
        }}
        
        .llm-block {{
            margin-bottom: 15px;
        }}
        
        .llm-label {{
            font-size: 14px;
            font-weight: 600;
            color: #666;
            margin-bottom: 8px;
        }}
        
        .llm-content {{
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            border-radius: 4px;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            max-height: 300px;
            overflow-y: auto;
        }}
        
        .llm-prompt {{
            border-left-color: #e67e22;
        }}
        
        .llm-response {{
            border-left-color: #27ae60;
        }}
        
        .no-data {{
            color: #999;
            font-style: italic;
            text-align: center;
            padding: 20px;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }}
        
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .badge-info {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        
        .badge-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        footer {{
            text-align: center;
            padding: 30px;
            color: #999;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎬 Janus Session Replay</h1>
            <div class="metadata">
                <div class="metadata-item">
                    <div class="metadata-label">Session ID</div>
                    <div class="metadata-value">{metadata['session_id']}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Start Time</div>
                    <div class="metadata-value">{parse_timestamp(metadata['start_time'])}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">End Time</div>
                    <div class="metadata-value">{parse_timestamp(metadata.get('end_time', 'N/A'))}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Total Steps</div>
                    <div class="metadata-value">{metadata.get('total_steps', len(metadata['steps']))}</div>
                </div>
            </div>
        </header>
        
        <div class="timeline">
"""
    
    # Generate steps
    for step in metadata["steps"]:
        step_index = step["step_index"]
        step_num = f"{step_index:03d}"
        
        html += f"""
            <div class="step">
                <div class="step-header">
                    <div class="step-title">
                        Step {step_index}: {step["step_name"].title()}
"""
        
        # Add badges
        if step.get("has_screenshot"):
            html += '<span class="badge badge-success">📸 Screenshot</span>'
        if step.get("has_elements"):
            html += '<span class="badge badge-info">🎯 Elements</span>'
        if step.get("has_llm_interaction"):
            html += '<span class="badge badge-warning">🤖 LLM</span>'
        
        html += f"""
                    </div>
                    <div class="step-info">
                        {parse_timestamp(step["timestamp"])}
                    </div>
                </div>
                <div class="step-content">
"""
        
        # Screenshot
        if step_num in trace_data["screenshots"]:
            screenshot_b64 = trace_data["screenshots"][step_num]
            html += f"""
                    <div class="screenshot-container">
                        <img src="data:image/jpeg;base64,{screenshot_b64}" alt="Screenshot" class="screenshot">
                    </div>
"""
        
        # Elements (Set-of-Marks)
        if step_num in trace_data["elements"]:
            elements = trace_data["elements"][step_num]
            html += """
                    <div class="elements-container">
                        <div class="section-title">🎯 Detected Elements (Set-of-Marks)</div>
                        <div class="elements-list">
"""
            if isinstance(elements, list) and len(elements) > 0:
                for elem in elements:
                    html += f'<div class="element-item">{json.dumps(elem, indent=2)}</div>\n'
            else:
                html += '<div class="no-data">No elements detected</div>'
            
            html += """
                        </div>
                    </div>
"""
        
        # LLM Interactions
        if step_num in trace_data["llm"]:
            llm_data = trace_data["llm"][step_num]
            html += """
                    <div class="llm-container">
                        <div class="section-title">🤖 LLM Interaction</div>
"""
            if "prompt" in llm_data:
                html += f"""
                        <div class="llm-block">
                            <div class="llm-label">Prompt:</div>
                            <div class="llm-content llm-prompt">{llm_data["prompt"]}</div>
                        </div>
"""
            if "response" in llm_data:
                html += f"""
                        <div class="llm-block">
                            <div class="llm-label">Response:</div>
                            <div class="llm-content llm-response">{llm_data["response"]}</div>
                        </div>
"""
            html += """
                    </div>
"""
        
        # Step metadata
        if step.get("metadata"):
            html += f"""
                    <div class="elements-container">
                        <div class="section-title">📋 Step Metadata</div>
                        <div class="llm-content">{json.dumps(step["metadata"], indent=2)}</div>
                    </div>
"""
        
        html += """
                </div>
            </div>
"""
    
    # Footer
    html += """
        </div>
        
        <footer>
            Generated by Janus Session Replay | TICKET-DEV-001: Flight Recorder
        </footer>
    </div>
</body>
</html>
"""
    
    # Write HTML file
    output_path.write_text(html, encoding="utf-8")
    print(f"✅ Report generated: {output_path}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Replay and visualize Janus session traces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/replay_session.py trace.janus_trace
  python scripts/replay_session.py trace.janus_trace output.html
  python scripts/replay_session.py logs/traces/session_*.janus_trace report.html
        """
    )
    
    parser.add_argument(
        "trace_file",
        type=str,
        help="Path to .janus_trace file"
    )
    
    parser.add_argument(
        "output_file",
        type=str,
        nargs="?",
        default=None,
        help="Output HTML file path (default: <trace_file>.html)"
    )
    
    args = parser.parse_args()
    
    # Load trace
    trace_path = Path(args.trace_file)
    print(f"📂 Loading trace: {trace_path}")
    
    try:
        trace_data = load_trace(trace_path)
        print(f"✅ Trace loaded: {trace_data['metadata']['total_steps']} steps")
    except Exception as e:
        print(f"❌ Error loading trace: {e}", file=sys.stderr)
        return 1
    
    # Generate output path
    if args.output_file:
        output_path = Path(args.output_file)
    else:
        output_path = trace_path.with_suffix(".html")
    
    # Generate HTML report
    print(f"🎨 Generating HTML report...")
    try:
        generate_html_report(trace_data, output_path)
        print(f"\n🎬 Open {output_path} in your browser to view the replay")
        return 0
    except Exception as e:
        print(f"❌ Error generating report: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
