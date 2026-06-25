"""Visual diff generation using Pillow."""

from PIL import Image, ImageChops
import io


def generate_visual_diff(before_bytes: bytes, after_bytes: bytes) -> bytes:
    """Generate a visual diff image highlighting changed areas."""
    before = Image.open(io.BytesIO(before_bytes)).convert('RGB')
    after = Image.open(io.BytesIO(after_bytes)).convert('RGB')
    
    # Resize to same dimensions if needed
    if before.size != after.size:
        after = after.resize(before.size)
    
    # Compute difference
    diff = ImageChops.difference(before, after)
    
    # Enhance diff visibility
    # TODO: Add red overlay on changed areas
    
    output = io.BytesIO()
    diff.save(output, format='PNG')
    return output.getvalue()
