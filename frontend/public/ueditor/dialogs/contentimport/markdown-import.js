/**
 * markdown-import.js — UEditor“导入内容”对话框使用的 Markdown → HTML 转换器。
 *
 * 从 contentimport.html 内联脚本中抽出为独立文件，便于单元测试
 * （src/components/editor/markdownImport.spec.js 直接引入本文件）。
 */
(function (root, factory) {
  if (typeof exports === 'object' && typeof module !== 'undefined') {
    module.exports = factory();
  } else {
    var api = factory();
    // 对话框内联脚本以全局函数方式调用
    root.convertMarkdownToHtml = api.convertMarkdownToHtml;
    root.MarkdownImport = api;
  }
})(typeof window !== 'undefined' ? window : globalThis, function () {
  'use strict';

  /**
   * 把 Markdown 文本转换为 HTML。
   * @param {string} markdown - Markdown 源文本
   * @returns {string} HTML 字符串
   */
  function convertMarkdownToHtml(markdown) {
    var html = markdown;

    // 保存代码块
    var codeBlocks = [];
    var codeIndex = 0;
    html = html.replace(/```([\w]*)\n([\s\S]*?)```/g, function (match, lang, code) {
      var placeholder = '___CODEBLOCK_' + (codeIndex++) + '___';
      codeBlocks.push({
        lang: lang || 'plaintext',
        code: code.trim()
      });
      return placeholder;
    });

    // 保存行内代码
    var inlineCodes = [];
    var inlineIndex = 0;
    html = html.replace(/`([^`]+)`/g, function (match, code) {
      var placeholder = '___INLINE_' + (inlineIndex++) + '___';
      inlineCodes.push(code);
      return placeholder;
    });

    // 保存数学公式（代码提取之后、其它语法之前，防止斜体/删除线/段落
    // 等正则破坏公式内部字符，如 $c^*$ 的星号被误转成 <em>）
    var mathBlocks = [];
    var mathIndex = 0;
    /**
     * 把公式暂存为占位符，稍后以规范化定界符还原。
     * 豆包会把公式内部的数学 token 也加裹成 \(...\)（如 \sqrt{\(V(t)\)}），
     * 而 \( 在 LaTeX 数学模式中非法。这里的括号属于定界符本身
     * （与外层 $\(...\)$ → $...$ 的解包语义一致），故循环剥掉全部
     * 内层定界符（循环以处理嵌套加裹）。
     * @param {string} formula - 公式内容（不含定界符）
     * @param {string} open - 规范化起始定界符（"$" 或 "$$"）
     * @param {string} close - 规范化结束定界符
     * @returns {string} 占位符
     */
    function stashMath(formula, open, close) {
      var normalized = formula;
      var prev;
      do {
        prev = normalized;
        normalized = normalized.replace(/\\\(([\s\S]*?)\\\)/g, '$1');
      } while (normalized !== prev);
      var placeholder = '___MATH_' + (mathIndex++) + '___';
      mathBlocks.push({ formula: normalized, open: open, close: close });
      return placeholder;
    }

    /**
     * 豆包复制伪影清理。
     *
     * 豆包的"复制"按钮存在已知缺陷：会把同一段公式碎片拼接进文中
     * 每一个连字符的位置（如"波动率\(碎片)相关性"原本是"波动率-相关性"，
     * "Module4\(碎片)Lesson4"原本是"Module4-Lesson4"）。碎片有两种形态：
     *   1. 病态嵌套：\(...\) 内部又含未配对的 \(（不可能是合法公式）；
     *   2. 合法公式本身（如 n(n-1)/2），但被逐字重复拼接在各处。
     *
     * 定罪证据（满足其一且逐字重复 ≥3 次）：
     *   a. 病态嵌套；
     *   b. 至少一处两侧紧贴字母数字（正规行内公式两侧通常是空白、
     *      中文或标点，不会嵌在 Module4...Lesson4 这类拉丁复合词内部）。
     *
     * 豁免：任一出现紧邻 $ 的片段（处于 $...$ 公式定界边缘，属于公式
     * 本体），及其包含的子片段；豁免沿包含链传播到不动点。
     * 定罪后，该碎片的全部出现（含中文夹心、公式内部）一并还原为连字符。
     * @param {string} text - 原始文本
     * @returns {string} 清理后的文本
     */
    function collapseDoubaoArtifacts(text) {
      // 配平扫描所有 \(...\) 片段（嵌套的按最外层配平收集）
      var spanInfo = {};
      var i = 0;
      while (i < text.length) {
        var open = text.indexOf('\\(', i);
        if (open === -1) break;
        // 跳过 \\(（转义括号，即前一个字符也是反斜杠）
        if (open > 0 && text.charAt(open - 1) === '\\') {
          i = open + 2;
          continue;
        }
        var depth = 1;
        var nested = false;
        var end = -1;
        var j = open + 2;
        while (j < text.length) {
          var ch = text.charAt(j);
          if (ch === '\\' && text.charAt(j + 1) === '(' && text.charAt(j - 1) !== '\\') {
            depth++;
            nested = true;
            j += 2;
            continue;
          }
          if (ch === '\\' && text.charAt(j + 1) === ')' && text.charAt(j - 1) !== '\\') {
            depth--;
            j += 2;
            if (depth === 0) {
              end = j;
              break;
            }
            continue;
          }
          j++;
        }
        if (end !== -1) {
          var s = text.substring(open, end);
          if (!spanInfo[s]) spanInfo[s] = { count: 0, nested: nested, sandwich: false };
          spanInfo[s].count++;
          spanInfo[s].nested = spanInfo[s].nested || nested;
        }
        i = open + 2;
      }

      var spanList = Object.keys(spanInfo);

      // 字母数字夹心证据：某处出现两侧均紧贴字母数字
      function isAlnum(c) {
        return /[A-Za-z0-9]/.test(c);
      }
      spanList.forEach(function (s) {
        var idx = text.indexOf(s);
        while (idx !== -1) {
          if (isAlnum(text.charAt(idx - 1)) && isAlnum(text.charAt(idx + s.length))) {
            spanInfo[s].sandwich = true;
            break;
          }
          idx = text.indexOf(s, idx + 1);
        }
      });

      // 豁免集：任一出现紧邻 $ 的片段，及其包含的子片段
      var excluded = {};
      spanList.forEach(function (s) {
        var idx = text.indexOf(s);
        while (idx !== -1) {
          if (text.charAt(idx - 1) === '$' || text.charAt(idx + s.length) === '$') {
            excluded[s] = true;
            break;
          }
          idx = text.indexOf(s, idx + 1);
        }
      });
      var changed = true;
      var guard = 0;
      while (changed && guard < 10) {
        changed = false;
        guard++;
        spanList.forEach(function (s) {
          if (excluded[s]) return;
          for (var t in excluded) {
            if (t !== s && t.indexOf(s) !== -1) {
              excluded[s] = true;
              changed = true;
              break;
            }
          }
        });
      }

      // 定罪：重复 ≥3 次、未豁免、且（病态嵌套 或 有字母数字夹心证据）
      spanList.forEach(function (s) {
        var info = spanInfo[s];
        if (!excluded[s] && info.count >= 3 && (info.nested || info.sandwich)) {
          text = text.split(s).join('-');
        }
      });
      return text;
    }

    html = collapseDoubaoArtifacts(html);

    // 豆包双重定界符 $\(...\)$ 解包为单层 \(...\)。
    // 内容限定为单行且不含 $：若允许跨行，懒惰匹配会越过本行
    // 吞并到若干段落之后的 \)$，毁掉中间的所有内容
    html = html.replace(/\$\\\(([^$\n]+?)\\\)\$/g, '\\($1\\)');

    // 块级 $$...$$（可跨多行）
    html = html.replace(/\$\$([\s\S]+?)\$\$/g, function (match, formula) {
      return stashMath(formula, '$$', '$$');
    });

    // 块级 \[...\]（ChatGPT 风格，可跨多行）→ 归一为 $$...$$
    html = html.replace(/\\\[([\s\S]+?)\\\]/g, function (match, formula) {
      return stashMath(formula, '$$', '$$');
    });

    // 行内 $...$：不跨行；起始 $ 后与结束 $ 前都不能是空白
    // （与 MathJax 的 $ 定界符规则一致，避免 "$100 和 $200" 被误判为公式）
    html = html.replace(/\$(\S(?:[^$\n]*\S)?)\$/g, function (match, formula) {
      return stashMath(formula, '$', '$');
    });

    // 行内 \(...\)（ChatGPT 风格）→ 归一为 $...$
    html = html.replace(/\\\(([\s\S]+?)\\\)/g, function (match, formula) {
      return stashMath(formula, '$', '$');
    });

    // 转换标题（支持 1~6 级）
    html = html.replace(/^###### (.*?)$/gm, '<h6>$1</h6>');
    html = html.replace(/^##### (.*?)$/gm, '<h5>$1</h5>');
    html = html.replace(/^#### (.*?)$/gm, '<h4>$1</h4>');
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');

    // 转换粗体和斜体
    html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
    html = html.replace(/~~(.*?)~~/g, '<del>$1</del>');

    // 转换列表
    html = html.replace(/^\* (.*?)$/gm, '<li>$1</li>');
    html = html.replace(/^- (.*?)$/gm, '<li>$1</li>');
    html = html.replace(/^\d+\. (.*?)$/gm, '<li>$1</li>');

    // 包装列表
    html = html.replace(/(<li>.*?<\/li>\n?)+/g, function (match) {
      return '<ul>' + match + '</ul>';
    });

    // 转换表格（Markdown 表格语法）
    // 识别连续的以 | 开头并包含 | 的行，其中第二行为分隔行
    html = html.replace(/((?:^\|.*\|\s*\n)+)/gm, function (match) {
      var lines = match.trim().split('\n');
      if (lines.length < 2) return match;

      var headerLine = lines[0].trim();
      var separatorLine = lines[1].trim();

      // 判断第二行是否是形如 |---|---| 的分隔行
      var sepNoSpace = separatorLine.replace(/\s/g, '');
      if (!/^\|[-:]+(?:\|[-:]+)*\|$/.test(sepNoSpace)) {
        return match;
      }

      function splitRow(row) {
        var cells = row.trim();
        if (cells[0] === '|') cells = cells.substring(1);
        if (cells[cells.length - 1] === '|') cells = cells.slice(0, -1);
        return cells.split('|').map(function (cell) { return cell.trim(); });
      }

      var headerCells = splitRow(headerLine);
      var bodyLines = lines.slice(2);
      var bodyRows = bodyLines
        .map(function (line) { return line.trim(); })
        .filter(function (line) { return line.length > 0; })
        .map(splitRow);

      var tableHtml = '<table><thead><tr>' +
        headerCells.map(function (text) { return '<th>' + text + '</th>'; }).join('') +
        '</tr></thead>';

      if (bodyRows.length > 0) {
        tableHtml += '<tbody>';
        bodyRows.forEach(function (cells) {
          tableHtml += '<tr>' +
            cells.map(function (text) { return '<td>' + text + '</td>'; }).join('') +
            '</tr>';
        });
        tableHtml += '</tbody>';
      }

      tableHtml += '</table>';
      return tableHtml + '\n';
    });

    // 转换链接和图片
    html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%;" />');
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');

    // 转换引用
    html = html.replace(/^> (.*?)$/gm, '<blockquote style="border-left:4px solid #ddd; margin:0; padding-left:16px; color:#666;">$1</blockquote>');

    // 转换水平线
    html = html.replace(/^---$/gm, '<hr style="border:none; border-top:1px solid #ccc; margin:20px 0;">');
    html = html.replace(/^\*\*\*$/gm, '<hr style="border:none; border-top:1px solid #ccc; margin:20px 0;">');

    // 处理 Markdown 行内换行：两个空格 + 换行 -> <br>
    // 例如："- 定义：...␣␣\n- 目标：..." 会在同一条目中换行显示
    html = html.replace(/ {2}\n/g, '<br>\n');

    // 转换段落
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';

    // 清理多余的标签（标题、列表、引用、分割线、表格不被 <p> 包裹）
    html = html.replace(/<p><\/p>/g, '');
    html = html.replace(/<p>(<h[1-6]>)/g, '$1');
    html = html.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
    html = html.replace(/<p>(<ul>)/g, '$1');
    html = html.replace(/(<\/ul>)<\/p>/g, '$1');
    html = html.replace(/<p>(<blockquote)/g, '$1');
    html = html.replace(/(<\/blockquote>)<\/p>/g, '$1');
    html = html.replace(/<p>(<hr)/g, '$1');
    html = html.replace(/(<hr[^>]*>)<\/p>/g, '$1');
    html = html.replace(/<p>(<table>)/g, '$1');
    html = html.replace(/(<\/table>)<\/p>/g, '$1');

    /**
     * HTML 转义公式内容：防止公式中的 < > & 被浏览器当作标签/实体解析
     * （MathJax 读取 DOM 文本时会解码回原字符，不影响渲染）。
     * @param {string} text - 公式原文
     * @returns {string} 转义后的文本
     */
    function escapeMath(text) {
      return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }

    // 还原数学公式。
    // 必须用函数形式的 replace：字符串替换中 $$、$& 等具有特殊含义，
    // 公式里必然出现 $，字符串形式会把 $$ 块错误折叠成单 $。
    mathBlocks.forEach(function (block, index) {
      var placeholder = '___MATH_' + index + '___';
      html = html.replace(placeholder, function () {
        return block.open + escapeMath(block.formula) + block.close;
      });
    });

    // 还原代码块（同样使用函数形式，防止代码中的 $ 序列被替换语义改写）
    codeBlocks.forEach(function (block, index) {
      var placeholder = '___CODEBLOCK_' + index + '___';
      var codeHtml = '<pre style="background:#f5f5f5; padding:10px; border-radius:3px; overflow-x:auto;"><code class="language-' + block.lang + '">' +
        block.code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') +
        '</code></pre>';
      html = html.replace(placeholder, function () { return codeHtml; });
    });

    // 还原行内代码
    inlineCodes.forEach(function (code, index) {
      var placeholder = '___INLINE_' + index + '___';
      var codeHtml = '<code style="background:#f5f5f5; padding:2px 4px; border-radius:3px; font-family:monospace;">' +
        code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') +
        '</code>';
      html = html.replace(placeholder, function () { return codeHtml; });
    });

    return html;
  }

  return {
    convertMarkdownToHtml: convertMarkdownToHtml
  };
});
