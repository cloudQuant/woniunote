# 迭代 9：UI 主题美化与多风格切换方案

> 作者：BMad Help（基于 woniunote 前端现状 + VoltAgent/awesome-design-md 设计源分析）
> 日期：2026-05-30
> 分支：dev_cpp（C++ Drogon 后端 + Vue3 前端）
> 范围：前端 UI 美化、设计令牌体系搭建、9 套可切换设计风格、主页主题切换入口
> 参考设计源：https://github.com/VoltAgent/awesome-design-md/tree/main （Google Stitch DESIGN.md 格式，共 73 套）

---

## 一、背景与目标

迭代 7、8 已完成后端安全加固、接口对齐、功能补全与测试体系（前端 Vitest 13/13、后端 ctest 10/10）。功能层面已稳定，但**视觉层面仍是「能用但不够专业」**：

- 全站颜色硬编码、风格拼凑（导航 `#17a2b8`、链接 `#409eff`、登录头 `#337AB7`、卡片阴影各处不一），缺少统一的设计语言。
- 直接用 Element Plus 默认皮肤，没有品牌识别度，与「量化投资」专业定位不匹配。
- 无设计令牌（design token）层，没有暗色模式，无法整体换肤。

**本迭代目标**：把 woniunote 前端从「硬编码样式」升级为「**令牌驱动的可换肤体系**」，并落地 **9 套精选设计风格**，在主页提供**一键切换**入口，切换即时生效并持久化。

> 需求方原话：「优化整个项目的 ui，希望 ui 能够更加美化和专业……从 awesome-design-md 里选 9 套不同的风格，在主页设置一个按钮，可以切换不同的风格。」

---

## 二、前端现状分析（含证据）

| 维度 | 现状 | 证据 | 问题 |
|------|------|------|------|
| 设计令牌 | 不存在 | `assets/main.css` 全是字面量 `#f5f7fa/#409eff/#333` | 无法整体换肤 |
| 颜色硬编码 | 遍布组件 | `AppHeader.vue`（`#17a2b8`、`#337AB7`、`#2b6db4`）、`ArticleCard.vue`（`#fff/#333/#007bff`）、`Home.vue`（`#f5f7fa`） | 改一处色要全局搜替 |
| 组件库主题 | EP 默认皮肤 | `main.js` 仅 `import 'element-plus/dist/index.css'` | 未做 `--el-*` 变量覆盖 |
| 暗色模式 | 无 | 未引入 `element-plus/theme-chalk/dark/css-vars.css` | 暗色风格无基础 |
| 主题状态 | 无 | `stores/` 仅 `user.js`、`article.js` | 无主题持久化/全局状态 |
| 字体 | 系统默认 | `main.css` body `-apple-system…` | 无品牌字体层 |
| 切换入口 | 无 | `AppHeader.vue` 无主题相关 UI | 需新增 |

**技术约束（已核实）**：
- 技术栈 Vue 3.4 + Element Plus 2.5 + Pinia 2.1 + Vite 5（`frontend/package.json`），含 `sass`。
- Element Plus 2.5 支持 CSS 变量主题（`--el-color-primary` 等）与暗色模式（`html.dark` + `dark/css-vars.css`），可在运行时整体换肤，**无需重新编译**。
- 入口 `main.js` / 根组件 `App.vue`（`<el-config-provider>` 包裹）是注入主题的天然挂载点。
- 组件普遍用 `<style scoped>`，迁移令牌时需逐组件替换字面量为 `var(--wn-*)`。

---

## 三、设计源研究：awesome-design-md 里有哪些风格

该仓库是 **Google Stitch「DESIGN.md」** 格式的设计系统文档集合，共 **73 套**，每套含三件套：

| 文件 | 用途 |
|------|------|
| `DESIGN.md` | 设计系统正文（颜色/字体/组件/布局/圆角/阴影/响应式 9 大节，YAML front-matter 携带可解析的 token） |
| `preview.html` | 浅色预览（色板、字阶、按钮、卡片） |
| `preview-dark.html` | 暗色预览 |

每个 `DESIGN.md` 的 YAML front-matter 提供机器可读的令牌：`colors` / `typography` / `rounded` / `spacing` / `components`，**可直接映射为 CSS 变量**——这正是本迭代换肤体系的数据来源。

