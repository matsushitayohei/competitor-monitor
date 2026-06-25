export interface ValidationResult {
  valid: boolean;
  fields: Record<string, string>;
}

export function isValidUrl(url: string): boolean {
  // Must start with http:// or https://
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:';
  } catch {
    return false;
  }
}

export function validateServiceInput(data: {
  name?: string;
  displayName?: string;
  baseUrl?: string;
}, options?: { partial?: boolean }): ValidationResult {
  const fields: Record<string, string> = {};
  const partial = options?.partial ?? false;

  // name validation
  if (!partial || data.name !== undefined) {
    if (!data.name || data.name.trim() === '') {
      fields.name = 'サービス名を入力してください';
    } else if (!/^[a-zA-Z0-9-]+$/.test(data.name)) {
      fields.name = 'サービス名は英数字とハイフンのみ使用できます';
    } else if (data.name.length > 50) {
      fields.name = 'サービス名は50文字以内で入力してください';
    }
  }

  // displayName validation
  if (!partial || data.displayName !== undefined) {
    if (!data.displayName || data.displayName.trim() === '') {
      fields.displayName = '表示名を入力してください';
    } else if (data.displayName.length > 100) {
      fields.displayName = '表示名は100文字以内で入力してください';
    }
  }

  // baseUrl validation
  if (!partial || data.baseUrl !== undefined) {
    if (!data.baseUrl || data.baseUrl.trim() === '') {
      fields.baseUrl = 'URLを入力してください';
    } else if (!isValidUrl(data.baseUrl)) {
      fields.baseUrl = '有効なURL形式で入力してください';
    }
  }

  return { valid: Object.keys(fields).length === 0, fields };
}

export function validatePageInput(data: {
  url?: string;
  pageType?: string;
  device?: string;
}, options?: { partial?: boolean }): ValidationResult {
  const fields: Record<string, string> = {};
  const partial = options?.partial ?? false;

  // url validation
  if (!partial || data.url !== undefined) {
    if (!data.url || data.url.trim() === '') {
      fields.url = 'URLを入力してください';
    } else if (!isValidUrl(data.url)) {
      fields.url = '有効なURL形式で入力してください';
    }
  }

  // pageType validation
  if (!partial || data.pageType !== undefined) {
    if (!data.pageType) {
      fields.pageType = 'ページ種別を選択してください';
    } else if (!['listing', 'detail'].includes(data.pageType)) {
      fields.pageType = 'ページ種別を選択してください';
    }
  }

  // device validation
  if (!partial || data.device !== undefined) {
    if (!data.device) {
      fields.device = 'デバイスを選択してください';
    } else if (!['pc', 'sp'].includes(data.device)) {
      fields.device = 'デバイスを選択してください';
    }
  }

  return { valid: Object.keys(fields).length === 0, fields };
}
