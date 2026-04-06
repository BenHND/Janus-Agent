"""
CorrectionDialog - Simple UI for user corrections
Allows users to correct misinterpreted commands
"""

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Any, Callable, Dict, Optional

from janus.runtime.core.contracts import Intent


@dataclass
class CorrectionResult:
    """Result from correction dialog"""

    corrected: bool
    correct_interpretation: Optional[str] = None
    correct_intent: Optional[str] = None
    notes: Optional[str] = None


class CorrectionDialog:
    """
    Simple dialog for user corrections
    Shows what Janus understood vs what the user meant
    """

    def __init__(self, parent: Optional[tk.Tk] = None):
        """
        Initialize correction dialog

        Args:
            parent: Parent window (creates new root if None)
        """
        self.parent = parent
        self.result: Optional[CorrectionResult] = None
        self.dialog: Optional[tk.Toplevel] = None
        self.root_created = False

    def show(
        self,
        command: str,
        wrong_intent: Intent,
        on_submit: Optional[Callable[[CorrectionResult], None]] = None,
    ) -> Optional[CorrectionResult]:
        """
        Show correction dialog for a misinterpreted command

        Args:
            command: Original command text
            wrong_intent: The intent that was incorrectly detected
            on_submit: Optional callback when user submits correction

        Returns:
            CorrectionResult if user submitted, None if cancelled
        """
        # Create root if needed
        if self.parent is None:
            self.parent = tk.Tk()
            self.parent.withdraw()
            self.root_created = True

        # Create dialog
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Correction de Commande")
        self.dialog.geometry("500x400")
        self.dialog.resizable(False, False)

        # Center dialog
        self._center_dialog()

        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Build UI
        self._build_ui(command, wrong_intent, on_submit)

        # Wait for dialog to close
        self.dialog.wait_window()

        # Clean up root if we created it
        if self.root_created:
            try:
                self.parent.destroy()
            except:
                pass
            self.root_created = False
            self.parent = None

        return self.result

    def _center_dialog(self):
        """Center dialog on screen"""
        self.dialog.update_idletasks()

        # Get screen dimensions
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()

        # Get dialog dimensions
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()

        # Calculate position
        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2

        self.dialog.geometry(f"+{x}+{y}")

    def _build_ui(
        self,
        command: str,
        wrong_intent: Intent,
        on_submit: Optional[Callable[[CorrectionResult], None]],
    ):
        """Build dialog UI"""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame, text="Correction de Commande", font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 20))

        # Original command section
        command_frame = ttk.LabelFrame(main_frame, text="Commande originale", padding="10")
        command_frame.pack(fill=tk.X, pady=(0, 10))

        command_label = ttk.Label(command_frame, text=command, font=("Arial", 11), wraplength=440)
        command_label.pack()

        # Wrong interpretation section
        wrong_frame = ttk.LabelFrame(main_frame, text="J'ai compris", padding="10")
        wrong_frame.pack(fill=tk.X, pady=(0, 10))

        intent_text = wrong_intent.action if hasattr(wrong_intent, "action") else str(wrong_intent)
        params_text = ""
        if hasattr(wrong_intent, "parameters") and wrong_intent.parameters:
            params_text = f"\nParamètres: {wrong_intent.parameters}"

        wrong_label = ttk.Label(
            wrong_frame,
            text=f"Action: {intent_text}{params_text}",
            font=("Arial", 11),
            wraplength=440,
        )
        wrong_label.pack()

        # Correction section
        correction_frame = ttk.LabelFrame(main_frame, text="Interprétation correcte", padding="10")
        correction_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Correction text field
        ttk.Label(
            correction_frame, text="Que vouliez-vous vraiment faire?", font=("Arial", 10)
        ).pack(anchor=tk.W, pady=(0, 5))

        self.correction_text = tk.Text(
            correction_frame, height=4, width=50, font=("Arial", 10), wrap=tk.WORD
        )
        self.correction_text.pack(fill=tk.BOTH, expand=True)
        self.correction_text.focus_set()

        # Optional notes field
        ttk.Label(correction_frame, text="Notes (optionnel):", font=("Arial", 10)).pack(
            anchor=tk.W, pady=(10, 5)
        )

        self.notes_text = tk.Text(
            correction_frame, height=2, width=50, font=("Arial", 10), wrap=tk.WORD
        )
        self.notes_text.pack(fill=tk.BOTH)

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        # Cancel button
        cancel_btn = ttk.Button(button_frame, text="Annuler", command=self._on_cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Submit button
        submit_btn = ttk.Button(
            button_frame, text="Soumettre", command=lambda: self._on_submit(on_submit)
        )
        submit_btn.pack(side=tk.RIGHT)

        # Bind Enter key to submit
        self.dialog.bind("<Return>", lambda e: self._on_submit(on_submit))
        self.dialog.bind("<Escape>", lambda e: self._on_cancel())

    def _on_submit(self, callback: Optional[Callable[[CorrectionResult], None]]):
        """Handle submit button"""
        # Get correction text
        correction = self.correction_text.get("1.0", tk.END).strip()

        if not correction:
            # Show error
            self._show_error("Veuillez entrer l'interprétation correcte")
            return

        # Get notes
        notes = self.notes_text.get("1.0", tk.END).strip()

        # Create result
        self.result = CorrectionResult(
            corrected=True, correct_interpretation=correction, notes=notes if notes else None
        )

        # Call callback if provided
        if callback:
            try:
                callback(self.result)
            except Exception as e:
                print(f"Error in correction callback: {e}")

        # Close dialog
        self.dialog.destroy()

    def _on_cancel(self):
        """Handle cancel button"""
        self.result = CorrectionResult(corrected=False)
        self.dialog.destroy()

    def _show_error(self, message: str):
        """Show error message"""
        error_dialog = tk.Toplevel(self.dialog)
        error_dialog.title("Erreur")
        error_dialog.geometry("300x100")
        error_dialog.resizable(False, False)

        # Center on parent
        error_dialog.transient(self.dialog)
        error_dialog.grab_set()

        # Message
        label = ttk.Label(error_dialog, text=message, padding="20", font=("Arial", 10))
        label.pack()

        # OK button
        ok_btn = ttk.Button(error_dialog, text="OK", command=error_dialog.destroy)
        ok_btn.pack(pady=(0, 10))

        error_dialog.wait_window()


def show_correction_dialog(
    command: str, wrong_intent: Intent, parent: Optional[tk.Tk] = None
) -> Optional[CorrectionResult]:
    """
    Convenience function to show correction dialog

    Args:
        command: Original command text
        wrong_intent: The intent that was incorrectly detected
        parent: Optional parent window

    Returns:
        CorrectionResult if user submitted, None if cancelled
    """
    dialog = CorrectionDialog(parent)
    return dialog.show(command, wrong_intent)


# Example usage
if __name__ == "__main__":
    # Test the dialog
    from janus.runtime.core.contracts import Intent

    # Create a test intent
    test_intent = Intent(
        action="open_app",
        parameters={"app_name": "Chrome"},
        confidence=0.8,
        raw_command="ouvre Firefox",
    )

    # Show dialog
    result = show_correction_dialog(command="ouvre Firefox", wrong_intent=test_intent)

    if result and result.corrected:
        print(f"User correction: {result.correct_interpretation}")
        if result.notes:
            print(f"Notes: {result.notes}")
    else:
        print("User cancelled")
