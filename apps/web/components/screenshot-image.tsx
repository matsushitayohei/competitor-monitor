"use client";

import { useState } from "react";

interface ScreenshotImageProps {
  src: string;
  alt: string;
  label: string;
  height?: string;
  objectFit?: string;
}

function getProxyUrl(originalUrl: string): string {
  return `/api/screenshots?url=${encodeURIComponent(originalUrl)}`;
}

export function ScreenshotImage({ src, alt, label, height = "h-48", objectFit = "object-cover object-top" }: ScreenshotImageProps) {
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  // Always use proxy to handle both public and private Vercel Blob URLs
  const imageSrc = src.includes(".blob.vercel-storage.com/")
    ? getProxyUrl(src)
    : src;

  if (error) {
    return (
      <div>
        {label && <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>}
        <div className={`w-full ${height} rounded border border-gray-200 bg-gray-50 flex items-center justify-center`}>
          <div className="text-center text-gray-400">
            <svg
              className="mx-auto h-8 w-8 mb-1"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5a1.5 1.5 0 001.5-1.5V5.25a1.5 1.5 0 00-1.5-1.5H3.75a1.5 1.5 0 00-1.5 1.5v14.25a1.5 1.5 0 001.5 1.5z"
              />
            </svg>
            <p className="text-xs">画像を読み込めません</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      {label && <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>}
      <div>
        {loading && (
          <div className={`w-full ${height} rounded border border-gray-200 bg-gray-100 animate-pulse`} />
        )}
        <img
          src={imageSrc}
          alt={alt}
          className={`w-full ${height} ${objectFit} rounded border border-gray-200 ${
            loading ? "hidden" : ""
          }`}
          onLoad={() => setLoading(false)}
          onError={() => {
            setError(true);
            setLoading(false);
          }}
        />
      </div>
    </div>
  );
}