### 仓库收录的风格分类（节选自官方 README）

- **AI & LLM**：Claude、Cohere、ElevenLabs、Minimax、Mistral、Ollama、OpenCode、Replicate、Runway、Together、VoltAgent、xAI
- **开发者工具/IDE**：Cursor、Expo、Lovable、Raycast、Superhuman、Vercel、Warp
- **后端/数据库/DevOps**：ClickHouse、Composio、HashiCorp、MongoDB、PostHog、Sanity、Sentry、Supabase
- **效率/SaaS**：Cal.com、Intercom、Linear、Mintlify、Notion、Resend、Zapier
- **设计/创意**：Airtable、Clay、Figma、Framer、Miro、Webflow
- **金融/加密**：Binance、Coinbase、Kraken、Mastercard、Revolut、Stripe、Wise
- **电商/零售**：Airbnb、Meta、Nike、Shopify、Starbucks
- **媒体/消费电子**：Apple、HP、IBM、NVIDIA、Pinterest、PlayStation、SpaceX、Spotify、The Verge、Uber、Vodafone、WIRED
- **汽车**：BMW、BMW M、Bugatti、Ferrari、Lamborghini、Renault、Tesla

---

## 四、9 套精选风格（含选型理由与核心令牌）

选型原则：**覆盖 浅色/暗色、冷/暖、编辑感/技术感、极简/鲜明 四个维度**，且契合 woniunote「量化投资」的专业 + 技术调性。下表令牌中，**标 ✅ 的 hex 已从该 DESIGN.md 核实**；未标注的取自官方风格描述，实现时以仓库内 `DESIGN.md` 实际值为准。

| # | 主题 key | 风格名 | 明/暗 | 主色 (primary) | 画布 (canvas) | 气质定位 | 核实 |
|---|----------|--------|-------|----------------|---------------|----------|------|
| 1 | `claude` | Claude 暖调编辑 | 浅 | `#cc785c` 珊瑚 | `#faf9f5` 奶油 | 温暖、文学、衬线标题（**推荐默认**，最适合阅读型博客） | ✅ |
| 2 | `notion` | Notion 简约工作区 | 浅 | `#5645d4` 紫 | `#ffffff` | 干净、友好、彩色卡片 | ✅ |
| 3 | `vercel` | Vercel 极简黑白 | 浅 | `#171717` 墨黑 | `#ffffff` | 极简、单色 + 网格渐变、Geist 几何字 | ✅ |
| 4 | `stripe` | Stripe 优雅紫渐变 | 浅 | `#635bff` 紫 | `#ffffff` | 高级、金融科技、渐变 | 描述 |
| 5 | `starbucks` | Starbucks 大地绿 | 浅 | `#00704a` 绿 | `#f7f5ef` 暖白 | 温暖大地色、品牌感 | 描述 |
| 6 | `linear` | Linear 深邃科技 | 暗 | `#5e6ad2` 薰衣草蓝 | `#010102` 近黑 | 致密、技术、奢静（**推荐暗色默认**） | ✅ |
| 7 | `spotify` | Spotify 沉浸暗夜 | 暗 | `#1ed760` 绿 | `#121212` | 内容优先、暗色、pill 几何 | ✅ |
| 8 | `supabase` | Supabase 代码翡翠 | 暗 | `#3ecf8e` 翡翠绿 | `#1c1c1c` | 代码优先暗色，**契合量化/技术博客** | 描述 |
| 9 | `sentry` | Sentry 数据暗紫 | 暗 | `#7553ff` 紫 | `#1d1127` | 数据密集仪表盘、粉紫强调 | 描述 |

> 浅色 5 套（Claude / Notion / Vercel / Stripe / Starbucks）+ 暗色 4 套（Linear / Spotify / Supabase / Sentry），覆盖暖冷与明暗，避免风格雷同。
> 若需替换：暖色可换 Airbnb（珊瑚）/ Mastercard（暖奶油）；高对比可换 Nike / Uber（黑白大写）；鲜明可换 Stripe→Cohere、Sentry→Kraken。9 套清单可按需求方喜好微调。

---

## 五、技术方案：令牌驱动的换肤架构

### 5.1 核心思路

