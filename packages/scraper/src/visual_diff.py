"""Visual diff module - generates highlighted difference images from Before/After screenshots.

This module focuses on detecting STRUCTURAL UI changes by masking out
dynamic content areas (property listings, prices, images, ads) before comparison.
This prevents daily-changing content from flooding the diff with noise.
"""

from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw


# Minimum region area (in pixels) to consider as a meaningful change
# Filters out tiny 1-2 block differences from anti-aliasing or font rendering
_MIN_REGION_AREA = 2000  # ~45x45px equivalent

# Block size for region detection - larger = fewer false positives, less precise
_BLOCK_SIZE = 24

# Threshold for considering a block as "changed"
# Higher = ignore subtle color shifts (font rendering, compression artifacts)
_PIXEL_THRESHOLD = 45


def generate_visual_diff(
    before_bytes: bytes,
    after_bytes: bytes,
    mask_regions: Optional[list[tuple[int, int, int, int]]] = None,
) -> Optional[bytes]:
    """Generate a visual diff image highlighting meaningful UI/UX changes.

    Uses masked comparison to exclude dynamic content areas from diff detection.
    Only highlights regions with substantial structural differences.

    Args:
        before_bytes: PNG bytes of the before screenshot.
        after_bytes: PNG bytes of the after screenshot.
        mask_regions: Optional list of (x, y, width, height) regions to exclude
                      from comparison (dynamic content areas).

    Returns:
        PNG bytes of the diff image with red highlights on structural changes,
        or None if no meaningful changes or on failure.
    """
    try:
        before_img = Image.open(BytesIO(before_bytes)).convert("RGB")
        after_img = Image.open(BytesIO(after_bytes)).convert("RGB")

        # Resize to match dimensions (use after as base)
        if before_img.size != after_img.size:
            before_img = before_img.resize(after_img.size, Image.LANCZOS)

        width, height = after_img.size

        # Apply masks to both images (fill masked regions with identical gray)
        if mask_regions:
            before_img = _apply_masks(before_img, mask_regions)
            after_img_masked = _apply_masks(after_img.copy(), mask_regions)
        else:
            after_img_masked = after_img.copy()

        # Compute pixel difference on masked images
        diff_mask = _compute_diff_mask(before_img, after_img_masked)

        # Find changed regions (with higher threshold to reduce noise)
        regions = _find_change_regions(
            diff_mask,
            block_size=_BLOCK_SIZE,
            threshold=_PIXEL_THRESHOLD,
        )

        # Filter out small regions (noise from font rendering, compression etc.)
        regions = [
            r for r in regions
            if (r[2] - r[0]) * (r[3] - r[1]) >= _MIN_REGION_AREA
        ]

        if not regions:
            # No meaningful visual changes detected
            return None

        # Create output: ORIGINAL after image (unmasked) with red highlights
        result = after_img.copy().convert("RGBA") if not mask_regions else Image.open(BytesIO(after_bytes)).convert("RGBA")
        overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for (x1, y1, x2, y2) in regions:
            # Semi-transparent red fill with clear red border
            draw.rectangle([x1, y1, x2, y2], fill=(255, 0, 0, 40), outline=(255, 0, 0, 220), width=2)

        result = Image.alpha_composite(result, overlay)
        result = result.convert("RGB")

        # Save to bytes
        output = BytesIO()
        result.save(output, format="PNG", optimize=True)
        return output.getvalue()

    except Exception as e:
        print(f"    [VisualDiff] Failed to generate diff: {e}")
        return None


def _apply_masks(img: Image.Image, mask_regions: list[tuple[int, int, int, int]]) -> Image.Image:
    """Fill masked regions with neutral gray to exclude from comparison.

    Args:
        img: Source image to mask.
        mask_regions: List of (x, y, width, height) regions to mask out.

    Returns:
        New image with masked regions filled with gray.
    """
    result = img.copy()
    draw = ImageDraw.Draw(result)
    for (x, y, w, h) in mask_regions:
        draw.rectangle([x, y, x + w, y + h], fill=(128, 128, 128))
    return result


def _compute_diff_mask(before: Image.Image, after: Image.Image) -> Image.Image:
    """Compute a grayscale difference mask between two images.

    Uses blur to reduce pixel-level noise from font rendering and compression.
    """
    import numpy as np

    before_arr = np.array(before, dtype=np.int16)
    after_arr = np.array(after, dtype=np.int16)

    # Absolute difference per channel, then max across channels
    diff = np.abs(before_arr - after_arr)
    diff_max = diff.max(axis=2).astype(np.uint8)

    # Apply slight blur to reduce single-pixel noise
    diff_img = Image.fromarray(diff_max, mode="L")
    from PIL import ImageFilter
    diff_img = diff_img.filter(ImageFilter.MedianFilter(size=3))

    return diff_img


def _find_change_regions(
    diff_mask: Image.Image, block_size: int = 24, threshold: int = 45
) -> list[tuple[int, int, int, int]]:
    """Find rectangular regions with significant changes.

    Uses larger block size and higher threshold than before to reduce
    false positives from dynamic content remnants.

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
    changed_blocks = []

    for y in range(0, h, block_size):
        for x in range(0, w, block_size):
            block = mask_arr[y:y + block_size, x:x + block_size]
            if block.mean() > threshold:
                changed_blocks.append((x, y, min(x + block_size, w), min(y + block_size, h)))

    # Merge adjacent regions with generous margin
    return _merge_regions(changed_blocks, margin=block_size * 2)


def _merge_regions(
    regions: list[tuple[int, int, int, int]], margin: int = 48
) -> list[tuple[int, int, int, int]]:
    """Merge overlapping or adjacent regions into larger bounding boxes.

    Uses a generous margin to consolidate nearby small changes into
    one readable highlight rather than many tiny scattered rectangles.
    """
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
