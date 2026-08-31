"""Visual diff module - generates highlighted difference images from Before/After screenshots.

IMPORTANT DESIGN DECISION:
Visual diff (pixel-based comparison) is inherently noisy for real estate portal pages
because property images, prices, and listing content change daily. This module applies
aggressive filtering to only produce a diff image when there are CLEAR structural/layout
changes (e.g., section moved, component added/removed, major color scheme change).

If the diff would be mostly noise (too many scattered small changes), this module
returns None and the system relies on the text-based DOM diff summary instead.
"""

from dataclasses import dataclass
from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw, ImageFilter


# Only show diff regions if they represent a SIGNIFICANT portion of the page
# AND are concentrated (not scattered pixel noise)
_BLOCK_SIZE = 32            # Large blocks = less sensitive to small pixel changes
_PIXEL_THRESHOLD = 60       # High threshold = ignore subtle color/rendering differences
_MIN_REGION_AREA = 3000     # ~55x55px以上で表示（旧: 5000=70x70px）
_MAX_REGIONS = 30           # 最大30領域まで許容（旧: 15 → 不動産ポータルでは複数セクション変化が多いため緩和）
_MIN_REGION_CONCENTRATION = 0.005  # 0.5%以上に緩和（旧: 1% → UI変更でも面積が小さいケースに対応）

# Padding (px) added around each cropped change region
_CROP_PADDING = 40

# Vertical gap (px) above which separate regions are cropped individually and stacked.
# Regions closer than this threshold are merged into one bounding box.
# 300px ≒ 約2〜3セクション分の間隔を目安に設定。
_STRIP_GAP_THRESHOLD = 300

# Height (px) of the separator bar drawn between stacked strips
_STRIP_SEPARATOR_HEIGHT = 8


@dataclass
class VisualDiffResult:
    """Result of a visual diff analysis.

    Attributes:
        diff_image: Full-page JPEG annotated with red rectangles over changed areas.
        before_crop: Merged JPEG crop from the before image covering all change regions.
        after_crop: Merged JPEG crop from the after image covering all change regions.
        regions: Bounding boxes [(x1,y1,x2,y2)] of detected change areas.
        skip_reason: None when diff was generated; human-readable reason when skipped.
    """
    diff_image: bytes
    before_crop: bytes
    after_crop: bytes
    regions: list[tuple[int, int, int, int]]
    skip_reason: Optional[str] = None


# Sentinel value returned instead of None so callers can log the reason.
class _SkippedDiff:
    """Returned by generate_visual_diff() when diff generation was skipped."""
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def __bool__(self) -> bool:  # allows `if result:` to be False
        return False


def _encode_jpeg(img: Image.Image, quality: int = 80) -> bytes:
    """Encode a PIL image as JPEG and return bytes."""
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def _merged_crop(img: Image.Image, regions: list[tuple[int, int, int, int]]) -> bytes:
    """Return a single JPEG crop that covers the union of all change regions (with padding).

    When regions are spread far apart vertically (gap > _STRIP_GAP_THRESHOLD), each
    cluster is cropped individually and stacked vertically with a separator bar so the
    viewer can see all changed areas without irrelevant content in between.

    For closely spaced regions the legacy bounding-box union is used.
    """
    return _encode_jpeg(_build_strip_image(img, regions))


def _build_strip_image(img: Image.Image, regions: list[tuple[int, int, int, int]]) -> Image.Image:
    """Build a vertically-stacked strip image from change regions.

    Algorithm:
    1. Sort regions by y1.
    2. Group consecutive regions whose vertical gap is < _STRIP_GAP_THRESHOLD into clusters.
    3. For each cluster compute a padded bounding box crop.
    4. Concatenate all crops with a thin separator bar between them.
    """
    w, h = img.size
    pad = _CROP_PADDING

    # Sort by top-y
    sorted_regions = sorted(regions, key=lambda r: r[1])

    # Group into clusters based on vertical gap
    clusters: list[list[tuple[int, int, int, int]]] = []
    current_cluster = [sorted_regions[0]]
    for region in sorted_regions[1:]:
        prev_y2 = max(r[3] for r in current_cluster)
        gap = region[1] - prev_y2
        if gap < _STRIP_GAP_THRESHOLD:
            current_cluster.append(region)
        else:
            clusters.append(current_cluster)
            current_cluster = [region]
    clusters.append(current_cluster)

    # Crop each cluster to a padded bounding box
    strips: list[Image.Image] = []
    strip_width = 0
    for cluster in clusters:
        cx1 = max(0, min(r[0] for r in cluster) - pad)
        cy1 = max(0, min(r[1] for r in cluster) - pad)
        cx2 = min(w, max(r[2] for r in cluster) + pad)
        cy2 = min(h, max(r[3] for r in cluster) + pad)
        strip = img.crop((cx1, cy1, cx2, cy2))
        strips.append(strip)
        strip_width = max(strip_width, strip.width)

    if len(strips) == 1:
        return strips[0]

    # Stack strips vertically with separator bars
    sep_h = _STRIP_SEPARATOR_HEIGHT
    total_height = sum(s.height for s in strips) + sep_h * (len(strips) - 1)
    canvas = Image.new("RGB", (strip_width, total_height), (230, 230, 230))

    y_offset = 0
    for i, strip in enumerate(strips):
        # Center-align narrower strips
        x_offset = (strip_width - strip.width) // 2
        canvas.paste(strip, (x_offset, y_offset))
        y_offset += strip.height
        if i < len(strips) - 1:
            # Draw separator: slightly darker gray band
            sep_region = Image.new("RGB", (strip_width, sep_h), (180, 180, 180))
            canvas.paste(sep_region, (0, y_offset))
            y_offset += sep_h

    return canvas


