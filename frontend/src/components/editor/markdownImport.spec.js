import { describe, it, expect } from 'vitest'
// 引入“导入内容”对话框实际加载的转换器（public/ 静态资源，UMD 模块）
import MarkdownImport from '../../../public/ueditor/dialogs/contentimport/markdown-import.js'

const { convertMarkdownToHtml } = MarkdownImport

/**
 * Markdown 导入公式处理测试。
 *
 * 背景：豆包/DeepSeek 等生成的 Markdown 使用 $...$ / $$...$$ 书写公式，
 * ChatGPT 使用 \(...\) / \[...\]。转换器必须：
 *   1. 在应用斜体/删除线等正则前把公式段提取出来（否则 $c^*$ 的 *
 *      会被误转成 <em>，公式被拆坏）；
 *   2. 对公式内容做 HTML 转义（否则 $p<x$ 的 < 会被浏览器当标签
 *      起始符吞掉公式）；
 *   3. 保留 $$ 双定界符原样（String.replace 的字符串替换会把 $$ 折叠
 *      成 $，必须用函数形式还原）。
 */
describe('editor/markdown-import: 数学公式保护', () => {
  it.each([
    {
      name: '同行多个含 * 的行内公式不被斜体正则破坏（豆包常见）',
      input: '临界值 $c^*$ 与样本量 $n^*$ 的关系',
      expectFragment: ['$c^*', '$n^*$'],
      forbidFragment: ['<em>']
    },
    {
      name: '公式内的 < 和 > 被转义（不等式场景）',
      input: '当 $p<\\alpha$ 时拒绝原假设，且 $Z>z_{0.05}$',
      expectFragment: ['$p&lt;\\alpha$', '$Z&gt;z_{0.05}$'],
      forbidFragment: []
    },
    {
      name: '块级 $$ 公式完整还原（双 $ 不折叠为单 $）',
      input: '方差为：$$\\sigma_p^2 = \\sum w_i^2\\sigma_i^2$$',
      expectFragment: ['$$\\sigma_p^2 = \\sum w_i^2\\sigma_i^2$$'],
      forbidFragment: []
    },
    {
      name: '多行 $$ 块公式（含空行）整体保留、不被段落切分',
      input: '期望收益：\n$$\nE(R_p) = \\sum_{i=1}^{n} w_i E(R_i)\n\nw_i \\geq 0\n$$',
      expectFragment: ['$$\nE(R_p) = \\sum_{i=1}^{n} w_i E(R_i)\n\nw_i \\geq 0\n$$'],
      forbidFragment: []
    },
    {
      name: 'ChatGPT 行内格式 \\(...\\) 归一为 $...$',
      input: '能量 \\(E = mc^2\\) 守恒',
      expectFragment: ['$E = mc^2$'],
      forbidFragment: ['\\(']
    },
    {
      name: 'ChatGPT 块级格式 \\[...\\] 归一为 $$...$$',
      input: '推导：\n\\[E = mc^2\\]',
      expectFragment: ['$$E = mc^2$$'],
      forbidFragment: ['\\[']
    },
    {
      name: '公式中的 & 被转义（aligned 环境）',
      input: '$$\\begin{aligned} a &= b \\\\ c &= d\\end{aligned}$$',
      expectFragment: ['a &amp;= b'],
      forbidFragment: []
    },
    {
      name: '表格单元格中的公式保持完整',
      input: '| 指标 | 公式 |\n|---|---|\n| 临界值 | $c^*$ 与 $n^*$ |\n',
      expectFragment: ['<td>$c^*$ 与 $n^*$</td>'],
      forbidFragment: ['<em>']
    }
  ])('$name', ({ input, expectFragment, forbidFragment }) => {
    const html = convertMarkdownToHtml(input)
    expectFragment.forEach((frag) => {
      expect(html).toContain(frag)
    })
    forbidFragment.forEach((frag) => {
      expect(html).not.toContain(frag)
    })
  })

  it('渲染到 DOM 后公式文本完整（$p<x$ 不被浏览器吞掉）', () => {
    const html = convertMarkdownToHtml('当 $p<x$ 时拒绝原假设')
    const div = document.createElement('div')
    div.innerHTML = html
    expect(div.textContent).toContain('$p<x$')
  })

  it('货币写法（$ 后/前有空白）不误判为公式', () => {
    const html = convertMarkdownToHtml('价格是 $100 和 $200 之间')
    expect(html).not.toContain('$$')
    expect(html).toContain('$100 和 $200')
  })
})

