/**
 * Truncate a title string for display purposes.
 * Returns original if ≤maxLength, otherwise truncates to maxLength + "..."
 */
export function truncateTitle(title: string, maxLength: number = 80): string {
  if (title.length <= maxLength) {
    return title;
  }
  return title.slice(0, maxLength) + "...";
}
