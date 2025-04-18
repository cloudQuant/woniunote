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

function processMarkdown(markdown) {
    // 第一步：处理代码块，保护它们不被当作公式处理
    var codeBlocks = [];
    var codeBlockIndex = 0;
    var processedMarkdown = markdown;
    
    // 先提取代码块避免其中的$ 符号被当作数学公式处理
    processedMarkdown = processedMarkdown.replace(/```([\s\S]*?)```/g, function(match) {
        var placeholder = "__CODE_" + codeBlockIndex + "__";
        codeBlocks.push({placeholder: placeholder, content: match});
        codeBlockIndex++;
        return placeholder;
    });
    
    // 第二步：使用Showdown转换markdown为HTML
    var converter = new showdown.Converter({
        tables: true,         // 启用表格支持
        strikethrough: true,  // 启用删除线
        tasklists: true,      // 支持任务列表
        simpleLineBreaks: true, // 简单换行
        emoji: true,          // 支持emoji
        literalMidWordUnderscores: true, // 支持单词内的下划线
        parseImgDimensions: true // 支持图片尺寸
    });
    
    // 页面上的MathJax配置支持$ $也支持\( \)格式，所以我们先将所有公式转换为$ $格式
    // 这样处理我们可以让Showdown正常处理Markdown，而公式部分不会被讨匀
    
    // 处理原生的\[ ... \]格式的公式（可能跨多行）
    processedMarkdown = processedMarkdown.replace(/\\\[([\s\S]*?)\\\]/g, function(match, formula) {
        return '$$' + formula + '$$';
    });
    
    // 将方括号内的LaTeX公式转换为$$..$$格式
    // 注意这里的正则使用[\s\S]*?来匹配包括换行在内的任意字符
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
    
    // 转换Markdown为HTML
    var html = converter.makeHtml(processedMarkdown);
    
    // 第三步：将代码块放回到HTML中
    codeBlocks.forEach(function(block) {
        html = html.replace(block.placeholder, block.content);
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
    
    // 添加表格样式
    var styles = '<style>\n' +
        'table {border-collapse: collapse; width: 100%; margin: 10px 0;}\n' +
        'table, th, td {border: 1px solid #ddd;}\n' +
        'th, td {padding: 8px; text-align: left;}\n' +
        'th {background-color: #f2f2f2;}\n' +
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
