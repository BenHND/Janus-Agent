"""
Audio and transcription logging for error auditing
"""

import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TranscriptionLog:
    """Single transcription log entry"""

    timestamp: str
    audio_path: str
    raw_transcription: str
    corrected_transcription: str
    normalized_transcription: str
    language: str
    model: str
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class AudioLogger:
    """Logs audio recordings and transcriptions for error auditing"""

    def __init__(
        self, log_dir: str = "audio_logs", max_logs: int = 1000, enable_audio_save: bool = True
    ):
        """
        Initialize audio logger

        Args:
            log_dir: Directory to store audio logs
            max_logs: Maximum number of logs to keep (oldest deleted first)
            enable_audio_save: Whether to save audio files
        """
        self.log_dir = Path(log_dir)
        self.max_logs = max_logs
        self.enable_audio_save = enable_audio_save

        # Create log directory structure
        self.audio_dir = self.log_dir / "audio"
        self.transcripts_dir = self.log_dir / "transcripts"
        self.metadata_file = self.log_dir / "metadata.json"

        self._setup_directories()
        self._load_metadata()

    def _setup_directories(self):
        """Create necessary directories"""
        self.log_dir.mkdir(exist_ok=True)
        self.audio_dir.mkdir(exist_ok=True)
        self.transcripts_dir.mkdir(exist_ok=True)

    def _load_metadata(self):
        """Load existing metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {"total_logs": 0, "logs": []}

    def _save_metadata(self):
        """Save metadata to file"""
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)

    def log_transcription(
        self,
        audio_path: str,
        raw_transcription: str,
        corrected_transcription: Optional[str] = None,
        normalized_transcription: Optional[str] = None,
        language: str = "fr",
        model: str = "base",
        confidence: Optional[float] = None,
        duration_seconds: Optional[float] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        Log a transcription with its audio

        Args:
            audio_path: Path to audio file
            raw_transcription: Raw transcription from STT
            corrected_transcription: Transcription after corrections
            normalized_transcription: Transcription after normalization
            language: Language code
            model: Model used for transcription
            confidence: Confidence score
            duration_seconds: Audio duration
            error: Error message if transcription failed

        Returns:
            Log ID
        """
        # Generate log ID
        timestamp = datetime.now()
        log_id = timestamp.strftime("%Y%m%d_%H%M%S_%f")

        # Copy audio file if enabled
        saved_audio_path = None
        if self.enable_audio_save and audio_path and Path(audio_path).exists():
            audio_filename = f"{log_id}.wav"
            saved_audio_path = self.audio_dir / audio_filename
            shutil.copy2(audio_path, saved_audio_path)
            saved_audio_path = str(saved_audio_path)

        # Create log entry
        log_entry = TranscriptionLog(
            timestamp=timestamp.isoformat(),
            audio_path=saved_audio_path or audio_path,
            raw_transcription=raw_transcription,
            corrected_transcription=corrected_transcription or raw_transcription,
            normalized_transcription=normalized_transcription or raw_transcription,
            language=language,
            model=model,
            confidence=confidence,
            duration_seconds=duration_seconds,
            success=error is None,
            error=error,
        )

        # Save transcript details
        transcript_file = self.transcripts_dir / f"{log_id}.json"
        with open(transcript_file, "w", encoding="utf-8") as f:
            json.dump(log_entry.to_dict(), f, indent=2, ensure_ascii=False)

        # Update metadata
        self.metadata["logs"].append(
            {
                "id": log_id,
                "timestamp": log_entry.timestamp,
                "success": log_entry.success,
                "raw_text": raw_transcription[:100],  # Preview
            }
        )
        self.metadata["total_logs"] += 1

        # Cleanup old logs if needed
        if len(self.metadata["logs"]) > self.max_logs:
            self._cleanup_old_logs()

        self._save_metadata()

        return log_id

    def _cleanup_old_logs(self):
        """Remove oldest logs when max_logs is exceeded"""
        # Calculate how many to remove
        to_remove = len(self.metadata["logs"]) - self.max_logs

        if to_remove <= 0:
            return

        # Sort by timestamp and remove oldest
        sorted_logs = sorted(self.metadata["logs"], key=lambda x: x["timestamp"])

        for log_entry in sorted_logs[:to_remove]:
            log_id = log_entry["id"]

            # Remove audio file
            audio_file = self.audio_dir / f"{log_id}.wav"
            if audio_file.exists():
                audio_file.unlink()

            # Remove transcript file
            transcript_file = self.transcripts_dir / f"{log_id}.json"
            if transcript_file.exists():
                transcript_file.unlink()

        # Update metadata
        self.metadata["logs"] = sorted_logs[to_remove:]

    def cleanup_old_logs_by_age(self, days: int):
        """
        Delete logs older than specified number of days

        Args:
            days: Number of days (logs older than this will be deleted)

        Returns:
            Number of logs deleted
        """
        if days <= 0:
            return 0

        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        logs_to_keep = []
        for log_entry in self.metadata["logs"]:
            log_timestamp = datetime.fromisoformat(log_entry["timestamp"])

            if log_timestamp < cutoff_date:
                # Delete old log
                log_id = log_entry["id"]

                # Remove audio file
                audio_file = self.audio_dir / f"{log_id}.wav"
                if audio_file.exists():
                    audio_file.unlink()

                # Remove transcript file
                transcript_file = self.transcripts_dir / f"{log_id}.json"
                if transcript_file.exists():
                    transcript_file.unlink()

                deleted_count += 1
            else:
                logs_to_keep.append(log_entry)

        # Update metadata
        self.metadata["logs"] = logs_to_keep
        self._save_metadata()

        return deleted_count

    def get_log(self, log_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific log entry

        Args:
            log_id: Log ID to retrieve

        Returns:
            Log entry dictionary or None
        """
        transcript_file = self.transcripts_dir / f"{log_id}.json"

        if not transcript_file.exists():
            return None

        with open(transcript_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_recent_logs(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent log entries

        Args:
            count: Number of logs to retrieve

        Returns:
            List of log entries
        """
        # Get most recent log IDs from metadata
        recent_ids = [log["id"] for log in self.metadata["logs"][-count:]]
        recent_ids.reverse()  # Most recent first

        logs = []
        for log_id in recent_ids:
            log = self.get_log(log_id)
            if log:
                logs.append(log)

        return logs

    def search_logs(
        self,
        query: Optional[str] = None,
        language: Optional[str] = None,
        success_only: bool = False,
        failed_only: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search logs with filters

        Args:
            query: Text to search in transcriptions
            language: Filter by language
            success_only: Only return successful transcriptions
            failed_only: Only return failed transcriptions
            limit: Maximum results to return

        Returns:
            List of matching log entries
        """
        results = []

        # Search through metadata for quick filtering
        candidate_ids = []
        for log_meta in reversed(self.metadata["logs"]):
            # Apply quick filters
            if success_only and not log_meta.get("success", True):
                continue
            if failed_only and log_meta.get("success", True):
                continue
            if query and query.lower() not in log_meta.get("raw_text", "").lower():
                continue

            candidate_ids.append(log_meta["id"])

            if len(candidate_ids) >= limit:
                break

        # Load full logs and apply detailed filters
        for log_id in candidate_ids:
            log = self.get_log(log_id)
            if not log:
                continue

            # Apply detailed filters
            if language and log.get("language") != language:
                continue

            results.append(log)

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get logging statistics

        Returns:
            Dictionary with statistics
        """
        total = self.metadata["total_logs"]
        current_logs = len(self.metadata["logs"])

        # Count successes and failures
        successes = sum(1 for log in self.metadata["logs"] if log.get("success", True))
        failures = current_logs - successes

        return {
            "total_logs": total,
            "current_logs": current_logs,
            "successful": successes,
            "failed": failures,
            "success_rate": successes / current_logs if current_logs > 0 else 0,
            "log_directory": str(self.log_dir),
            "audio_saved": self.enable_audio_save,
        }

    def export_logs(self, output_file: str, format: str = "json"):
        """
        Export all logs to a file

        Args:
            output_file: Output file path
            format: Export format (json or csv)
        """
        logs = [self.get_log(log["id"]) for log in self.metadata["logs"]]
        logs = [log for log in logs if log]  # Filter None

        if format == "json":
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)
        elif format == "csv":
            import csv

            with open(output_file, "w", newline="", encoding="utf-8") as f:
                if logs:
                    writer = csv.DictWriter(f, fieldnames=logs[0].keys())
                    writer.writeheader()
                    writer.writerows(logs)
