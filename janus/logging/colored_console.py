"""Enhanced colored logging for Janus terminal output"""
import logging
import sys
from typing import Optional


class Colors:
    """ANSI color codes for terminal output"""
    # Basic colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    # Level-specific formats with icons and colors
    FORMATS = {
        logging.DEBUG: f"{Colors.DIM}🔍 %(message)s{Colors.RESET}",
        logging.INFO: f"{Colors.BRIGHT_CYAN}ℹ️  %(message)s{Colors.RESET}",
        logging.WARNING: f"{Colors.BRIGHT_YELLOW}⚠️  %(message)s{Colors.RESET}",
        logging.ERROR: f"{Colors.BRIGHT_RED}❌ %(message)s{Colors.RESET}",
        logging.CRITICAL: f"{Colors.BOLD}{Colors.BG_RED}{Colors.WHITE} 🚨 %(message)s {Colors.RESET}",
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(message)s")
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class JanusConsoleHandler(logging.StreamHandler):
    """Enhanced console handler with colors and formatting"""
    
    def __init__(self, stream=None):
        super().__init__(stream or sys.stdout)
        self.setFormatter(ColoredFormatter())


def setup_colored_logging(level: int = logging.INFO) -> None:
    """Setup colored logging for the root logger"""
    # Remove existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
    
    # Add our colored handler
    handler = JanusConsoleHandler()
    root.addHandler(handler)
    root.setLevel(level)


def print_banner(title: str, subtitle: Optional[str] = None, color: str = Colors.BRIGHT_CYAN):
    """Print a styled banner"""
    width = 70
    print(f"\n{color}{Colors.BOLD}{'═' * width}")
    print(f"  {title.upper()}")
    if subtitle:
        print(f"  {Colors.DIM}{subtitle}{Colors.RESET}{color}{Colors.BOLD}")
    print(f"{'═' * width}{Colors.RESET}\n")


def print_section(title: str, color: str = Colors.BRIGHT_BLUE):
    """Print a section header"""
    print(f"\n{color}{Colors.BOLD}▶ {title}{Colors.RESET}")


def print_success(message: str):
    """Print a success message"""
    print(f"{Colors.BRIGHT_GREEN}✓{Colors.RESET} {message}")


def print_error(message: str):
    """Print an error message"""
    print(f"{Colors.BRIGHT_RED}✗{Colors.RESET} {message}")


def print_warning(message: str):
    """Print a warning message"""
    print(f"{Colors.BRIGHT_YELLOW}⚠️ {Colors.RESET} {message}")


def print_info(message: str):
    """Print an info message"""
    print(f"{Colors.BRIGHT_CYAN}ℹ️ {Colors.RESET} {message}")


def print_command(text: str):
    """Print a transcribed command"""
    print(f"\n{Colors.BRIGHT_MAGENTA}{Colors.BOLD}🎤 Command:{Colors.RESET} {Colors.WHITE}{text}{Colors.RESET}")


def print_action(action: str):
    """Print an action being taken"""
    print(f"{Colors.BRIGHT_GREEN}  ➜{Colors.RESET} {action}")


def print_thinking():
    """Print thinking indicator"""
    print(f"{Colors.BRIGHT_YELLOW}🤔 Thinking...{Colors.RESET}")


def print_listening():
    """Print listening indicator"""
    print(f"\n{Colors.BRIGHT_CYAN}🎤 Listening...{Colors.RESET} {Colors.DIM}(speak now){Colors.RESET}")


def print_config_item(key: str, value: str, enabled: bool = True):
    """Print a configuration item"""
    icon = "✓" if enabled else "✗"
    color = Colors.BRIGHT_GREEN if enabled else Colors.DIM
    print(f"  {color}{icon}{Colors.RESET} {key}: {Colors.WHITE}{value}{Colors.RESET}")


def print_separator(char: str = "─", color: str = Colors.BRIGHT_BLACK):
    """Print a separator line"""
    print(f"{color}{char * 70}{Colors.RESET}")
