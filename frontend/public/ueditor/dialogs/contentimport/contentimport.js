var contentImport = {};
var g = $G;

contentImport.data = {
    result: null,
};
contentImport.init = function (opt, callbacks) {
    addUploadButtonListener();
    addOkListener();
};

function processWord(file) {
    $('.file-tip').html('正在转换Word文件，请稍后...');
    $('.file-result').html('').hide();
    var reader = new FileReader();
    reader.onload = function (loadEvent) {
        mammoth.convertToHtml({
            arrayBuffer: loadEvent.target.result
        })
            .then(function displayResult(result) {
                $('.file-tip').html('转换成功');
                contentImport.data.result = result.value;
                $('.file-result').html(result.value).show();
            }, function (error) {
                $('.file-tip').html('Word文件转换失败:' + error);
            });
    };
    reader.onerror = function (loadEvent) {
        $('.file-tip').html('Word文件转换失败:' + loadEvent);
    };
    reader.readAsArrayBuffer(file);
}

// 修复元宝表格格式
function fixYuanbaoTable(text) {
    var result = text;
    
    // 1. 首先处理表格行被压缩成一行的情况
    // 元宝格式: | 维度 | 分类树 | 回归树 |   |---|---|---|   | 任务目标 | xxx | yyy |
    // 需要在两个或更多空格处分行
    result = result.replace(/\|\s{2,}\|/g, '|\n|');
    
    // 2. 检测并修复分隔符行 |---|---|---|
    // 分隔符行前后应该有换行
    result = result.replace(/(\|[^|\n-]+\|[^|\n-]*\|[^\n]*)(\|[-:]+\|(?:[-:]+\|)+)/g, '$1\n$2');
    result = result.replace(/(\|[-:]+\|(?:[-:]+\|)+)(\|[^|\n-]+)/g, '$1\n$2');
    
    // 3. 处理多列表格行被合并的情况
    // 检测 | xxx | yyy | zzz |  后面跟着空格和另一个表格行
    result = result.replace(/(\|(?:[^|\n]+\|){2,})\s{2,}(\|(?:[^|\n]+\|){2,})/g, '$1\n$2');
    
    // 4. 确保表格分隔符行独立
    result = result.replace(/([^\n|])(\|[-:]+[-:|\s]+\|)/g, '$1\n$2');
    result = result.replace(/(\|[-:]+[-:|\s]+\|)([^\n|])/g, '$1\n$2');
    
    // 5. 智能分行：检测完整的表格行模式
    // 一个表格行通常是 | cell1 | cell2 | cell3 | 格式
    // 计算每行应有的列数，然后分行
    var lines = result.split('\n');
    var processedLines = [];
    
    for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        
        // 检查是否是被压缩的表格行
        if (line.indexOf('|') !== -1 && (line.match(/\|/g) || []).length > 6) {
            // 可能是多行被压缩，尝试分割
            // 检测分隔符模式 |---|
            var separatorMatch = line.match(/\|[-:]+\|(?:[-:]+\|)+/);
            if (separatorMatch) {
                var separator = separatorMatch[0];
                var parts = line.split(separator);
                if (parts.length >= 2) {
                    // 头部 + 分隔符 + 数据行们
                    var headerPart = parts[0].trim();
                    var dataParts = parts.slice(1).join(separator).trim();
                    
                    if (headerPart) processedLines.push(headerPart);
                    processedLines.push(separator);
                    
                    // 分割数据行
                    if (dataParts) {
                        // 数据行用多空格分隔
                        var dataRows = dataParts.split(/\s{2,}/).filter(function(r) { return r.trim(); });
                        dataRows.forEach(function(row) {
                            if (row.trim()) processedLines.push(row.trim());
                        });
                    }
                    continue;
                }
            }
            
            // 尝试按多空格分割
            var subLines = line.split(/\s{2,}/).filter(function(s) { return s.indexOf('|') !== -1; });
            if (subLines.length > 1) {
                subLines.forEach(function(sl) {
                    if (sl.trim()) processedLines.push(sl.trim());
                });
                continue;
            }
        }
        
        processedLines.push(line);
    }
    
    result = processedLines.join('\n');
    
    // 6. 清理表格中多余的空行
    result = result.replace(/\|\n\n+\|/g, '|\n|');
    
    // 7. 确保表格前后有空行（Markdown表格需要）
    result = result.replace(/([^\n])\n(\|[^|]+\|)/g, '$1\n\n$2');
    result = result.replace(/(\|[^|]+\|)\n([^\n|])/g, '$1\n\n$2');
    
    return result;
}

