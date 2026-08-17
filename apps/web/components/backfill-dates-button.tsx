"use client";

import { useState } from "react";

interface BackfillResult {
  mode: string;
  totalWithoutDate: number;
  updated: number;
  stillNoDate: number;
  updatedArticles: { id: string; title: string; date: string }[];
  noDateArticles: { id: string; title: string }[];
}

export function BackfillDatesButton() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BackfillResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleDryRun() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/backfill-dates?dry-run=true");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleExecute() {
    if (!confirm("日付のバックフィルを実行しますか？")) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/backfill-dates");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6 max-w-2xl">
      <h2 className="text-lg font-semibold text-gray-900 mb-2">
        プレス記事 日付バックフィル
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        公開日が未設定の記事について、本文テキストから日付を抽出して補完します。
      </p>

      <div className="flex gap-3">
        <button
          onClick={handleDryRun}
          disabled={loading}
          className="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50"
        >
          {loading ? "確認中..." : "プレビュー（dry-run）"}
        </button>
        <button
          onClick={handleExecute}
          disabled={loading}
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "実行中..." : "実行"}
        </button>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="p-3 bg-gray-50 rounded text-sm">
            <p>モード: <span className="font-medium">{result.mode}</span></p>
            <p>日付なし記事数: <span className="font-medium">{result.totalWithoutDate}</span></p>
            <p>更新{result.mode === "dry-run" ? "予定" : "済み"}: <span className="font-medium text-green-700">{result.updated}</span></p>
            <p>日付抽出不可: <span className="font-medium text-orange-600">{result.stillNoDate}</span></p>
          </div>

          {result.updatedArticles.length > 0 && (
            <details className="text-sm">
              <summary className="cursor-pointer text-blue-600 hover:underline">
                更新{result.mode === "dry-run" ? "対象" : "済み"}一覧 ({result.updatedArticles.length}件)
              </summary>
              <ul className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                {result.updatedArticles.map((a) => (
                  <li key={a.id} className="text-gray-600">
                    <span className="text-gray-400">{a.date}</span> {a.title}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
