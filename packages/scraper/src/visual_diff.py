"""Visual diff module - generates highlighted difference images from Before/After screenshots."""

from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter


def generate_visual_diff(before_bytes: bytes, after_bytes: bytes) -> Optional[bytes]:
    """Generate a visual diff image highlighting pixel differences between before and after.

    Creates an image based on the 'after' screenshot with semi-transparent red overlay
    on regions that changed. Returns PNG bytes or None on failure.

    Args:
        before_bytes: PNG bytes of the before screenshot.
        after_bytes: PNG bytes of the after screenshot.

    Returns:
        PNG bytes of the diff image, or None on failure.
    """
    try:
        before_img = Image.open(BytesIO(before_bytes)).convert("RGB")
        after_img = Image.open(BytesIO(after_bytes)).convert("RGB")

        # Resize to match dimensions (use after as base)
        if before_img.size != after_img.size:
            before_img = before_img.resize(after_img.size, Image.LANCZOS)

        # Compute pixel difference
        diff_img = _compute_diff_mask(before_img, after_img)

        # Create output: after image with red highlights on changed areas
        result = after_img.copy().convert("RGBA")
        overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Find changed regions and draw red rectangles
        regions = _find_change_regions(diff_img, block_size=16, threshold=30)
        for (x1, y1, x2, y2) in regions:
            # Semi-transparent red fill
            draw.rectangle([x1, y1, x2, y2], fill=(255, 0, 0, 60), outline=(255, 0, 0, 200))

        result = Image.alpha_composite(result, overlay)
        result = result.convert("RGB")

        # Save to bytes
        output = BytesIO()
        result.save(output, format="PNG", optimize=True)
        return output.getvalue()

    except Exception as e:
        print(f"    [VisualDiff] Failed to generate diff: {e}")
        return None


def _compute_diff_mask(before: Image.Image, after: Image.Image) -> Image.Image:
    """Compute a grayscale difference mask between two images."""
    import numpy as np

    before_arr = np.array(before, dtype=np.int16)
    after_arr = np.array(after, dtype=np.int16)

    # Absolute difference per channel, then max across channels
    diff = np.abs(before_arr - after_arr)
    diff_max = diff.max(axis=2).astype(np.uint8)

    return Image.fromarray(diff_max, mode="L")


def _find_change_regions(
    diff_mask: Image.Image, block_size: int = 16, threshold: int = 30
) -> list[tuple[int, int, int, int]]:
    """Find rectangular regions with significant changes.

    Divides the image into blocks and marks blocks where average
    difference exceeds the threshold.

    Args:
        diff_mask: Grayscale difference image.
        block_size: Size of blocks to analyze.
        threshold: Minimum average difference to consider a block changed.

    Returns:
        List of (x1, y1, x2, y2) bounding boxes of changed regions.
    """
    import numpy as np

    mask_arr = np.array(diff_mask)
    h, w = mask_arr.shape
    regions = []

    for y in range(0, h, block_size):
        for x in range(0, w, block_size):
            block = mask_arr[y:y + block_size, x:x + block_size]
            if block.mean() > threshold:
                regions.append((x, y, min(x + block_size, w), min(y + block_size, h)))

    # Merge adjacent regions
    return _merge_regions(regions, block_size)


def _merge_regions(
    regions: list[tuple[int, int, int, int]], margin: int = 16
) -> list[tuple[int, int, int, int]]:
    """Merge overlapping or adjacent regions into larger bounding boxes."""
    if not regions:
        return []

    # Sort by y then x
    regions.sort(key=lambda r: (r[1], r[0]))

    merged = []
    current = list(regions[0])

    for x1, y1, x2, y2 in regions[1:]:
        # Check if this region overlaps or is adjacent to current
        if (x1 <= current[2] + margin and y1 <= current[3] + margin and
                x2 >= current[0] - margin and y2 >= current[1] - margin):
            # Merge
            current[0] = min(current[0], x1)
            current[1] = min(current[1], y1)
            current[2] = max(current[2], x2)
            current[3] = max(current[3], y2)
        else:
            merged.append(tuple(current))
            current = [x1, y1, x2, y2]

    merged.append(tuple(current))
    return merged