// 预处理元宝格式的Markdown
function preprocessYuanbaoMarkdown(markdown) {
    var result = markdown;
    
    // 0. 首先处理换行符统一
    result = result.replace(/\r\n/g, '\n');
    result = result.replace(/\r/g, '\n');
    
    // 1. 移除零宽空格和其他不可见字符
    result = result.replace(/[\u200B-\u200D\uFEFF]/g, '');
    
    // 1b. 修复元宝标题格式 - 标题后可能有多余的空格或特殊字符
    // 处理标题：确保 # 号数量正确，去除末尾特殊字符
    result = result.replace(/^(#{1,6})\s*(.*?)\s*$/gm, function(match, hashes, title) {
        // 去除标题文本中的特殊字符
        title = title.replace(/[​\u200B-\u200D\uFEFF]/g, '').trim();
        return hashes + ' ' + title;
    });
    
    // 1c. 处理元宝特有的表格格式（在同一行内的表格）
    // 检测表格模式：| xxx |   | yyy |   | zzz |
    // 元宝会把表格行压缩成一行，用多个空格分隔
    result = result.replace(/(\|[^|\n]+\|)\s{2,}(\|[-:]+\|)/g, '$1\n$2');
    result = result.replace(/(\|[-:]+\|)\s{2,}(\|[^|\n]+\|)/g, '$1\n$2');
    result = result.replace(/(\|[^|\n]+\|)\s{2,}(\|[^|\n]+\|)/g, '$1\n$2');
    
    // 2. 处理元宝特殊的列表标记 "- ••" -> "-"
    result = result.replace(/^(\s*)-\s*•+\s*/gm, '$1- ');
    
    // 3. 处理元宝特殊的编号列表 "1. 1.1.内容" -> "1. 内容"
    result = result.replace(/^(\s*)(\d+)\.\s*\d+\.\d+\.\s*/gm, '$1$2. ');
    
    // 4. 处理元宝代码块中错误渲染的公式格式
    // 例如：Gini(D)=1−k=1∑K​pk2​ 这种格式的公式在代码块中
    // 将代码块中的公式保留为代码格式
    
    // 5. 处理元宝公式格式 - 检测并修复被错误渲染的LaTeX公式
    // 修复常见的数学符号（元宝会把LaTeX渲染成Unicode数学符号）
    var mathSymbolMap = {
        '∑': '\\sum',
        '∏': '\\prod',
        '∫': '\\int',
        '√': '\\sqrt',
        '∞': '\\infty',
        '≈': '\\approx',
        '≠': '\\neq',
        '≤': '\\leq',
        '≥': '\\geq',
        '×': '\\times',
        '÷': '\\div',
        '±': '\\pm',
        '−': '-',
        '·': '\\cdot',
        '…': '\\cdots',
        'α': '\\alpha',
        'β': '\\beta',
        'γ': '\\gamma',
        'δ': '\\delta',
        'ε': '\\epsilon',
        'θ': '\\theta',
        'λ': '\\lambda',
        'μ': '\\mu',
        'σ': '\\sigma',
        'π': '\\pi',
        'ω': '\\omega',
        '∂': '\\partial',
        '∇': '\\nabla',
        '∈': '\\in',
        '∉': '\\notin',
        '⊂': '\\subset',
        '⊃': '\\supset',
        '∪': '\\cup',
        '∩': '\\cap',
        '∧': '\\wedge',
        '∨': '\\vee',
        '¬': '\\neg',
        '→': '\\rightarrow',
        '←': '\\leftarrow',
        '↔': '\\leftrightarrow',
        '⇒': '\\Rightarrow',
        '⇐': '\\Leftarrow',
        '⇔': '\\Leftrightarrow'
    };
    
    // 6. 检测并修复元宝特有的公式格式
    // 元宝会把公式如 \sum_{k=1}^{K} p_k^2 渲染成 k=1∑K​pk2​
    // 这种格式很难完全还原，但我们可以尝试识别并包装为$$
    
    // 匹配看起来像被渲染过的公式的文本
    // 特征：包含数学Unicode符号、下标上标格式等
    result = result.replace(/([A-Za-z]+\([A-Za-z]\)\s*=\s*[^\n]+(?:[∑∏∫∞αβγδεθλμσπω]|[₀-₉⁰-⁹])[^\n]*)/g, function(match) {
        // 如果已经在$$中，跳过
        if (match.indexOf('$$') !== -1) return match;
        // 如果在代码块中，跳过
        if (match.indexOf('```') !== -1) return match;
        
        // 尝试将Unicode数学符号转换回LaTeX
        var latex = match;
        for (var symbol in mathSymbolMap) {
            latex = latex.split(symbol).join(mathSymbolMap[symbol]);
        }
        
        // 处理下标和上标的Unicode字符
        latex = latex.replace(/([a-z])([₀-₉]+)/gi, function(m, letter, subscript) {
            var num = subscript.replace(/[₀₁₂₃₄₅₆₇₈₉]/g, function(c) {
                return '0123456789'['₀₁₂₃₄₅₆₇₈₉'.indexOf(c)];
            });
            return letter + '_{' + num + '}';
        });
        latex = latex.replace(/([a-z])([⁰¹²³⁴⁵⁶⁷⁸⁹]+)/gi, function(m, letter, superscript) {
            var num = superscript.replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹]/g, function(c) {
                return '0123456789'['⁰¹²³⁴⁵⁶⁷⁸⁹'.indexOf(c)];
            });
            return letter + '^{' + num + '}';
        });
        
        return '$$' + latex + '$$';
    });
    
    // 7. 处理独立行的公式（被代码块包裹的公式文本）
    result = result.replace(/```\n([^`]+(?:[∑∏∫∞]|[=\-+])[^`]+)\n```/g, function(match, formula) {
        // 将Unicode数学符号转换回LaTeX
        var latex = formula.trim();
        for (var symbol in mathSymbolMap) {
            latex = latex.split(symbol).join(mathSymbolMap[symbol]);
        }
        return '$$' + latex + '$$';
    });
    
    // 8. 处理元宝特有的公式格式：函数名(变量)=表达式
    // 如：Entropy(D)=−k=1∑K​pk​log2​pk​
    result = result.replace(/\n([A-Za-z]+\([A-Za-z]+\)\s*=\s*[^\n]*[∑∏∫∞−×÷±αβγδεθλμσπω][^\n]*)\n/g, function(match, formula) {
        // 如果已经在$$中或代码块中，跳过
        if (formula.indexOf('$$') !== -1 || formula.indexOf('```') !== -1) return match;
        
        var latex = formula.trim();
        for (var symbol in mathSymbolMap) {
            latex = latex.split(symbol).join(mathSymbolMap[symbol]);
        }
        return '\n$$' + latex + '$$\n';
    });
    
    // 9. 处理元宝特有的下标格式: pk​ -> p_k (带有零宽空格的下标)
    // 元宝会用特殊方式表示下标
    result = result.replace(/([a-zA-Z])([a-zA-Z])​/g, function(match, base, subscript) {
        return base + '_{' + subscript + '}';
    });
    
    // 10. 处理log2​ -> \log_2 格式
    result = result.replace(/log([0-9]+)​/g, '\\log_{$1}');
    
    // 11. 修复元宝表格格式 - 智能表格修复
    result = fixYuanbaoTable(result);
    
    // 12. 修复重复的换行
    result = result.replace(/\n{3,}/g, '\n\n');
    
    return result;
}