```
DESIGN.md (YAML tokens)  →  主题令牌文件 themes/*.js|css  →  CSS 变量 (--wn-*)
                                                                    │
                            映射  →  Element Plus 变量 (--el-*)  ──┤  作用于 [data-theme]
                                                                    │
        Pinia themeStore (当前主题 + localStorage 持久化)  →  <html data-theme="claude" class="dark?">
                                                                    │
                            ThemeSwitcher 组件（主页/导航栏按钮）  ─┘
```

要点：
1. **单一令牌层**：定义一套语义化 CSS 变量（`--wn-color-primary` / `--wn-color-canvas` / `--wn-color-surface` / `--wn-color-text` / `--wn-color-muted` / `--wn-color-border` / `--wn-radius-md` / `--wn-font-display` / `--wn-shadow-card` …）。所有组件只消费这套变量，不再写字面量颜色。
2. **主题 = 一组变量值**：每套主题用 `[data-theme="claude"] { --wn-color-primary: #cc785c; … }` 覆盖。切换主题 = 改 `<html data-theme>` 属性，CSS 变量级联即时生效，**零重渲染、零重编译**。
3. **打通 Element Plus**：把 `--el-color-primary`、`--el-bg-color`、`--el-text-color-primary`、`--el-border-color` 等映射到 `--wn-*`，使 EP 的按钮/输入框/弹窗/下拉随主题变。暗色主题额外加 `html.dark` 并引入 `element-plus/theme-chalk/dark/css-vars.css`。
4. **防闪烁（FOUC）**：在 `index.html` 内联一小段脚本，于首屏渲染前从 `localStorage` 读取主题并设好 `data-theme`/`class`，避免先白后变。
5. **持久化**：`themeStore` 写入 `localStorage('wn-theme')`；首次访问用默认主题（建议 `claude`）。

### 5.2 文件落点（计划新增/改动）

```
frontend/src/
├── assets/
│   ├── main.css                 # 改：字面量 → var(--wn-*)，保留 reset
│   └── themes/                  # 新增
│       ├── tokens.css           # 语义变量契约 + EP 变量映射（默认值）
│       ├── claude.css           # 9 套主题各一文件（[data-theme="x"]{...}）
│       ├── notion.css
│       ├── vercel.css
│       ├── stripe.css
│       ├── starbucks.css
│       ├── linear.css           # 暗色：含 .dark 覆盖
│       ├── spotify.css
│       ├── supabase.css
│       ├── sentry.css
│       └── index.css            # @import 汇总（main.js 引入）
├── config/
│   └── themes.js                # 新增：主题清单元数据（key/名称/明暗/预览色板）
├── stores/
│   └── theme.js                 # 新增：当前主题 + 切换 + 持久化 + applyTheme()
├── components/
│   └── common/
│       └── ThemeSwitcher.vue    # 新增：主题切换器（按钮 + 弹层九宫格预览）
└── main.js                      # 改：引入 themes/index.css + 初始化 themeStore

frontend/index.html              # 改：内联防闪烁脚本
frontend/src/components/layout/AppHeader.vue  # 改：放置 ThemeSwitcher 入口
```

### 5.3 切换入口设计

- **主入口（需求指定）**：主页可见的切换按钮。建议放在**导航栏右侧**（`AppHeader.vue` 的 `.nav-right`，登录入口旁），全站可见、符合「主页有按钮」的要求。
- **交互**：点击弹出**九宫格主题面板**，每格显示 主题名 + 3~4 色色板小样 + 明/暗标记，当前主题高亮；点击即时应用并持久化。
- **可选增强**：暗色/浅色一键切换的快捷图标；`prefers-color-scheme` 首次访问跟随系统选默认明暗。

---

## 六、分阶段任务（Epic 拆解）

### Epic 9.1：设计令牌基座（P0，约 1 sprint）
- [ ] 定义语义令牌契约 `themes/tokens.css`：颜色（primary/canvas/surface/surface-soft/text/text-muted/border/link/success/warning/error/on-primary）、圆角、阴影、字体族、间距。
- [ ] 建立 `--wn-*` → `--el-*` 映射，验证 EP 按钮/输入/弹窗/下拉随变量变化。
- [ ] 引入 EP 暗色变量 `element-plus/theme-chalk/dark/css-vars.css`，跑通 `html.dark` 暗色基底。
- [ ] `index.html` 内联防闪烁脚本；`main.js` 引入 `themes/index.css`。

