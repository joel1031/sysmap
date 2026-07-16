// Coloring code, in both themes at once.
//
// Shiki emits one variable per theme on every token, and the stylesheet picks
// which one wins off the `data-theme` we already set on <html>. So the theme
// toggle keeps working with no second palette to maintain by hand — which is
// why Shiki and not a regex highlighter.
//
// It is loaded on demand: it costs ~124kB gzipped, and someone reading the map
// without ever opening a file shouldn't pay for it. Only the grammars we can
// actually meet are pulled in (CODE_EXT is the TS/JS family), with the
// JavaScript engine rather than the WASM one.

import type { createHighlighterCore } from 'shiki/core';

type Core = Awaited<ReturnType<typeof createHighlighterCore>>;

const LANGS: Record<string, string> = {
  ts: 'typescript', cts: 'typescript', mts: 'typescript',
  tsx: 'tsx',
  js: 'javascript', mjs: 'javascript', cjs: 'javascript',
  jsx: 'jsx',
};

export const langOf = (path: string) => LANGS[path.split('.').pop() ?? ''] ?? 'typescript';

let engine: Promise<Core> | null = null;

function highlighter(): Promise<Core> {
  if (!engine) {
    engine = (async () => {
      const [core, js, dark, light, typescript, tsx, javascript, jsx] = await Promise.all([
        import('shiki/core'),
        import('shiki/engine/javascript'),
        import('@shikijs/themes/github-dark-default'),
        import('@shikijs/themes/github-light-default'),
        import('@shikijs/langs/typescript'),
        import('@shikijs/langs/tsx'),
        import('@shikijs/langs/javascript'),
        import('@shikijs/langs/jsx'),
      ]);
      return core.createHighlighterCore({
        themes: [dark.default, light.default],
        langs: [typescript.default, tsx.default, javascript.default, jsx.default],
        engine: js.createJavaScriptRegexEngine(),
      });
    })();
    engine.catch(() => (engine = null)); // a failed load shouldn't be permanent
  }
  return engine;
}

/** `code` as HTML, colored for both themes. `startLine` numbers the lines from
 *  where the window actually begins; `mark` is the one line to call out — the
 *  reference you came here for. */
export async function highlight(
  code: string,
  lang: string,
  startLine: number,
  mark?: number,
): Promise<string> {
  const hl = await highlighter();
  return hl.codeToHtml(code, {
    lang,
    themes: { light: 'github-light-default', dark: 'github-dark-default' },
    defaultColor: false, // emit variables for both and let the CSS choose
    cssVariablePrefix: '--sh-',
    transformers: [
      {
        line(node, i) {
          const n = startLine + i - 1;
          node.properties['data-line'] = String(n);
          if (n === mark) this.addClassToHast(node, 'marked');
        },
      },
    ],
  });
}
