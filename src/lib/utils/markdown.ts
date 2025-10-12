import { marked } from 'marked';
import createDOMPurify from 'dompurify';
// Use core build and register common languages for reliable highlighting
import hljs from 'highlight.js/lib/core';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import bash from 'highlight.js/lib/languages/bash';
import json from 'highlight.js/lib/languages/json';
import xml from 'highlight.js/lib/languages/xml';
import css from 'highlight.js/lib/languages/css';
import markdownLang from 'highlight.js/lib/languages/markdown';
import yaml from 'highlight.js/lib/languages/yaml';

hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('js', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('ts', typescript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('py', python);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('sh', bash);
hljs.registerLanguage('shell', bash);
hljs.registerLanguage('json', json);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('html', xml);
hljs.registerLanguage('css', css);
hljs.registerLanguage('markdown', markdownLang);
hljs.registerLanguage('md', markdownLang);
hljs.registerLanguage('yaml', yaml);
hljs.registerLanguage('yml', yaml);

// Minimal marked setup; can be extended (GFM, breaks)
marked.setOptions({ gfm: true, breaks: true, langPrefix: 'language-' });

// Use a custom renderer so we can always include `hljs` class and avoid prose overrides.
const renderer: any = new (marked as any).Renderer();
renderer.code = (codeAny: any, infostring: any) => {
  // Normalize inputs: some environments may pass a token object instead of a string
  let code: string;
  let lang = (typeof infostring === 'string' ? infostring : '')?.match(/\S+/)?.[0];
  if (typeof codeAny === 'string') {
    code = codeAny;
  } else if (codeAny && typeof codeAny.text === 'string') {
    code = codeAny.text;
    if (!lang && typeof codeAny.lang === 'string') lang = codeAny.lang;
  } else if (codeAny && typeof codeAny.raw === 'string') {
    // Strip fences from raw
    const raw: string = codeAny.raw;
    code = raw.replace(/^```[^\n]*\n?/, '').replace(/\n?```\s*$/, '');
    if (!lang && typeof codeAny.lang === 'string') lang = codeAny.lang;
  } else {
    code = String(codeAny ?? '');
  }
  let highlighted: string;
  try {
    if (lang && hljs.getLanguage(lang)) {
      highlighted = hljs.highlight(code, { language: lang }).value;
    } else {
      highlighted = hljs.highlightAuto(code).value;
    }
  } catch {
    highlighted = code;
  }
  const cls = ['hljs'];
  if (lang) cls.push(`language-${lang}`);
  const out = typeof highlighted === 'string' ? highlighted : String(highlighted);
  return `<div class="not-prose"><pre><code class="${cls.join(' ')}">${out}</code></pre></div>`;
};
(marked as any).use({ renderer });

const purifier: any = typeof window !== 'undefined' ? createDOMPurify(window as any) : null;

export function renderMarkdown(md: string | undefined | null): string {
  // Support both marked() and marked.parse() across versions
  const parse: any = (marked as any).parse ? (marked as any).parse : (marked as any);
  const rawAny = parse(md ?? '');
  // Ensure we have a plain string (avoid TrustedHTML or objects)
  const raw = typeof rawAny === 'string' ? rawAny : String(rawAny);
  if (purifier) {
    const sanitized: any = purifier.sanitize(raw, { RETURN_TRUSTED_TYPE: false });
    return typeof sanitized === 'string' ? sanitized : String(sanitized);
  }
  return raw;
}