### Epic 9.2：主题状态与切换器（P0，约 0.5 sprint）
- [ ] `config/themes.js`：9 套主题元数据（key、显示名、明/暗、预览色板）。
- [ ] `stores/theme.js`：`currentTheme`、`setTheme()`、`applyTheme()`（写 `data-theme` + 切 `dark` class）、`localStorage` 持久化、`initTheme()`。
- [ ] `ThemeSwitcher.vue`：九宫格预览面板 + 当前高亮 + 即时切换。
- [ ] 接入 `AppHeader.vue` 导航栏右侧；`main.js`/`App.vue` 启动时 `initTheme()`。

### Epic 9.3：9 套主题令牌落地（P1，约 1.5 sprint）
- [ ] 从仓库逐套取 `DESIGN.md`，把 YAML token 转为 `themes/<key>.css` 的 `[data-theme]` 覆盖（颜色/圆角/字体/阴影）。
- [ ] 浅色 5 套：claude、notion、vercel、stripe、starbucks。
- [ ] 暗色 4 套：linear、spotify、supabase、sentry（含 `.dark` 适配）。
- [ ] 字体策略：品牌字用「描述里的替代开源字体」（如 Claude 衬线→Cormorant/EB Garamond，Vercel→Inter 近似 Geist），中文回退 `PingFang SC/Microsoft YaHei`，避免版权字体缺失。
- [ ] 每套主题做明暗对比度自查（正文文本 ≥ WCAG AA 4.5:1），不达标微调中性色。

### Epic 9.4：现有界面令牌化迁移（P1，约 1.5 sprint）
> 把硬编码样式改为消费 `--wn-*`，是工作量主体，按「可见优先级」推进。
- [ ] 核心骨架：`main.css`、`App.vue`、`AppHeader.vue`、`AppFooter.vue`。
- [ ] 首页相关：`Home.vue`、`ArticleList.vue`、`ArticleCard.vue`、`Sidebar.vue`、`Pagination.vue`、`EmptyState.vue`。
- [ ] 详情与表单：`ArticleDetail.vue`、`Login/Register.vue`、`WriteArticle.vue`（含 UEditor 容器壳层，编辑器内部样式列为已知限制）。
- [ ] 其余视图：`Category/Search/UserCenter/MathTraining/NotFound` 及 `admin/`、`user/` 子目录。
- [ ] 缩略图 SVG 占位的取色改用主题色板（`ArticleCard.vue` 的 `colors[]`）。

### Epic 9.5：打磨、验证与文档（P2，约 0.5 sprint）
- [ ] 9 套 × 关键页面（首页/详情/登录弹窗/后台）逐一目检，修边界（弹窗遮罩、表格、富文本壳）。
- [ ] 切换过渡：根节点加 `transition: background-color/color .2s`，避免生硬跳变。
- [ ] 移动端在 2~3 套主题下抽检断点。
- [ ] Vitest：`themeStore` 用例（默认值、setTheme、持久化、applyTheme 对 DOM 的副作用）；`ThemeSwitcher` 渲染与切换交互。
- [ ] `npm run build` 通过；新增 `docs/前端主题体系.md`（如何新增第 10 套主题：复制 DESIGN.md → 填 `<key>.css` → 注册 `themes.js`）。

---

## 七、优先级与建议节奏

```
Sprint 1: Epic 9.1（令牌基座）+ Epic 9.2（状态/切换器）   ← 先把「换肤管道」打通
Sprint 2: Epic 9.3（9 套令牌落地）+ Epic 9.4 起步（核心骨架迁移）
Sprint 3: Epic 9.4 完成（全量视图迁移）+ Epic 9.5（打磨/测试/文档）
```

**建议起点**：Epic 9.1 的 `tokens.css` + EP 变量映射 —— 这是一切的地基，且可用「Claude + Linear 两套」先验证浅/暗双轨打通，再批量复制其余 7 套。

**最小可演示里程碑（MVP）**：9.1 + 9.2 + 9.3 仅做 claude/linear 两套 → 主页按钮已能在「暖调浅色 ↔ 深邃暗色」间切换，需求骨架即可演示，再逐步补齐到 9 套与全量迁移。

---

## 八、验收标准

