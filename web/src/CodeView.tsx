import { useEffect, useState } from 'react';
import { fetchFile } from './api';
import { highlight, langOf } from './highlight';

const REPO = new URLSearchParams(window.location.search).get('repo') ?? '';

// How much code to show around a reference. Enough to see how the line is
// used, little enough to take in at a glance — the whole file would bury the
// line you came for, and the line alone would strand you with no context.
const WINDOW = 8;

const base = (p: string) => p.split('/').pop() ?? p;

/**
 * A piece of a source file. Given a line, it opens a window around it and
 * marks it; given none, it shows the file from the top.
 */
export function CodeView({
  path,
  line,
  caption,
}: {
  path: string;
  line?: number | null;
  caption?: string;
}) {
  const [text, setText] = useState<string | null>(null);
  const [html, setHtml] = useState('');
  const [error, setError] = useState(false);
  const [whole, setWhole] = useState(false);

  useEffect(() => {
    let alive = true;
    setText(null);
    setError(false);
    setWhole(false);
    fetchFile(REPO, path)
      .then((t) => alive && setText(t))
      .catch(() => alive && setError(true));
    return () => {
      alive = false;
    };
  }, [path]);

  useEffect(() => {
    if (text === null) return;
    let alive = true;
    const lines = text.split('\n');
    const windowed = !!line && !whole;
    const from = windowed ? Math.max(1, line - WINDOW) : 1;
    const to = windowed ? Math.min(lines.length, line + WINDOW) : lines.length;
    highlight(lines.slice(from - 1, to).join('\n'), langOf(path), from, line ?? undefined)
      .then((h) => alive && setHtml(h))
      .catch(() => alive && setError(true));
    return () => {
      alive = false;
    };
  }, [text, whole, line, path]);

  if (error) return <div className="panel-fail">Couldn't read {base(path)}.</div>;

  return (
    <div className="code">
      <div className="code-head">
        {caption && <span className="code-cap">{caption}</span>}
        <span className="code-path" title={path}>
          {base(path)}
          {line ? `:${line}` : ''}
        </span>
      </div>
      {text === null ? (
        <div className="panel-dim code-wait">Reading…</div>
      ) : (
        <>
          <div className="code-body" dangerouslySetInnerHTML={{ __html: html }} />
          {!!line && (
            <button className="code-more" onClick={() => setWhole((v) => !v)}>
              {whole ? 'show less' : `expand — the whole file (${text.split('\n').length} lines)`}
            </button>
          )}
        </>
      )}
    </div>
  );
}
