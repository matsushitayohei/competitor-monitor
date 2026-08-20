"""Visual diff module - generates highlighted difference images from Before/After screenshots.

IMPORTANT DESIGN DECISION:
Visual diff (pixel-based comparison) is inherently noisy for real estate portal pages
because property images, prices, and listing content change daily. This module applies
aggressive filtering to only produce a diff image when there are CLEAR structural/layout
changes (e.g., section moved, component added/removed, major color scheme change).

If the diff would be mostly noise (too many scattered small changes), this module
returns None and the system relies on the text-based DOM diff summary instead.
"""

from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter


# Only show diff regions if they represent a SIGNIFICANT portion of the page
# AND are concentrated (not scattered pixel noise)
_BLOCK_SIZE = 32            # Large blocks = less sensitive to small pixel changes
_PIXEL_THRESHOLD = 60       # High threshold = ignore subtle color/rendering differences
_MIN_REGION_AREA = 3000     # Relaxed: ~55x55px以上で表示（旧: 5000=70x70px）
_MAX_REGIONS = 15           # Relaxed: 最大15領域まで許容（旧: 5）
_MIN_REGION_CONCENTRATION = 0.01  # Relaxed: 1%以上に緩和（旧: 2%）


def generate_visual_diff(
    before_bytes: bytes,
    after_bytes: bytes,
    mask_regions: Optional[list[tuple[int, int, int, int]]] = None,
) -> Optional[bytes]:
    """Generate a visual diff ONLY when changes are clearly structural.

    Returns None (no diff image) when:
    - Images are different sizes (page length changed = too much noise)
    - Too many scattered change regions (dynamic content noise)
    - Changes are too small to be meaningful

    Args:
        before_bytes: PNG bytes of the before screenshot.
        after_bytes: PNG bytes of the after screenshot.
        mask_regions: Ignored (kept for API compatibility, masking approach deprecated).

    Returns:
        PNG bytes of the diff image, or None if changes are noisy/insignificant.
    """
    try:
        before_img = Image.open(BytesIO(before_bytes)).convert("RGB")
        after_img = Image.open(BytesIO(after_bytes)).convert("RGB")

        before_w, before_h = before_img.size
        after_w, after_h = after_img.size

        # If page height changed significantly (>25%), the whole layout shifted.
        # Pixel comparison would flag everything below the change point.
        # In this case, text summary is more useful than a noisy diff image.
        if before_h > 0 and abs(after_h - before_h) / before_h > 0.25:
            return None

        # If width is different (viewport mismatch), skip entirely
        if before_w != after_w:
            return None

        # Resize height to match (minor height differences from dynamic content loading)
        if before_img.size != after_img.size:
            before_img = before_img.resize(after_img.size, Image.LANCZOS)

        # Compute difference
        diff_mask = _compute_diff_mask(before_img, after_img)

        # Find changed regions with strict thresholds
        regions = _find_change_regions(diff_mask)

        # Filter small regions
        regions = [
            r for r in regions
            if (r[2] - r[0]) * (r[3] - r[1]) >= _MIN_REGION_AREA
        ]

        if not regions:
            return None

        # If too many separate regions, it's likely dynamic content noise
        if len(regions) > _MAX_REGIONS:
            return None

        # Check concentration: if total changed area is tiny relative to image, skip
        total_image_area = after_w * after_h
        total_change_area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in regions)
        if total_change_area / total_image_area < _MIN_REGION_CONCENTRATION:
            return None

        # Passed all filters: generate the annotated image
        result = after_img.copy().convert("RGBA")
        overlay = Image.new("RGBA", result.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for (x1, y1, x2, y2) in regions:
            draw.rectangle([x1, y1, x2, y2], fill=(255, 0, 0, 35), outline=(255, 50, 50, 200), width=3)

        result = Image.alpha_composite(result, overlay)
        result = result.convert("RGB")

        output = BytesIO()
        result.save(output, format="PNG", optimize=True)
        return output.getvalue()

    except Exception as e:
        print(f"    [VisualDiff] Failed to generate diff: {e}")
        return None


def _compute_diff_mask(before: Image.Image, after: Image.Image) -> Image.Image:
    """Compute a grayscale difference mask with aggressive noise reduction."""
    import numpy as np

    before_arr = np.array(before, dtype=np.int16)
    after_arr = np.array(after, dtype=np.int16)

    diff = np.abs(before_arr - after_arr)
    diff_max = diff.max(axis=2).astype(np.uint8)

    diff_img = Image.fromarray(diff_max, mode="L")
    # Aggressive blur to eliminate single-pixel and anti-aliasing noise
    diff_img = diff_img.filter(ImageFilter.MedianFilter(size=5))

    return diff_img


def _find_change_regions(
    diff_mask: Image.Image,
) -> list[tuple[int, int, int, int]]:
    """Find rectangular regions with significant changes."""
    import numpy as np

    mask_arr = np.array(diff_mask)
    h, w = mask_arr.shape
    changed_blocks = []

    for y in range(0, h, _BLOCK_SIZE):
        for x in range(0, w, _BLOCK_SIZE):
            block = mask_arr[y:y + _BLOCK_SIZE, x:x + _BLOCK_SIZE]
            if block.mean() > _PIXEL_THRESHOLD:
                changed_blocks.append((x, y, min(x + _BLOCK_SIZE, w), min(y + _BLOCK_SIZE, h)))

    return _merge_regions(changed_blocks, margin=_BLOCK_SIZE * 2)


def _merge_regions(
    regions: list[tuple[int, int, int, int]], margin: int = 64
) -> list[tuple[int, int, int, int]]:
    """Merge overlapping or nearby regions into larger bounding boxes."""
    if not regions:
        return []

    regions.sort(key=lambda r: (r[1], r[0]))
    merged = []
    current = list(regions[0])

    for x1, y1, x2, y2 in regions[1:]:
        if (x1 <= current[2] + margin and y1 <= current[3] + margin and
                x2 >= current[0] - margin and y2 >= current[1] - margin):
            current[0] = min(current[0], x1)
            current[1] = min(current[1], y1)
            current[2] = max(current[2], x2)
            current[3] = max(current[3], y2)
        else:
            merged.append(tuple(current))
            current = [x1, y1, x2, y2]

    merged.append(tuple(current))
    return merged
