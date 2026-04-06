"""
GPU detection and device management utilities
"""

import platform
from typing import List, Optional

from janus.logging import get_logger

logger = get_logger("gpu_utils")


class GPUDevice:
    """Represents a GPU device"""

    def __init__(self, device_type: str, device_id: int = 0, name: Optional[str] = None):
        self.device_type = device_type  # "cuda", "mps", "cpu"
        self.device_id = device_id
        self.name = name or device_type

    def __str__(self):
        return f"{self.device_type}:{self.device_id}"

    def __repr__(self):
        return f"GPUDevice(type={self.device_type}, id={self.device_id}, name={self.name})"


def detect_gpu_devices() -> List[GPUDevice]:
    """
    Detect available GPU devices

    Returns:
        List of available GPU devices (CUDA, MPS, or CPU fallback)
    """
    devices = []

    # Try CUDA (NVIDIA)
    try:
        import torch

        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                devices.append(GPUDevice("cuda", i, name))
                logger.info(f"✓ CUDA device detected: {name}")
    except ImportError:
        pass
    except Exception as e:
        logger.info(f"CUDA detection failed: {e}")

    # Try MPS (Apple Silicon)
    if not devices:
        try:
            import torch

            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                # MPS is available on Apple Silicon
                devices.append(GPUDevice("mps", 0, "Apple Metal Performance Shaders"))
                logger.info(f"✓ MPS device detected: Apple Metal Performance Shaders")
        except ImportError:
            pass
        except Exception as e:
            logger.info(f"MPS detection failed: {e}")

    # Fallback to CPU
    if not devices:
        devices.append(GPUDevice("cpu", 0, "CPU"))
        logger.warning(
            "⚠️ No GPU detected, using CPU. Performance may be degraded. "
            "For Apple Silicon, ensure PyTorch with MPS support is installed: pip install torch"
        )

    return devices


def get_best_device() -> GPUDevice:
    """
    Get the best available device for computation

    Returns:
        Best available GPUDevice (prefers CUDA > MPS > CPU)
    """
    devices = detect_gpu_devices()

    # Prefer CUDA over MPS over CPU
    for device in devices:
        if device.device_type == "cuda":
            return device

    for device in devices:
        if device.device_type == "mps":
            return device

    # Fallback to CPU
    return devices[0] if devices else GPUDevice("cpu", 0)


def get_whisper_device() -> str:
    """
    Get the appropriate device string for Whisper model

    Returns:
        Device string ("cuda", "mps", or "cpu")
    """
    device = get_best_device()
    return device.device_type


def get_torch_device():
    """
    Get torch device object (if torch is available)

    Returns:
        torch.device object or None if torch not available
    """
    try:
        import torch

        device = get_best_device()

        if device.device_type == "cuda":
            return torch.device(f"cuda:{device.device_id}")
        elif device.device_type == "mps":
            return torch.device("mps")
        else:
            return torch.device("cpu")
    except ImportError:
        return None


def supports_fp16() -> bool:
    """
    Check if the current device supports FP16 computation

    Returns:
        True if FP16 is supported, False otherwise
    """
    device = get_best_device()

    # CUDA devices support FP16
    if device.device_type == "cuda":
        return True

    # Apple Silicon MPS supports FP16
    if device.device_type == "mps":
        return True

    # CPU generally doesn't benefit from FP16
    return False


def print_device_info():
    """Print information about available devices"""
    logger.info("=" * 60)
    logger.info("GPU DEVICE INFORMATION")
    logger.info("=" * 60)

    devices = detect_gpu_devices()
    best = get_best_device()

    logger.info(f"\nAvailable devices: {len(devices)}")
    for device in devices:
        marker = " (SELECTED)" if device.device_type == best.device_type else ""
        logger.info(f"  - {device.name}{marker}")

    logger.info(f"\nBest device: {best.name}")
    logger.info(f"FP16 support: {supports_fp16()}")
    logger.info(f"Platform: {platform.system()} {platform.machine()}")

    # Try to get more detailed info
    try:
        import torch

        logger.info(f"\nPyTorch version: {torch.__version__}")
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"CUDA version: {torch.version.cuda}")
            logger.info(f"CUDA devices: {torch.cuda.device_count()}")

        if hasattr(torch.backends, "mps"):
            logger.info(f"MPS available: {torch.backends.mps.is_available()}")
    except ImportError:
        logger.info("\nPyTorch not installed")

    logger.info("=" * 60)


def get_optimal_device() -> str:
    """
    Auto-detect the best available device for faster-whisper

    Returns:
        Device string ("cuda", "mps", or "cpu")
    """
    try:
        import torch

        if torch.backends.mps.is_available():
            return "mps"  # Mac M1/M2/M3
        elif torch.cuda.is_available():
            return "cuda"  # NVIDIA GPU
        else:
            return "cpu"
    except ImportError:
        return "cpu"


def get_optimal_compute_type(device: str) -> str:
    """
    Get optimal compute_type for faster-whisper based on device

    Args:
        device: Device type ("cuda", "mps", or "cpu")

    Returns:
        Compute type string ("int8", "float16", or "float32")
    """
    compute_types = {
        "cuda": "float16",  # Fast on NVIDIA with FP16 support
        "mps": "float32",  # MPS doesn't support int8 yet
        "cpu": "float32",  # Use float32 on CPU for better quality (int8 degrades French transcription)
    }
    return compute_types.get(device, "float32")  # Safe default


# TICKET-P2-01: MLX detection for Apple Silicon
def is_apple_silicon() -> bool:
    """
    Check if running on Apple Silicon (M1/M2/M3/M4)

    Returns:
        True if running on macOS with ARM64 architecture
    """
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def is_mlx_available() -> bool:
    """
    Check if MLX framework is available for STT acceleration

    Returns:
        True if on Apple Silicon with lightning-whisper-mlx installed
    """
    if not is_apple_silicon():
        return False

    try:
        from lightning_whisper_mlx import LightningWhisperMLX

        return True
    except ImportError:
        return False


def get_best_stt_engine() -> str:
    """
    Get the best available STT engine based on hardware

    Returns:
        Engine name: "mlx" (Apple Silicon), "faster-whisper" (CUDA/CPU), or "whisper" (fallback)
    """
    # TICKET-P2-01: Prefer MLX on Apple Silicon for instant STT
    if is_mlx_available():
        logger.info("✓ Using MLX STT engine (Apple Silicon Neural Engine)")
        return "mlx"

    # Try faster-whisper
    try:
        from faster_whisper import WhisperModel

        device = get_optimal_device()
        logger.info(f"✓ Using faster-whisper STT engine (device: {device})")
        return "faster-whisper"
    except ImportError:
        pass

    # Fallback to standard whisper
    logger.info("Using standard whisper STT engine (fallback)")
    return "whisper"