| Epic | 验收 |
|------|------|
| 9.1 | 改 `<html data-theme>` 即整页换色；EP 按钮/输入/弹窗随主题变；`html.dark` 暗色基底正常；首屏无白闪 |
| 9.2 | 导航栏可见切换按钮；点击弹九宫格；选中即时生效；刷新后保持（localStorage） |
| 9.3 | 9 套主题均可选且视觉区分明显；正文对比度达 WCAG AA；无版权字体导致的 tofu/回退错乱 |
| 9.4 | 首页/详情/登录/后台无残留硬编码色（抽查关键文件）；切任意主题不破版 |
| 9.5 | 9 套 × 关键页目检通过；`vitest` 新增用例通过；`npm run build` 成功；主题文档可指导新增第 10 套 |

---

## 九、风险与对策

| 风险 | 说明 | 对策 |
|------|------|------|
| 迁移工作量大 | 硬编码色遍布多视图 | 按可见优先级分批；先核心骨架可演示，再全量 |
| 版权字体缺失 | Copernicus/Geist/Circular 等非公开 web 字体 | 一律用 DESIGN.md 文档给出的开源替代 + 中文系统字体回退 |
| 暗色对比度 | 暗色主题文本/边框易偏灰 | 每套过 AA 自查，必要时上调中性色亮度 |
| 富文本(UEditor) | 编辑器内部样式不在 Vue 作用域 | 仅令牌化其外层容器；编辑器内部主题化列为已知限制/后续项 |
| EP 深度样式 | 部分 EP 组件需 `:deep()` 覆盖 | 集中在 `tokens.css` 用 `--el-*` 映射，减少散落 `:deep()` |
| 切换闪烁 | 异步应用导致先白后变 | `index.html` 内联同步脚本在首屏前定好主题 |

---

## 十、范围确认（明确边界）

- ✅ 含：令牌体系、9 套主题、主页切换入口、现有视图令牌化迁移、主题持久化、测试与文档。
- ❌ 不含：后端改动（纯前端迭代）；新业务功能；富文本编辑器**内部**深度主题化（仅壳层）；像素级 1:1 复刻各品牌（取其设计语言/令牌，非抄袭其页面与 logo）。
- ⚠️ 版权：仅使用各 DESIGN.md 的**设计令牌**（公开 CSS 数值）与开源替代字体，不使用品牌专有字体与 logo，不声称与原品牌关联。

---

## 十一、BMad 工作流衔接

本方案为规划产物。建议后续按 BMad 流程推进（每个 skill 在全新对话窗口运行）：

1. `[CU]` **Create UX**（`bmad-ux`）：若想先把切换器交互、九宫格预览与令牌语义体系设计成正式 UX 规格，再实现。
2. `[SP]` **Sprint Planning**（`bmad-sprint-planning`）：把 9.1~9.5 五个 Epic 拆为可执行故事。
3. `[CS]` **Create Story** → `[DS]` **Dev Story** → `[CR]` **Code Review**：逐故事实现。
4. 或用 `[QQ]` **Quick Dev**（`bmad-quick-dev`）单点突破：建议先做 Epic 9.1 + 9.2 + claude/linear 两套，打通端到端「主页按钮换肤」MVP。

---

## 附录 A：语义令牌契约草案（tokens.css 雏形）

```css
/* themes/tokens.css —— 所有组件只消费这些变量 */
:root {
  /* 颜色 */
  --wn-color-primary:        #cc785c;
  --wn-color-primary-hover:  #a9583e;
  --wn-color-on-primary:     #ffffff;
  --wn-color-canvas:         #faf9f5;  /* 页面底色 */
  --wn-color-surface:        #ffffff;  /* 卡片/弹层 */
  --wn-color-surface-soft:   #f5f0e8;
  --wn-color-text:           #141413;
  --wn-color-text-muted:     #6c6a64;
  --wn-color-border:         #e6dfd8;
  --wn-color-link:           var(--wn-color-primary);
  --wn-color-success:        #5db872;
  --wn-color-warning:        #d4a017;
  --wn-color-error:          #c64545;
  /* 圆角 */
  --wn-radius-sm: 6px;
  --wn-radius-md: 8px;
  --wn-radius-lg: 12px;
  /* 阴影 */
  --wn-shadow-card: 0 2px 12px rgba(0,0,0,.08);
  /* 字体 */
  --wn-font-display: "Cormorant Garamond", "Songti SC", serif;
  --wn-font-body: Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif;

  /* —— 打通 Element Plus —— */
  --el-color-primary: var(--wn-color-primary);
  --el-bg-color: var(--wn-color-surface);
  --el-text-color-primary: var(--wn-color-text);
  --el-text-color-regular: var(--wn-color-text-muted);
  --el-border-color: var(--wn-color-border);
}

/* 主题覆盖示例：Linear（暗） */
[data-theme="linear"] {
  --wn-color-primary: #5e6ad2;
  --wn-color-canvas:  #010102;
  --wn-color-surface: #0f1011;
  --wn-color-text:    #f7f8f8;
  --wn-color-text-muted: #8a8f98;
  --wn-color-border:  #23252a;
  --wn-font-display: "Inter", system-ui, sans-serif;
}
```