def generate_visual_diff(
    before_bytes: bytes,
    after_bytes: bytes,
    mask_regions: Optional[list[tuple[int, int, int, int]]] = None,
) -> "VisualDiffResult | _SkippedDiff":
    """Generate a visual diff ONLY when changes are clearly structural.

    Returns a _SkippedDiff (falsy) instead of None so callers can log skip_reason.

    Skip conditions:
    - Page height changed > 50% (whole layout shifted, pixel diff too noisy)
    - Width mismatch (viewport inconsistency)
    - No regions found after size filtering
    - Too many scattered regions (dynamic content noise)
    - Total changed area < MIN_REGION_CONCENTRATION (change too small)

    Args:
        before_bytes: PNG/JPEG bytes of the before screenshot.
        after_bytes: PNG/JPEG bytes of the after screenshot.
        mask_regions: Ignored (kept for API compatibility).

    Returns:
        VisualDiffResult on success, _SkippedDiff (with .reason) when skipped.
    """
    try:
        before_img = Image.open(BytesIO(before_bytes)).convert("RGB")
        after_img = Image.open(BytesIO(after_bytes)).convert("RGB")

        before_w, before_h = before_img.size
        after_w, after_h = after_img.size

        # If page height changed significantly (>50%), the whole layout shifted too much.
        # Pixel comparison would flag everything below the change point.
        # NOTE: Threshold is intentionally loose (50%) to handle real estate portals where
        # listing count changes cause moderate height fluctuation. Full-page screenshots are
        # NOT stored as fallback by design — storage cost reduction is the priority.
        # See: .kiro/steering/guide.md (visual diff design decisions)
        height_diff_ratio = abs(after_h - before_h) / before_h if before_h > 0 else 0
        if height_diff_ratio > 0.50:
            return _SkippedDiff(
                f"height changed too much ({before_h}px → {after_h}px, {height_diff_ratio:.0%} diff > 50% threshold)"
            )

        # If width is different (viewport mismatch), skip entirely
        if before_w != after_w:
            return _SkippedDiff(f"width mismatch (before={before_w}px, after={after_w}px)")

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
            return _SkippedDiff(
                f"no regions found after size filtering (min area: {_MIN_REGION_AREA}px²)"
            )

        # If too many separate regions, it's likely dynamic content noise
        if len(regions) > _MAX_REGIONS:
            return _SkippedDiff(
                f"too many scattered regions ({len(regions)} > {_MAX_REGIONS} threshold), likely dynamic content noise"
            )

        # Check concentration: if total changed area is tiny relative to image, skip
        total_image_area = after_w * after_h
        total_change_area = sum((r[2] - r[0]) * (r[3] - r[1]) for r in regions)
        concentration = total_change_area / total_image_area
        if concentration < _MIN_REGION_CONCENTRATION:
            return _SkippedDiff(
                f"change area too small ({concentration:.2%} < {_MIN_REGION_CONCENTRATION:.2%} threshold, "
                f"{total_change_area}px² / {total_image_area}px²)"
            )

        # Passed all filters: generate the annotated diff image (full-page with red rectangles)
        annotated = after_img.copy().convert("RGBA")
        overlay = Image.new("RGBA", annotated.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        for (x1, y1, x2, y2) in regions:
            draw.rectangle([x1, y1, x2, y2], fill=(255, 0, 0, 35), outline=(255, 50, 50, 200), width=3)

        annotated = Image.alpha_composite(annotated, overlay).convert("RGB")

        diff_output = BytesIO()
        # Use JPEG for the full-page diff image to save space
        annotated.save(diff_output, format="JPEG", quality=75, optimize=True)

        # Generate merged crops (single bounding-box covering all changed regions)
        # before_img may have been resized above, so use the current objects
        before_crop_bytes = _merged_crop(before_img, regions)
        after_crop_bytes = _merged_crop(after_img, regions)

        return VisualDiffResult(
            diff_image=diff_output.getvalue(),
            before_crop=before_crop_bytes,
            after_crop=after_crop_bytes,
            regions=regions,
        )

    except Exception as e:
        print(f"    [VisualDiff] Failed to generate diff: {e}")
        return _SkippedDiff(f"exception during processing: {e}")


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