function processMarkdown(markdown) {
    // 预处理元宝格式
    markdown = preprocessYuanbaoMarkdown(markdown);
    
    // 保存原始Markdown内容
    var originalMarkdown = markdown;
    var processedMarkdown = markdown;
    
    // 直接将代码块转换为HTML格式，不使用占位符
    // 步骤1：预处理代码块 - 直接将代码块转换为HTML格式
    function detectLanguage(code) {
        // 默认为普通文本
        var language = 'plaintext';
        
        // 简单的语言检测逻辑
        if (code.match(/^\s*(import|from|def|class|if __name__)/m)) {
            language = 'python';
        } else if (code.match(/^\s*(function|const|let|var|import from|export|=>)/m)) {
            language = 'javascript';
        } else if (code.match(/^\s*(public class|private|protected|void|static|@Override)/m)) {
            language = 'java';
        } else if (code.match(/^\s*(#include|int main|std::)/m)) {
            language = 'cpp';
        } else if (code.match(/^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE TABLE)/im)) {
            language = 'sql';
        } else if (code.match(/^\s*(<html|<!DOCTYPE|<head|<body)/m)) {
            language = 'html';
        } else if (code.match(/^\s*(body|margin|padding|font-size|color:|background:)/m)) {
            language = 'css';
        }
        
        return language;
    }
    
    // 匹配带有语言标识的代码块: ```python、```javascript等
    processedMarkdown = processedMarkdown.replace(/```(\w*)\s*\n([\s\S]*?)```/g, function(match, language, code) {
        var lang = language.trim() || detectLanguage(code.trim());
        return '<pre><code class="language-' + lang + '">' + 
               code.trim()
                   .replace(/&/g, '&amp;')
                   .replace(/</g, '&lt;')
                   .replace(/>/g, '&gt;') + 
               '</code></pre>';
    });
    
    // 匹配不带语言标识的代码块
    processedMarkdown = processedMarkdown.replace(/```([\s\S]*?)```/g, function(match, code) {
        var lang = detectLanguage(code.trim());
        return '<pre><code class="language-' + lang + '">' + 
               code.trim()
                   .replace(/&/g, '&amp;')
                   .replace(/</g, '&lt;')
                   .replace(/>/g, '&gt;') + 
               '</code></pre>';
    });
    
    // 步骤2：处理数学公式
    // 处理原生的\[ ... \]格式的公式（可能跨多行）
    processedMarkdown = processedMarkdown.replace(/\\\[([\s\S]*?)\\\]/g, function(match, formula) {
        return '$$' + formula + '$$';
    });
    
    // 将方括号内的LaTeX公式转换为$$..$$格式
    processedMarkdown = processedMarkdown.replace(/\[([\s\S]*?)\]/g, function(match, formula) {
        // 只有当括号中的内容包含公式特性的内容才进行转换
        if (formula.indexOf('\\beta') !== -1 || 
            formula.indexOf('\\frac') !== -1 || 
            formula.indexOf('_') !== -1 || 
            formula.indexOf('^') !== -1 || 
            formula.indexOf('\\epsilon') !== -1 ||
            formula.indexOf('\\left') !== -1 ||
            formula.indexOf('\\right') !== -1 ||
            formula.indexOf('\\cdots') !== -1) {
            return '$$' + formula + '$$';
        }
        return match; // 如果不是公式，保持原样
    });
    
    // 步骤3：使用Showdown转换markdown为HTML
    var converter = new showdown.Converter({
        tables: true,         // 启用表格支持
        strikethrough: true,  // 启用删除线
        tasklists: true,      // 支持任务列表
        simpleLineBreaks: true, // 简单换行
        emoji: true,          // 支持emoji
        literalMidWordUnderscores: true, // 支持单词内的下划线
        parseImgDimensions: true // 支持图片尺寸
    });
    
    // 转换Markdown为HTML
    var html = converter.makeHtml(processedMarkdown);
    
    // 步骤4：修复可能被错误处理的代码块
    // 从原始Markdown中重新提取代码块
    var codeBlocksFromOriginal = [];
    var codeBlockRegex = /```(\w*)\s*\n([\s\S]*?)```/g;
    var match;
    
    while ((match = codeBlockRegex.exec(originalMarkdown)) !== null) {
        codeBlocksFromOriginal.push({
            language: match[1].trim(),
            code: match[2].trim()
        });
    }
    
    // 处理可能存在的各种代码块格式问题
    
    // 1. 处理可能存在的CODEBLOCK_格式
    html = html.replace(/CODEBLOCK_(\d+)/g, function(match, index) {
        if (codeBlocksFromOriginal[parseInt(index)]) {
            var block = codeBlocksFromOriginal[parseInt(index)];
            var lang = block.language || detectLanguage(block.code);
            return '<pre><code class="language-' + lang + '">' + 
                   block.code
                       .replace(/&/g, '&amp;')
                       .replace(/</g, '&lt;')
                       .replace(/>/g, '&gt;') + 
                   '</code></pre>';
        }
        return match;
    });
    
    // 2. 处理可能存在的~CODEBLOCK_PLACEHOLDER_格式
    html = html.replace(/~+CODEBLOCK_PLACEHOLDER_(\d+)~+/g, function(match, index) {
        if (codeBlocksFromOriginal[parseInt(index)]) {
            var block = codeBlocksFromOriginal[parseInt(index)];
            var lang = block.language || detectLanguage(block.code);
            return '<pre><code class="language-' + lang + '">' + 
                   block.code
                       .replace(/&/g, '&amp;')
                       .replace(/</g, '&lt;')
                       .replace(/>/g, '&gt;') + 
                   '</code></pre>';
        }
        return match;
    });
    
    // 3. 处理可能存在的CODE_格式
    html = html.replace(/__CODE_(\d+)__/g, function(match, index) {
        if (codeBlocksFromOriginal[parseInt(index)]) {
            var block = codeBlocksFromOriginal[parseInt(index)];
            var lang = block.language || detectLanguage(block.code);
            return '<pre><code class="language-' + lang + '">' + 
                   block.code
                       .replace(/&/g, '&amp;')
                       .replace(/</g, '&lt;')
                       .replace(/>/g, '&gt;') + 
                   '</code></pre>';
        }
        return match;
    });
    
    // 4. 处理可能存在的<pre class='code数字'>格式
    html = html.replace(/<pre\s+class=["']code(\d+)["']>([\s\S]*?)<\/pre>/g, function(match, index, content) {
        if (codeBlocksFromOriginal[parseInt(index)]) {
            var block = codeBlocksFromOriginal[parseInt(index)];
            var lang = block.language || detectLanguage(block.code);
            return '<pre><code class="language-' + lang + '">' + 
                   block.code
                       .replace(/&/g, '&amp;')
                       .replace(/</g, '&lt;')
                       .replace(/>/g, '&gt;') + 
                   '</code></pre>';
        }
        // 如果找不到对应的原始代码块，则尝试处理content
        var lang = detectLanguage(content);
        return '<pre><code class="language-' + lang + '">' + 
               content
                   .replace(/&/g, '&amp;')
                   .replace(/</g, '&lt;')
                   .replace(/>/g, '&gt;') + 
               '</code></pre>';
    });
    
    // 5. 处理可能被转换为段落的代码块
    html = html.replace(/<p>```([\s\S]*?)```<\/p>/g, function(match, content) {
        // 尝试提取语言和代码
        var langMatch = content.match(/^(\w*)\s*\n([\s\S]*?)$/);
        if (langMatch) {
            var lang = langMatch[1].trim() || detectLanguage(langMatch[2].trim());
            return '<pre><code class="language-' + lang + '">' + 
                   langMatch[2].trim()
                       .replace(/&/g, '&amp;')
                       .replace(/</g, '&lt;')
                       .replace(/>/g, '&gt;')
                       .replace(/<br\s*\/?>/g, '\n') + 
                   '</code></pre>';
        }
        // 如果无法提取，则整体处理
        var lang = detectLanguage(content.replace(/```/g, '').trim());
        return '<pre><code class="language-' + lang + '">' + 
               content.replace(/```/g, '').trim()
                   .replace(/&/g, '&amp;')
                   .replace(/</g, '&lt;')
                   .replace(/>/g, '&gt;')
                   .replace(/<br\s*\/?>/g, '\n') + 
               '</code></pre>';
    });
    
    // 6. 确保所有代码块都有正确的类名
    html = html.replace(/<pre><code>((?!class=)[\s\S]*?)<\/code><\/pre>/g, function(match, content) {
        var lang = detectLanguage(content);
        return '<pre><code class="language-' + lang + '">' + 
               content + 
               '</code></pre>';
    });
    
    // 第四步：添加MathJax配置，与网站现有配置保持一致
    var mathjaxConfig = '<script type="text/javascript">\n' +
        'window.MathJax = {\n' +
        '  tex: {\n' +
        '    inlineMath: [["$", "$"], ["\\\\(", "\\\\)"]],\n' +
        '    displayMath: [["$$", "$$"], ["\\\\[", "\\\\]"]],\n' +
        '    processEscapes: true,\n' +
        '    processEnvironments: true\n' +
        '  },\n' +
        '  options: {\n' +
        '    ignoreHtmlClass: "tex2jax_ignore",\n' +
        '    processHtmlClass: "tex2jax_process"\n' +
        '  },\n' +
        '  startup: {\n' +
        '    ready: function() {\n' +
        '      MathJax.startup.defaultReady();\n' +
        '    }\n' +
        '  }\n' +
        '};\n' +
        '</script>\n';
    
    // 添加MathJax脚本支持，使用与网站相同的版本和渲染器
    var mathjaxSupport = mathjaxConfig +
        '<script type="text/javascript" id="MathJax-script" async ' +
        'src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>';
    
    // 添加表格样式 - 增强美观性
    var styles = '<style>\n' +
        'table {border-collapse: collapse; width: 100%; margin: 16px 0; font-size: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);}\n' +
        'table, th, td {border: 1px solid #e0e0e0;}\n' +
        'th, td {padding: 12px 16px; text-align: left; vertical-align: top;}\n' +
        'th {background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%); font-weight: 600; color: #333;}\n' +
        'tr:nth-child(even) {background-color: #f8f9fa;}\n' +
        'tr:hover {background-color: #e8f4fd;}\n' +
        'td:first-child {font-weight: 500; white-space: nowrap;}\n' +
        '</style>\n';
    
    // 特别为网站添加的公式处理脚本
    var specialMathJaxScript = '<script>\n' +
        'setTimeout(function() {\n' +
        '  // 获取文章内容元素\n' +
        '  const contentElement = document.getElementById(\'content\');\n' +
        '  if (!contentElement) return;\n' +
        '  \n' +
        '  // 获取HTML内容\n' +
        '  let html = contentElement.innerHTML;\n' +
        '  \n' +
        '  // 使用正则表达式处理多行公式\n' +
        '  // 注意这里的s标志可以匹配多行内容\n' +
        '  html = html.replace(/\\[([\\s\\S]*?)\\]/gs, function(match, formula) {\n' +
        '    // 只有当括号中的内容包含公式特性的内容才进行转换\n' +
        '    if (formula.indexOf(\'\\\\beta\') !== -1 || \n' +
        '        formula.indexOf(\'\\\\frac\') !== -1 || \n' +
        '        formula.indexOf(\'_\') !== -1 || \n' +
        '        formula.indexOf(\'^\') !== -1 || \n' +
        '        formula.indexOf(\'\\\\epsilon\') !== -1 ||\n' +
        '        formula.indexOf(\'\\\\left\') !== -1 ||\n' +
        '        formula.indexOf(\'\\\\right\') !== -1 ||\n' +
        '        formula.indexOf(\'\\\\cdots\') !== -1) {\n' +
        '      return \'$$\' + formula + \'$$\';\n' +
        '    }\n' +
        '    return match; // 如果不是公式，保持原样\n' +
        '  });\n' +
        '  \n' +
        '  // 更新内容\n' +
        '  contentElement.innerHTML = html;\n' +
        '  \n' +
        '  // 重新渲染数学公式\n' +
        '  MathJax && MathJax.typeset && MathJax.typeset();\n' +
        '}, 500);\n' +
        '</script>';
    
    html = styles + html + mathjaxSupport + specialMathJaxScript;
    
    $('.file-tip').html('转换成功');
    contentImport.data.result = html;
    $('.file-result').html(html).show();
    
    // 初始化MathJax渲染
    if (window.MathJax) {
        try {
            window.MathJax.typesetPromise && window.MathJax.typesetPromise();
        } catch(e) {
            console.error('MathJax渲染失败:', e);
        }
    }
}

function processMarkdownFile(file) {
    $('.file-tip').html('正在转换Markdown文件，请稍后...');
    $('.file-result').html('').hide();
    var reader = new FileReader();
    reader.onload = function (loadEvent) {
        // 加载MathJax脚本以支持数学公式
        if (!window.MathJax) {
            // 加载MathJax配置和脚本
            var configScript = document.createElement('script');
            configScript.type = 'text/javascript';
            configScript.text = 'window.MathJax = {' +
                'tex: {' +
                '  inlineMath: [["\\\\(", "\\\\)"]],' +
                '  displayMath: [["\\\\[", "\\\\]"]],' +
                '  processEscapes: true,' +
                '  processEnvironments: true,' +
                '  macros: {' +
                '    beta: "\\\\beta",' +
                '    epsilon: "\\\\epsilon",' +
                '    hat: ["\\\\hat{#1}", 1]' +
                '  }' +
                '},' +
                'options: {' +
                '  ignoreHtmlClass: "tex2jax_ignore",' +
                '  processHtmlClass: "tex2jax_process"' +
                '},' +
                'startup: {' +
                '  ready: function() {' +
                '    MathJax.startup.defaultReady();' +
                '  }' +
                '}' +
              '};';
            document.head.appendChild(configScript);
            
            $.getScript('https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js', function() {
                processMarkdown(loadEvent.target.result);
            });
        } else {
            processMarkdown(loadEvent.target.result);
        }
    };
    reader.onerror = function (loadEvent) {
        $('.file-tip').html('Markdown文件转换失败:' + loadEvent);
    };
    reader.readAsText(file, "UTF-8");
}

function addUploadButtonListener() {
    g('contentImport').addEventListener('change', function () {
        const file = this.files[0];
        const fileName = file.name;
        const fileExt = fileName.substring(fileName.lastIndexOf('.') + 1).toLowerCase();
        switch (fileExt) {
            case 'docx':
            case 'doc':
                processWord(file);
                break;
            case 'md':
                processMarkdownFile(file);
                break;
            default:
                $('.file-tip').html('不支持的文件格式:' + fileExt);
                break;
        }
    });
    g('fileInputConfirm').addEventListener('click', function () {
        processMarkdown( g('fileInputContent').value );
        $('.file-input').hide();
    });
}

function addOkListener() {
    dialog.onok = function () {
        if (!contentImport.data.result) {
            alert('请先上传文件识别内容');
            return false;
        }
        
        // 内容已经包含样式，直接插入
        var content = contentImport.data.result;
        
        // 检查是否已包含MathJax，如果不包含则添加
        if (content.indexOf('MathJax-script') === -1) {
            // 添加MathJax配置和脚本，使用与网站相同的配置
            var mathjaxConfig = '<script type="text/javascript">\n' +
                'window.MathJax = {\n' +
                '  tex: {\n' +
                '    inlineMath: [["$", "$"], ["\\\\(", "\\\\)"]],\n' +
                '    displayMath: [["$$", "$$"], ["\\\\[", "\\\\]"]],\n' +
                '    processEscapes: true,\n' +
                '    processEnvironments: true\n' +
                '  },\n' +
                '  options: {\n' +
                '    ignoreHtmlClass: "tex2jax_ignore",\n' +
                '    processHtmlClass: "tex2jax_process"\n' +
                '  },\n' +
                '  startup: {\n' +
                '    ready: function() {\n' +
                '      MathJax.startup.defaultReady();\n' +
                '    }\n' +
                '  }\n' +
                '};\n' +
                '</script>\n';
            
            var mathjaxScript = '<script type="text/javascript" id="MathJax-script" async ' +
                'src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>';
                            // 特别为网站添加的公式处理脚本，处理方括号内的公式
            var specialMathJaxScript = '<script>\n' +
                'setTimeout(function() {\n' +
                '  var contentElement = document.getElementById(\'content\');\n' +
                '  if (!contentElement) {\n' +
                '    contentElement = document.querySelector(\'.ueditor-content\');\n' +
                '  }\n' +
                '  if (!contentElement) return;\n' +
                '  \n' +
                '  let html = contentElement.innerHTML;\n' +
                '  \n' +
                '  // 使用正则表达式处理多行公式\n' +
                '  // 注意这里的s标志可以匹配多行内容\n' +
                '  html = html.replace(/\\[([\\s\\S]*?)\\]/gs, function(match, formula) {\n' +
                '    // 只有当括号中的内容包含公式特性的内容才进行转换\n' +
                '    if (formula.indexOf(\'\\\\beta\') !== -1 || \n' +
                '        formula.indexOf(\'\\\\frac\') !== -1 || \n' +
                '        formula.indexOf(\'_\') !== -1 || \n' +
                '        formula.indexOf(\'^\') !== -1 || \n' +
                '        formula.indexOf(\'\\\\epsilon\') !== -1 ||\n' +
                '        formula.indexOf(\'\\\\left\') !== -1 ||\n' +
                '        formula.indexOf(\'\\\\right\') !== -1 ||\n' +
                '        formula.indexOf(\'\\\\cdots\') !== -1) {\n' +
                '      return \'$$\' + formula + \'$$\';\n' +
                '    }\n' +
                '    return match; // 如果不是公式，保持原样\n' +
                '  });\n' +
                '  \n' +
                '  contentElement.innerHTML = html;\n' +
                '  \n' +
                '  MathJax && MathJax.typeset && MathJax.typeset();\n' +
                '}, 500);\n' +
                '</script>';
                
            content = mathjaxConfig + content + mathjaxScript + specialMathJaxScript;
        }
        
        editor.fireEvent('saveScene');
        editor.execCommand("inserthtml", content);
        editor.fireEvent('saveScene');
        
        // 重新初始化MathJax渲染，以确保公式正确显示
        if (window.MathJax) {
            setTimeout(function() {
                try {
                    // MathJax 3.x
                    if (window.MathJax && window.MathJax.typeset) {
                        window.MathJax.typeset();
                        
                        // 额外处理方括号中的公式
                        var contentElement = document.getElementById('content');
                        if (!contentElement) {
                            contentElement = document.querySelector('.ueditor-content');
                        }
                        if (contentElement) {
                            var html = contentElement.innerHTML;
                            // 使用正则表达式处理多行公式
                            html = html.replace(/\[([\s\S]*?)\]/gs, function(match, formula) {
                                // 只有当括号中的内容包含公式特性的内容才进行转换
                                if (formula.indexOf('\\beta') !== -1 || 
                                    formula.indexOf('\\frac') !== -1 || 
                                    formula.indexOf('_') !== -1 || 
                                    formula.indexOf('^') !== -1 || 
                                    formula.indexOf('\\epsilon') !== -1 ||
                                    formula.indexOf('\\left') !== -1 ||
                                    formula.indexOf('\\right') !== -1 ||
                                    formula.indexOf('\\cdots') !== -1) {
                                    return '$$' + formula + '$$';
                                }
                                return match; // 如果不是公式，保持原样
                            });                            
                            contentElement.innerHTML = html;
                            window.MathJax.typeset();
                        }
                        console.log('MathJax渲染成功');
                    } 
                    // MathJax 2.x
                    else if (window.MathJax && window.MathJax.Hub) {
                        window.MathJax.Hub.Queue(["Typeset", window.MathJax.Hub]);
                    }
                } catch(e) {
                    console.error('MathJax初始化或渲染失败:', e);
                }
            }, 1000); // 增加延时确保内容已加载
        }
    };
    dialog.oncancel = function () {
    };
}