describe('editor/markdown-import: 豆包复制伪影清理', () => {
  // 豆包"复制"按钮的已知伪影：同一段公式碎片被拼接进文中每个连字符位置，
  // 碎片内部还嵌套着未配对的 \( （结构上不可能是合法公式）。
  // 注：碎片中的 w_{t‑1} 使用 U+2011 不换行连字符，与真实数据一致
  const BLOB = String.raw`\(\Delta Q_{t}=\Vert Q_{t}-Q_{t\(min \ w^{T} H_{t} w-\mu^{T} w+\tau\left\| w-w_{t‑1}\right\| _{2}^{2}\)1}\Vert_F\)`

  it('重复拼接的公式碎片（≥3次）还原为连字符', () => {
    const md = [
      '# 波动率' + BLOB + '相关性耦合关系（Module4' + BLOB + 'Lesson5）',
      '',
      '相关性由0.3' + BLOB + '0.6跳升至0.8以上',
      ''
    ].join('\n')
    const html = convertMarkdownToHtml(md)
    expect(html).toContain('<h1>波动率-相关性耦合关系（Module4-Lesson5）</h1>')
    expect(html).toContain('0.3-0.6')
  })

  it('碎片嵌在公式内部时重建原始公式（Q_{t-1}）', () => {
    const md = [
      '# 波动率' + BLOB + '相关性',
      '',
      '矩阵' + BLOB + 'Heston模型',
      '',
      '范数$\\Delta Q_{t}=\\Vert Q_{t}-Q_{t' + BLOB + '1}\\Vert_F$监控',
      ''
    ].join('\n')
    const html = convertMarkdownToHtml(md)
    expect(html).toContain('波动率-相关性')
    expect(html).toContain('矩阵-Heston模型')
    expect(html).toContain('$\\Delta Q_{t}=\\Vert Q_{t}-Q_{t-1}\\Vert_F$')
  })

  it('$\\(...\\)$ 双定界符解包为单层', () => {
    const html = convertMarkdownToHtml('把协方差矩阵$\\(V(t)\\)$本身设置为随机过程')
    expect(html).toContain('$V(t)$')
    expect(html).not.toContain('$\\(')
  })

  it('公式内部被豆包加裹的 \\( \\) 剥除定界符（括号属于定界符本身）', () => {
    const html = convertMarkdownToHtml('\\[\\sqrt{\\(V(t)\\)} d W(t)\\]')
    expect(html).toContain('$$\\sqrt{V(t)} d W(t)$$')
    expect(html).not.toContain('\\(')
  })

  it('$ 定界符旁的伪影不折叠（含嵌套子片段，整体作为一个公式块）', () => {
    // 豆包把三行阈值互相嵌套损坏：外层紧邻 $，内层子片段不紧邻 $
    // 但仍处于 $...$ 公式内部，也不得折叠
    const span3 = String.raw`\(EVR_1>1.5\times\(EVR_1>2.0\times\(EVR_1>2.5\times历史均值\)\)\)`
    const md = [
      '- $EVR_1>1.5\\times' + span3 + '$：风险升高',
      '- $EVR_1>2.0\\times' + span3 + '$：压力测试',
      '- $EVR_1>2.5\\times' + span3 + '$：危机状态'
    ].join('\n')
    const html = convertMarkdownToHtml(md)
    // 未折叠为连字符，整体保留为公式（内层定界符全部剥除）
    expect(html).toContain('EVR_1&gt;1.5\\timesEVR_1&gt;1.5\\timesEVR_1&gt;2.0\\timesEVR_1&gt;2.5\\times历史均值')
    expect(html).not.toContain('\\times-')
    expect(html).not.toContain('-EVR_1')
  })

  it('正常公式重复出现不受伪影清理影响', () => {
    const html = convertMarkdownToHtml('值\\(a+b\\)与\\(a+b\\)和\\(a+b\\)的和')
    expect((html.match(/\$a\+b\$/g) || []).length).toBe(3)
    expect(html).not.toContain('-a+b-')
  })

  it('合法形态的碎片（两侧紧贴字母数字）也折叠为连字符', () => {
    // 豆包伪影的另一形态：碎片本身是完全合法的公式（如 n(n-1)/2），
    // 被拼进每个连字符位置。判定证据：同一碎片逐字重复 ≥3 次，
    // 且至少一处两侧紧贴字母数字（正规行内公式两侧通常是空白、
    // 中文或标点，不会嵌在 Module4...Lesson4 这类拉丁复合词内部）
    const frag = String.raw`\(\frac{n(n‑1)}{2}\)`
    const md = [
      '# 高级相关性结构（Module4' + frag + 'Lesson4）',
      '',
      '奔向安全资产Flight' + frag + 'to' + frag + 'quality',
      '',
      '置信区间47' + frag + '76，组合大幅改变。',
      '',
      '股' + frag + '债相关性转为显著负。'
    ].join('\n')
    const html = convertMarkdownToHtml(md)
    expect(html).toContain('（Module4-Lesson4）')
    expect(html).toContain('Flight-to-quality')
    expect(html).toContain('47-76')
    // CJK 夹心的出现与公式内部的出现随整个碎片一并定罪
    expect(html).toContain('股-债')
  })

  it('碎片嵌在 $ 公式内部时同样折叠', () => {
    const frag = String.raw`\(\frac{n(n‑1)}{2}\)`
    const md = [
      '标题A' + frag + '标题B',
      '',
      '说明C' + frag + '说明D',
      '',
      '两两参数$\\frac{n' + frag + '1)}{2}$需要估计'
    ].join('\n')
    const html = convertMarkdownToHtml(md)
    expect(html).toContain('标题A-标题B')
    expect(html).toContain('$\\frac{n-1)}{2}$')
  })

  it('中文夹心的正常重复公式不折叠（无字母数字夹心证据）', () => {
    const md = '能量为\\(E=mc^2\\)焦耳，质量\\(E=mc^2\\)守恒，又说\\(E=mc^2\\)不变'
    const html = convertMarkdownToHtml(md)
    expect((html.match(/\$E=mc\^2\$/g) || []).length).toBe(3)
    expect(html).not.toContain('-E=mc^2-')
  })

  it('解包 $\\(...\\)$ 不得跨行/跨 $ 吞并后续内容', () => {
    // 豆包真实案例：$\(V(t)\)=D(t)R(t)D(t)$ 的闭合定界符不是 \)$，
    // 解包正则若允许跨行，会一路吞到若干行之后 EVR 段落的 \)$，
    // 毁掉中间所有内容
    const md = [
      '分解形式 $\\(V(t)\\)=D(t)R(t)D(t)$：$D$对角矩阵，$R$相关矩阵。',
      '',
      '正文若干行。',
      '',
      '- $EVR_1>1.5\\times\\(EVR_1>2.5\\times历史均值\\)$：风险升高'
    ].join('\n')
    const html = convertMarkdownToHtml(md)
    expect(html).toContain('$V(t)=D(t)R(t)D(t)$')
    expect(html).toContain('$D$')
    expect(html).toContain('$R$')
    expect(html).toContain('正文若干行。')
    // EVR 行保持为单个完整公式（内层定界符剥除）
    expect(html).toContain('EVR_1&gt;1.5\\timesEVR_1&gt;2.5\\times历史均值')
  })
})

describe('editor/markdown-import: 既有语法回归', () => {
  it.each([
    {
      name: '标题与粗体',
      input: '# 标题\n\n**加粗** 内容',
      expectFragment: ['<h1>标题</h1>', '<strong>加粗</strong>']
    },
    {
      name: '代码块中的 $ 不当作公式',
      input: '```\nconst price = `$${amount}`\n```',
      expectFragment: ['$${amount}'],
      forbidFragment: ['<em>', '$<']
    },
    {
      name: '行内代码中的 $ 不当作公式',
      input: '变量 `cost$_1` 的值',
      expectFragment: ['cost$_1</code>'],
      forbidFragment: ['$<']
    },
    {
      name: '列表与表格',
      input: '- 项目一\n\n| a | b |\n|---|---|\n| 1 | 2 |\n',
      expectFragment: ['<li>项目一</li>', '<table>', '<td>1</td>']
    }
  ])('$name', ({ input, expectFragment, forbidFragment = [] }) => {
    const html = convertMarkdownToHtml(input)
    expectFragment.forEach((frag) => {
      expect(html).toContain(frag)
    })
    forbidFragment.forEach((frag) => {
      expect(html).not.toContain(frag)
    })
  })
})
