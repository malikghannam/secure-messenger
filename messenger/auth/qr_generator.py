"""
QR Code Generator for TOTP Setup

Generates QR codes for TOTP provisioning URIs in both ASCII art format
(for CLI/terminal) and image format (for Desktop GUI).
"""

import os
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    logger.warning("qrcode library not available")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillow library not available")


class QRCodeGenerator:
    """
    Generate QR codes for TOTP setup.
    
    Supports:
    - ASCII art QR codes for CLI/terminal display
    - PNG image QR codes for Desktop GUI
    """
    
    def __init__(self):
        """Initialize QR code generator."""
        if not QR_AVAILABLE:
            raise RuntimeError("qrcode library is required. Install with: pip install qrcode")
    
    def generate_ascii(self, uri: str) -> str:
        """
        Generate ASCII art QR code for CLI/terminal display.
        
        Args:
            uri: The otpauth:// URI to encode
            
        Returns:
            ASCII art string representation of QR code
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        # Generate ASCII representation
        modules = qr.get_matrix()
        
        lines = []
        for row in modules:
            line = ""
            for cell in row:
                # Use block characters for better visibility
                line += "██" if cell else "  "
            lines.append(line)
        
        return "\n".join(lines)
    
    def generate_ascii_inverted(self, uri: str) -> str:
        """
        Generate inverted ASCII art QR code (white on black terminals).
        
        Args:
            uri: The otpauth:// URI to encode
            
        Returns:
            Inverted ASCII art string representation of QR code
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        modules = qr.get_matrix()
        
        lines = []
        for row in modules:
            line = ""
            for cell in row:
                # Inverted: empty for black, filled for white
                line += "  " if cell else "██"
            lines.append(line)
        
        return "\n".join(lines)
    
    def generate_image(self, uri: str, path: str) -> str:
        """
        Generate PNG QR code image file.
        
        Args:
            uri: The otpauth:// URI to encode
            path: File path to save the PNG image
            
        Returns:
            The path where the image was saved
        """
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow library is required for image generation")
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        
        img.save(path)
        logger.info(f"QR code image saved to {path}")
        
        return path
    
    def generate_image_bytes(self, uri: str) -> bytes:
        """
        Generate PNG QR code as bytes (for embedding in UI).
        
        Args:
            uri: The otpauth:// URI to encode
            
        Returns:
            PNG image as bytes
        """
        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow library is required for image generation")
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()


# Global instance
_qr_generator: Optional[QRCodeGenerator] = None


def get_qr_generator() -> QRCodeGenerator:
    """Get or create the global QR code generator instance."""
    global _qr_generator
    if _qr_generator is None:
        _qr_generator = QRCodeGenerator()
    return _qr_generator