## 附录 B：themeStore 行为草案

```js
// stores/theme.js（行为示意，非最终代码）
// state: currentTheme（默认 'claude'）
// setTheme(key): 校验 → currentTheme=key → applyTheme() → localStorage 持久化
// applyTheme(): document.documentElement.setAttribute('data-theme', key)
//               并按 themes[key].dark 切换 html 'dark' class
// initTheme(): 从 localStorage 读取（无则默认/跟随 prefers-color-scheme）→ applyTheme()
```

---

## 十二、实施记录（迭代 9 执行结果）

> 执行日期：2026-05-30 · 前端 `vitest` 23/23 通过（新增 10），`npm run build` 成功，关键文件 `getDiagnostics` 无报错。

### Epic 9.1 — 设计令牌基座 ✅

- 新增 `src/assets/themes/tokens.css`：语义令牌契约（`--wn-color-*` / `--wn-radius-*` / `--wn-shadow-*` / `--wn-font-*`）+ 含默认值（防 FOUC）。
- 建立 `--wn-*` → Element Plus `--el-*` 映射（主色及 light-3/5/7/8/9 用 `color-mix` 从主色+表面推导，自动适配明暗；背景/文本/边框/填充/圆角/阴影全覆盖），挂在 `html[data-theme]`（特异度 0,1,1）以覆盖 EP 默认与暗色 css-vars。
- `src/assets/themes/index.css` 统一 `@import`，含 `element-plus/theme-chalk/dark/css-vars.css` 暗色基底。
- `index.html` 注入首屏防闪烁内联脚本（同步读 localStorage/系统偏好设 `data-theme`/`dark`）。
- `main.js` 引入 `themes/index.css`，挂载前 `useThemeStore(pinia).initTheme()`。

### Epic 9.2 — 主题状态与切换器 ✅

- `src/config/themes.js`：9 套主题元数据（key/名称/描述/明暗/色板）、`DEFAULT_THEME='claude'`、`THEME_STORAGE_KEY='wn-theme'`、`getThemeMeta()`。
- `src/stores/theme.js`：`currentTheme`/`themes` state，`currentMeta`/`isDark` getters，`initTheme()`/`setTheme()` actions，导出纯函数 `applyThemeToDom()`（设 `data-theme` + 切 `dark` class），localStorage 持久化，首次访问按 `prefers-color-scheme` 选默认。
- `src/components/common/ThemeSwitcher.vue`：导航栏「主题」入口 + `el-popover` 九宫格预览面板（色板小样/名称/明暗标记/当前高亮/即时切换）。
- 接入 `AppHeader.vue` 导航栏右侧 `.nav-right`（全站可见，满足「主页有按钮」）。

### Epic 9.3 — 9 套主题令牌落地 ✅

浅色 5：`claude`、`notion`、`vercel`、`stripe`、`starbucks`；暗色 4：`linear`、`spotify`、`supabase`、`sentry`（均 `color-scheme` 标注，暗色配 `dark` class）。令牌均取自各 `DESIGN.md` 实测值。品牌专有字体用开源替代（Cormorant/EB Garamond、Inter≈Geist、Rubik 等）+ 中文 `PingFang SC/Microsoft YaHei` 回退。

### Epic 9.4 — 现有界面令牌化迁移 ✅

