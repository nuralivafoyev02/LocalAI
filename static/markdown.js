/* LocalAI — xavfsiz Markdown renderer va yengil kod highlighter (tashqi kutubxonalarsiz). */
(function (global) {
  "use strict";

  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = (text) => String(text).replace(/[&<>"']/g, (ch) => ESC[ch]);
  const escRe = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  /* ------------------------------------------------------------ highlighter */

  const words = (text) => new Set(text.split(/\s+/).filter(Boolean));
  const C_STRINGS = [`"(?:\\\\.|[^"\\\\\\n])*"?`, `'(?:\\\\.|[^'\\\\\\n])*'?`];
  const LIT = "true false null undefined NaN Infinity nil None True False this self super";

  const SPECS = {
    js: {
      line: ["//"], block: [["/*", "*/"]],
      strings: [...C_STRINGS, "`(?:\\\\.|[^`\\\\])*`?"],
      kw: words(`async await break case catch class const continue debugger default delete do else export extends
        finally for from function get if implements import in instanceof interface let new of private protected
        public readonly return set static switch throw try type typeof var void while with yield enum declare
        namespace abstract as satisfies keyof`),
      lit: words(LIT),
    },
    py: {
      line: ["#"], block: [],
      strings: [`[rbfuRBFU]{0,2}"""[\\s\\S]*?(?:"""|$)`, `[rbfuRBFU]{0,2}'''[\\s\\S]*?(?:'''|$)`,
        `[rbfuRBFU]{0,2}"(?:\\\\.|[^"\\\\\\n])*"?`, `[rbfuRBFU]{0,2}'(?:\\\\.|[^'\\\\\\n])*'?`],
      kw: words(`and as assert async await break class continue def del elif else except finally for from global
        if import in is lambda nonlocal not or pass raise return try while with yield match case print`),
      lit: words(LIT),
      extra: [["@[\\w.]+", "f"]],
    },
    c: {
      line: ["//"], block: [["/*", "*/"]],
      strings: [...C_STRINGS, "`(?:\\\\.|[^`\\\\])*`?"],
      kw: words(`auto break case catch char class const constexpr continue default delete do double else enum
        explicit extern final float for friend func go goto if impl import include inline int interface let long
        loop match mod module mut namespace new operator override package private protected pub public register
        return short signed sizeof static struct super switch template throw throws trait try typedef typename
        union unsigned use using var virtual void volatile where while fn val fun when object data sealed open
        internal lateinit defer select chan map range type string bool byte rune async await extends implements
        final abstract synchronized native transient instanceof yield guard protocol extension`),
      lit: words(LIT),
      extra: [["#\\s*\\w+", "k"], ["@\\w+", "f"]],
    },
    php: {
      line: ["//", "#"], block: [["/*", "*/"]], strings: C_STRINGS,
      kw: words(`abstract and array as break case catch class clone const continue declare default do echo else
        elseif empty endforeach endif extends final finally fn for foreach function global if implements include
        instanceof interface isset list match namespace new or print private protected public require return
        static switch throw trait try unset use var while yield`),
      lit: words(LIT), extra: [["\\$\\w+", "l"]],
    },
    sql: {
      line: ["--"], block: [["/*", "*/"]], strings: C_STRINGS, ci: true,
      kw: words(`select from where and or not insert into values update set delete create table drop alter add
        primary key foreign references index view join inner left right outer full on as group by order having
        limit offset distinct union all case when then else end is null in between like exists count sum avg min
        max asc desc default unique constraint returning with recursive cascade truncate begin commit rollback
        integer int varchar text boolean date timestamp serial float decimal numeric`),
      lit: words("true false null"),
    },
    sh: {
      line: ["#"], block: [], strings: C_STRINGS,
      kw: words(`if then else elif fi for while until do done case esac function in return export local readonly
        source alias cd echo exit set unset shift break continue sudo apt pip npm git cat grep sed awk curl wget
        mkdir rm cp mv ls chmod chown python python3 node docker`),
      lit: words("true false"), extra: [["\\$\\{[^}]*\\}|\\$\\w+|\\$[@#?$!*0-9]", "l"], ["(?<=\\s)--?[\\w-]+", "p"]],
    },
    json: {
      line: [], block: [], strings: [`"(?:\\\\.|[^"\\\\\\n])*"?`], kw: new Set(), lit: words("true false null"),
    },
    yaml: {
      line: ["#"], block: [], strings: C_STRINGS, kw: new Set(),
      lit: words("true false null yes no on off ~"), extra: [["^[ \\t-]*[\\w.$-]+(?=\\s*:)", "p"]],
    },
    css: {
      line: [], block: [["/*", "*/"]], strings: C_STRINGS, kw: new Set(), lit: words("important inherit initial none auto"),
      extra: [["@[\\w-]+", "k"], ["#[0-9a-fA-F]{3,8}\\b", "n"], ["[\\w-]+(?=\\s*:[^:{;]*[;}]?)", "p"],
        ["-?\\d*\\.?\\d+(?:px|em|rem|%|vh|vw|s|ms|deg|fr)?\\b", "n"]],
    },
    html: { html: true },
  };

  const ALIASES = {
    javascript: "js", jsx: "js", mjs: "js", cjs: "js", ts: "js", typescript: "js", tsx: "js", node: "js",
    python: "py", py3: "py", ipython: "py", rb: "py", ruby: "py",
    java: "c", cpp: "c", "c++": "c", cc: "c", h: "c", hpp: "c", cs: "c", csharp: "c", go: "c", golang: "c",
    rust: "c", rs: "c", kotlin: "c", kt: "c", swift: "c", dart: "c", scala: "c", groovy: "c", objc: "c",
    bash: "sh", shell: "sh", zsh: "sh", console: "sh", terminal: "sh", powershell: "sh", ps1: "sh", cmd: "sh",
    bat: "sh", dockerfile: "sh", docker: "sh", makefile: "sh", make: "sh", ini: "yaml", toml: "yaml", env: "sh",
    yml: "yaml", jsonc: "json", json5: "json", scss: "css", less: "css", sass: "css",
    xml: "html", svg: "html", vue: "html", svelte: "html", htm: "html", markup: "html",
    postgres: "sql", postgresql: "sql", mysql: "sql", sqlite: "sql", plsql: "sql",
  };

  const compiled = {};
  function specFor(lang) {
    const key = (lang || "").toLowerCase();
    const name = SPECS[key] ? key : ALIASES[key];
    if (!name) return null;
    if (compiled[name]) return compiled[name];
    const spec = SPECS[name];
    spec.name = name;
    if (spec.html) {
      spec.re = /(<!--[\s\S]*?(?:-->|$))|("[^"]*"?|'[^']*'?)|(<\/?[\w:.-]+|\/?>)|([\w:.-]+(?==))/g;
      return (compiled[name] = spec);
    }
    const comments = [
      ...spec.line.map((token) => `${escRe(token)}.*`),
      ...spec.block.map(([open, close]) => `${escRe(open)}[\\s\\S]*?(?:${escRe(close)}|$)`),
    ];
    const extras = spec.extra || [];
    const groups = [
      comments.length ? comments.join("|") : "(?!)",
      spec.strings.join("|"),
      ...extras.map(([source]) => source),
      "\\b(?:0[xX][\\da-fA-F]+|\\d[\\d_]*(?:\\.\\d+)?(?:[eE][+-]?\\d+)?)\\b",
      "[A-Za-z_$][\\w$]*",
    ];
    spec.re = new RegExp(groups.map((source) => `(${source})`).join("|"), "gm");
    spec.extraClasses = extras.map(([, cls]) => cls);
    return (compiled[name] = spec);
  }

  function highlight(code, lang) {
    const spec = specFor(lang);
    if (!spec || code.length > 120000) return esc(code);
    const re = spec.re;
    re.lastIndex = 0;
    let out = "";
    let last = 0;
    let match;
    while ((match = re.exec(code))) {
      const token = match[0];
      if (!token) { re.lastIndex++; continue; }
      if (match.index > last) out += esc(code.slice(last, match.index));
      let cls = null;
      if (spec.html) {
        cls = match[1] ? "c" : match[2] ? "s" : match[3] ? "k" : match[4] ? "p" : null;
      } else if (match[1] !== undefined) {
        cls = "c";
      } else if (match[2] !== undefined) {
        const isKey = /^\s*:/.test(code.slice(re.lastIndex, re.lastIndex + 8));
        cls = isKey && (spec.name === "json" || spec.name === "js" || spec.name === "py") ? "p" : "s";
      } else {
        const extraCount = spec.extraClasses.length;
        let index = 3;
        for (let e = 0; e < extraCount; e++, index++) {
          if (match[index] !== undefined) { cls = spec.extraClasses[e]; break; }
        }
        if (!cls) {
          if (match[index] !== undefined) cls = "n";
          else if (match[index + 1] !== undefined) {
            const word = spec.ci ? token.toLowerCase() : token;
            if (spec.kw.has(word)) cls = "k";
            else if (spec.lit.has(word)) cls = "l";
            else if (code[re.lastIndex] === "(") cls = "f";
            else if (/^[A-Z][a-z0-9]+[A-Za-z0-9]*$/.test(token) && !spec.ci) cls = "t";
          }
        }
      }
      out += cls ? `<span class="tk-${cls}">${esc(token)}</span>` : esc(token);
      last = re.lastIndex;
    }
    return out + esc(code.slice(last));
  }

  /* ---------------------------------------------------------------- inline */

  function safeUrl(url) {
    const value = url.trim().replace(/^<|>$/g, "");
    return /^(https?:\/\/|mailto:)/i.test(value) ? value : null;
  }

  function emphasis(html) {
    return html
      .replace(/\*\*(?=\S)([\s\S]*?\S)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^\w])__(?=\S)([\s\S]*?\S)__(?!\w)/g, "$1<strong>$2</strong>")
      .replace(/(^|[^*\w])\*(?=[^\s*])([^*\n]*?[^\s*])\*(?!\*)/g, "$1<em>$2</em>")
      .replace(/(^|[^\w])_(?=[^\s_])([^_\n]*?[^\s_])_(?!\w)/g, "$1<em>$2</em>")
      .replace(/~~(?=\S)([\s\S]*?\S)~~/g, "<del>$1</del>");
  }

  function inline(text) {
    const stash = [];
    const keep = (html) => `\u0000${stash.push(html) - 1}\u0000`;
    let src = text.replace(/\u0000/g, "");
    src = src.replace(/(`+)(?!`)([\s\S]*?[^`])\1(?!`)/g, (_, ticks, code) =>
      keep(`<code>${esc(code.replace(/^ (.+) $/, "$1"))}</code>`));
    src = src.replace(/!?\[([^\]\n]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g, (whole, label, url) => {
      const href = safeUrl(url);
      if (!href) return keep(esc(label));
      return keep(`<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${emphasis(esc(label))}</a>`);
    });
    src = src.replace(/\bhttps?:\/\/[^\s<>"'`)\]]+[^\s<>"'`)\].,;:!?]/g, (url) =>
      keep(`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(url)}</a>`));
    let html = emphasis(esc(src));
    for (let guard = 0; guard < 5 && html.includes("\u0000"); guard++) {
      html = html.replace(/\u0000(\d+)\u0000/g, (_, index) => stash[Number(index)] ?? "");
    }
    return html;
  }

  /* ---------------------------------------------------------------- blocks */

  const COPY_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
  const FENCE = /^(\s{0,3})(`{3,}|~{3,})\s*([^\s`]*)[^`]*$/;
  const HEADING = /^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$/;
  const HR = /^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/;
  const QUOTE = /^\s{0,3}>/;
  const ITEM = /^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$/;
  const TABLE_SEP = /^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$/;
  const blank = (line) => /^\s*$/.test(line || "");

  function codeBlock(code, lang, open) {
    const label = lang ? esc(lang) : "kod";
    return `<div class="code-block${open ? " is-open" : ""}"><div class="code-head"><span>${label}</span>` +
      `<button class="copy-code" type="button" aria-label="Kodni nusxalash">${COPY_ICON}<span>Nusxa</span></button></div>` +
      `<pre><code>${highlight(code, lang)}</code></pre></div>`;
  }

  function isTableStart(line, next) {
    return line.includes("|") && next !== undefined && next.includes("|") && TABLE_SEP.test(next) && next.includes("-");
  }

  function splitRow(line) {
    let row = line.trim();
    if (row.startsWith("|")) row = row.slice(1);
    if (row.endsWith("|") && !row.endsWith("\\|")) row = row.slice(0, -1);
    return row.split(/(?<!\\)\|/).map((cell) => cell.trim().replace(/\\\|/g, "|"));
  }

  function table(lines, start) {
    const header = splitRow(lines[start]);
    const aligns = splitRow(lines[start + 1]).map((cell) =>
      /^:-+:$/.test(cell) ? "center" : /-+:$/.test(cell) ? "right" : /^:-+/.test(cell) ? "left" : "");
    let i = start + 2;
    const rows = [];
    while (i < lines.length && lines[i].includes("|") && !blank(lines[i])) {
      rows.push(splitRow(lines[i]));
      i++;
    }
    const cell = (tag, text, index) => {
      const align = aligns[index] ? ` style="text-align:${aligns[index]}"` : "";
      return `<${tag}${align}>${inline(text || "")}</${tag}>`;
    };
    const head = `<tr>${header.map((text, index) => cell("th", text, index)).join("")}</tr>`;
    const body = rows.map((row) => `<tr>${header.map((_, index) => cell("td", row[index], index)).join("")}</tr>`).join("");
    return [`<div class="table-wrap"><table><thead>${head}</thead><tbody>${body}</tbody></table></div>`, i];
  }

  function isBlockStart(line, next, inParagraph) {
    if (FENCE.test(line) || HEADING.test(line) || HR.test(line) || QUOTE.test(line)) return true;
    if (isTableStart(line, next)) return true;
    const item = line.match(ITEM);
    if (item) {
      if (!inParagraph) return true;
      return !/\d/.test(item[2]) || parseInt(item[2], 10) === 1;
    }
    return false;
  }

  function list(lines, start) {
    const first = lines[start].match(ITEM);
    const base = first[1].length;
    const ordered = /\d/.test(first[2]);
    const items = [];
    let loose = false;
    let i = start;
    while (i < lines.length) {
      const line = lines[i];
      const match = line.match(ITEM);
      if (match && Math.abs(match[1].length - base) <= 1 && /\d/.test(match[2]) === ordered) {
        items.push({ lines: [match[3]], offset: match[1].length + match[2].length + 1 });
        i++;
        continue;
      }
      if (match && match[1].length < base) break;
      if (blank(line)) {
        let j = i + 1;
        while (j < lines.length && blank(lines[j])) j++;
        if (j >= lines.length || !items.length) break;
        const nextItem = lines[j].match(ITEM);
        const indent = lines[j].match(/^\s*/)[0].length;
        const sibling = nextItem && Math.abs(nextItem[1].length - base) <= 1 && /\d/.test(nextItem[2]) === ordered;
        if (sibling || indent > base + 1) {
          loose = loose || sibling;
          items[items.length - 1].lines.push("");
          i = j;
          continue;
        }
        break;
      }
      const indent = line.match(/^\s*/)[0].length;
      const current = items[items.length - 1];
      if (indent > base && current) {
        current.lines.push(line.slice(Math.min(indent, current.offset)));
        i++;
        continue;
      }
      if (current && !isBlockStart(line, lines[i + 1], true)) {
        current.lines.push(line.trim());
        i++;
        continue;
      }
      break;
    }
    const tag = ordered ? "ol" : "ul";
    const startAttr = ordered && parseInt(first[2], 10) !== 1 ? ` start="${parseInt(first[2], 10)}"` : "";
    const html = items.map((item) => {
      let content = item.lines.join("\n");
      let task = "";
      const check = content.match(/^\[([ xX])\]\s+/);
      if (check) {
        task = `<span class="task${check[1] === " " ? "" : " done"}" aria-hidden="true"></span>`;
        content = content.slice(check[0].length);
      }
      let body = render(content);
      if (!loose) body = body.replace(/^<p>([\s\S]*?)<\/p>/, "$1");
      return `<li${task ? ' class="task-item"' : ""}>${task}${body}</li>`;
    }).join("");
    return [`<${tag}${startAttr}>${html}</${tag}>`, i];
  }

  function render(source) {
    const lines = String(source || "").replace(/\r\n?/g, "\n").split("\n");
    const out = [];
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      let match = line.match(FENCE);
      if (match) {
        const fence = match[2];
        const indent = match[1].length;
        const body = [];
        let closed = false;
        i++;
        while (i < lines.length) {
          const current = lines[i];
          const close = current.match(/^\s{0,3}(`{3,}|~{3,})\s*$/);
          if (close && close[1][0] === fence[0] && close[1].length >= fence.length) {
            closed = true;
            i++;
            break;
          }
          body.push(indent ? current.replace(new RegExp(`^ {0,${indent}}`), "") : current);
          i++;
        }
        out.push(codeBlock(body.join("\n"), match[3], !closed));
        continue;
      }
      if (blank(line)) { i++; continue; }
      if ((match = line.match(HEADING))) {
        const level = match[1].length;
        out.push(`<h${level}>${inline(match[2])}</h${level}>`);
        i++;
        continue;
      }
      if (HR.test(line)) { out.push("<hr>"); i++; continue; }
      if (QUOTE.test(line)) {
        const body = [];
        while (i < lines.length && (QUOTE.test(lines[i]) || (!blank(lines[i]) && body.length && !isBlockStart(lines[i], lines[i + 1], true)))) {
          body.push(lines[i].replace(/^\s{0,3}>\s?/, ""));
          i++;
        }
        out.push(`<blockquote>${render(body.join("\n"))}</blockquote>`);
        continue;
      }
      if (isTableStart(line, lines[i + 1])) {
        const [html, next] = table(lines, i);
        out.push(html);
        i = next;
        continue;
      }
      if (ITEM.test(line)) {
        const [html, next] = list(lines, i);
        out.push(html);
        i = next;
        continue;
      }
      const paragraph = [line];
      i++;
      while (i < lines.length && !blank(lines[i]) && !isBlockStart(lines[i], lines[i + 1], true)) {
        paragraph.push(lines[i]);
        i++;
      }
      out.push(`<p>${paragraph.map((text) => inline(text.trim())).join("<br>")}</p>`);
    }
    return out.join("");
  }

  global.LocalMarkdown = { render, inline, highlight, escape: esc };
  if (typeof module !== "undefined") module.exports = global.LocalMarkdown;
})(typeof window !== "undefined" ? window : globalThis);
