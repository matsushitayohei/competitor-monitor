export interface PressSourceValidationResult {
  valid: boolean;
  errors: { name?: string; url?: string };
}

const PRESS_SOURCE_NAME_PATTERN = /^[a-zA-Z0-9-]{1,50}$/;

/**
 * プレスソース名のバリデーション
 * 1〜50文字の英数字とハイフンのみ許可
 */
export function validatePressSourceName(name: string): boolean {
  return PRESS_SOURCE_NAME_PATTERN.test(name);
}

/**
 * プレスソースURLのバリデーション
 * 有効な http または https URLのみ許可
 */
export function validatePressSourceUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * プレスソース入力の総合バリデーション
 * partial: true の場合、未指定フィールドはスキップ（編集時の部分バリデーション用）
 */
export function validatePressSourceInput(
  data: { name?: string; url?: string },
  options?: { partial?: boolean }
): PressSourceValidationResult {
  const errors: { name?: string; url?: string } = {};
  const partial = options?.partial ?? false;

  // name validation
  if (!partial || data.name !== undefined) {
    if (!data.name || data.name.trim() === '') {
      errors.name = '名前は1〜50文字の英数字とハイフンのみ使用できます';
    } else if (!validatePressSourceName(data.name)) {
      errors.name = '名前は1〜50文字の英数字とハイフンのみ使用できます';
    }
  }

  // url validation
  if (!partial || data.url !== undefined) {
    if (!data.url || data.url.trim() === '') {
      errors.url = '有効なHTTPまたはHTTPS URLを入力してください';
    } else if (!validatePressSourceUrl(data.url)) {
      errors.url = '有効なHTTPまたはHTTPS URLを入力してください';
    }
  }

  return { valid: Object.keys(errors).length === 0, errors };
}
