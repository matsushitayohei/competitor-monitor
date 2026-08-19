"use client";

import { useState, useMemo } from "react";

interface DiffViewerProps {
  diffText: string;
}

interface DiffLine {
  type: "add" | "remove" | "context" | "header";
  content: string;
  lineNum?: number;
}

// コンテキスト行の折りたたみ: 連続するcontext行が COLLAPSE_THRESHOLD を超えたら折りたたむ
const COLLAPSE_THRESHOLD = 4;

export function DiffViewer({ diffText }: DiffViewerProps) {
  const [expandedSections, setExpandedSections] = useState<Set<number>>(new Set());

  const { lines, stats } = useMemo(() => {
    const rawLines = diffText.split("\n");
    const parsed: DiffLine[] = [];
    let lineNum = 0;

    for (const line of rawLines) {
      if (line.startsWith("@@")) {
        // hunk header — @@ -a,b +c,d @@ から行番号を抽出
        const match = line.match(/@@ -\d+(?:,\d+)? \+(\d+)/);
        if (match) lineNum = parseInt(match[1], 10) - 1;
        parsed.push({ type: "header", content: line });
      } else if (line.startsWith("+") && !line.startsWith("+++")) {
        lineNum++;
        parsed.push({ type: "add", content: line.slice(1), lineNum });
      } else if (line.startsWith("-") && !line.startsWith("---")) {
        parsed.push({ type: "remove", content: line.slice(1) });
      } else if (line.startsWith("---") || line.startsWith("+++")) {
        // ファイルヘッダー行はスキップ
        continue;
      } else {
        lineNum++;
        parsed.push({ type: "context", content: line.startsWith(" ") ? line.slice(1) : line, lineNum });
      }
    }

    const additions = parsed.filter((l) => l.type === "add").length;
    const deletions = parsed.filter((l) => l.type === "remove").length;

    return { lines: parsed, stats: { additions, deletions } };
  }, [diffText]);

  // セクション分け: 連続する context 行をグループ化
  const sections = useMemo(() => {
    const result: { type: "lines" | "collapsed"; startIdx: number; endIdx: number }[] = [];
    let i = 0;

    while (i < lines.length) {
      if (lines[i].type === "context") {
        // 連続する context 行を数える
        const start = i;
        while (i < lines.length && lines[i].type === "context") i++;
        const count = i - start;

        if (count > COLLAPSE_THRESHOLD) {
          // 前後2行は表示、中間を折りたたみ
          if (start > 0) {
            result.push({ type: "lines", startIdx: start, endIdx: start + 2 });
          }
          result.push({ type: "collapsed", startIdx: start + 2, endIdx: i - 2 });
          result.push({ type: "lines", startIdx: i - 2, endIdx: i });
        } else {
          result.push({ type: "lines", startIdx: start, endIdx: i });
        }
      } else {
        const start = i;
        while (i < lines.length && lines[i].type !== "context") i++;
        result.push({ type: "lines", startIdx: start, endIdx: i });
      }
    }
    return result;
  }, [lines]);

  const toggleSection = (startIdx: number) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(startIdx)) next.delete(startIdx);
      else next.add(startIdx);
      return next;
    });
  };

  return (
    <div className="rounded-lg border border-gray-200 overflow-hidden">
      {/* Stats header */}
      <div className="flex items-center gap-3 px-3 py-2 bg-gray-50 border-b border-gray-200">
        <span className="text-xs font-medium text-gray-600">DOM差分</span>
        <span className="text-xs text-green-600 font-mono">+{stats.additions}</span>
        <span className="text-xs text-red-600 font-mono">-{stats.deletions}</span>
        <span className="text-xs text-gray-400">({stats.additions + stats.deletions}行変更)</span>
      </div>

      {/* Diff body */}
      <div className="overflow-x-auto max-h-80 overflow-y-auto bg-gray-900 text-xs font-mono">
        <table className="w-full border-collapse">
          <tbody>
            {sections.map((section, sIdx) => {
              if (section.type === "collapsed" && !expandedSections.has(section.startIdx)) {
                const count = section.endIdx - section.startIdx;
                return (
                  <tr key={`s-${sIdx}`}>
                    <td colSpan={3} className="text-center py-1">
                      <button
                        onClick={() => toggleSection(section.startIdx)}
                        className="text-xs text-blue-400 hover:text-blue-300 bg-gray-800 px-3 py-0.5 rounded hover:bg-gray-700 transition-colors"
                      >
                        ⋯ {count}行を展開
                      </button>
                    </td>
                  </tr>
                );
              }

              const startIdx = section.startIdx;
              const endIdx = section.type === "collapsed" ? section.endIdx : section.endIdx;

              return lines.slice(startIdx, endIdx).map((line, lineIdx) => {
                const globalIdx = startIdx + lineIdx;

                if (line.type === "header") {
                  return (
                    <tr key={`l-${globalIdx}`} className="bg-gray-800/50">
                      <td colSpan={3} className="px-3 py-1 text-cyan-400 text-xs">
                        {line.content}
                      </td>
                    </tr>
                  );
                }

                const bgClass =
                  line.type === "add"
                    ? "bg-green-900/30"
                    : line.type === "remove"
                    ? "bg-red-900/30"
                    : "";
                const textClass =
                  line.type === "add"
                    ? "text-green-300"
                    : line.type === "remove"
                    ? "text-red-300"
                    : "text-gray-400";
                const prefix =
                  line.type === "add" ? "+" : line.type === "remove" ? "-" : " ";

                return (
                  <tr key={`l-${globalIdx}`} className={bgClass}>
                    <td className="w-8 text-right pr-2 text-gray-600 select-none border-r border-gray-700/50 py-0.5">
                      {line.lineNum || ""}
                    </td>
                    <td className="w-4 text-center text-gray-500 select-none py-0.5">
                      <span className={textClass}>{prefix}</span>
                    </td>
                    <td className={`px-2 py-0.5 whitespace-pre-wrap break-all ${textClass}`}>
                      {line.content}
                    </td>
                  </tr>
                );
              });
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