将硬编码色/卡片阴影/卡片圆角改为消费 `--wn-*`，覆盖：
- 骨架：`main.css`、`App.vue`(原已简洁)、`AppHeader.vue`（导航/登录弹窗/输入框）、`AppFooter.vue`。
- 首页相关：`Home.vue`、`ArticleList.vue`、`ArticleCard.vue`、`Sidebar.vue`、`Pagination.vue`。
- 详情/表单：`ArticleDetail.vue`（含代码块、表格、评论、楼中楼）、`Login.vue`、`Register.vue`、`WriteArticle.vue`、`UEditor.vue`(容器壳层)、`PdfViewer.vue`(chrome)。
- 其余视图：`Category.vue`、`Search.vue`、`NotFound.vue`、`UserCenter.vue`、`MathTraining.vue`、`admin/AdminDashboard.vue`、`user/{MyArticles,MyDrafts,MyComments,MyCredits,MyFavorites,Profile}.vue`。
- 渐变头图（UserCenter/Login/Register/MyCredits）改为 `linear-gradient(135deg, var(--wn-color-primary), var(--wn-color-primary-active))` 随主题走；浅色 tint 块（MathTraining 状态图标、反馈框）改用 `color-mix` 适配暗色。

> 保留为字面量（非主题色，状态/占位用途）：`ArticleCard` SVG 占位取色数组、`AdminDashboard`/`MathTraining` 进度条与仪表盘阈值色、彩色徽章上的白字、PDF 阅读区 `#525252` 背景与白色页面 canvas。

### Epic 9.5 — 打磨、验证与文档 ✅

- `tokens.css` 给 `html,body` 加 `transition: background-color/color .25s`，切换平滑。
- 测试：`stores/theme.spec.js`（7）+ `components/common/ThemeSwitcher.spec.js`（3）；`npm test` **23/23 通过**。
- 文档：新增 `docs/前端主题体系.md`（架构、令牌清单、新增第 10 套主题步骤、已知限制）。

### 验证方式

- 前端：`npm run build` 成功；`npm test` 23/23。
- 诊断：`theme.js`/`themes.js`/`ThemeSwitcher.vue`/`main.js`/`AppHeader.vue` 无报错。
- 残留硬编码扫描：仅余上述「保留为字面量」的状态/占位色。

### 完成度

- 需求「选 9 套不同风格 + 主页切换按钮」**已全部落地**（9 套全部实现，非仅两套）。
- 切换即时生效 + localStorage 持久化 + 首屏防闪烁 + 跟随系统明暗默认。

### 后续可选项（非阻塞）

- ~~富文本编辑器内部（iframe）深度主题化。~~ → **已补做，见下「补充：UEditor 编辑区主题化」**
- 大 chunk 体积优化（与迭代 8 遗留同）。
- 9 套 × 各页面的人工逐页目检（构建/测试已过，建议上线前抽检暗色对比度）。

### 补充：UEditor 编辑区 iframe 主题化 ✅

> 执行日期：2026-05-30 · 解除迭代 9 原「已知限制」第 1 条。

UEditor 编辑区是同源 iframe，父页面 CSS 无法穿透。改造方案（`components/editor/UEditor.vue`）：
- 新增 `applyEditorTheme()`：从父页面 `getComputedStyle(documentElement)` 读取当前主题的 `--wn-*` 实测值，往 `editor.document.head` 注入 `<style id="wn-editor-theme">`，覆盖编辑区 `html/body/a/p/pre/code/table/blockquote` 等的背景与文字色；同时同步 `editor.iframe` 外层底色。
- 时机：`editor.ready` 时首次注入；`watch(themeStore.currentTheme)` 在切换主题时刷新；`contentChange` 时若检测到注入样式丢失（切源码模式/`setContent` 可能重建 iframe 文档）则补回。
- 工具栏：新增 `--wn-editor-icon-filter` 令牌，浅色主题为 `none`，4 套暗色主题为 `invert(0.85) hue-rotate(180deg)`，使 UEditor 单色 sprite 图标在暗色工具栏下可读；并令牌化工具栏/状态栏/iframeholder 背景与边框。

验证：`npm run build` 成功；`npm test` 23/23；`UEditor.vue` 无诊断报错；UEditor 静态资源（`public/ueditor/`）齐备。

> 残留说明：图标反色用 CSS filter 近似处理（UEditor 自带位图 sprite，非矢量），暗色下观感可接受但非像素级完美；如需完美可后续替换为矢量图标集。
