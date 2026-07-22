---
name: margin-trading-wechat-long-image
description: "为国泰海通融资融券公众号生成自适应长图 PNG 和可一键复制到微信公众号正文编辑器的兼容富文本 HTML；当用户提到‘给融资融券公众号做长图’‘两融聚焦长图’或‘融资融券公众号市场概览’时使用。内容结构由任务提示词和来源文件决定，每份正式产物必须使用 Skill 自带的官方完整横版 Logo、融资融券公众号二维码、固定色板和合规文案。仅限该品牌与渠道场景，普通财报、通用数据看板或其他公众号内容不要使用。"
---

# 国泰海通微信公众号长图

从同一份来源生成一组同序号产物：1080px 宽的自适应公众号长图 HTML/PNG，以及可复制到微信公众号正文编辑器的兼容富文本 HTML。两种呈现使用相同事实、品牌素材和合规文字。

## 内容决策边界

- 以任务提示词和来源文件作为内容结构的唯一依据。由提示词决定标题、板块数量、板块名称、顺序、每部分内容，以及是否使用表格、图表、榜单、KPI、摘要或结论。
- 不在本 Skill 中预设、补充或推断任何内容板块。提示词没有要求表格或图表时，不要自行添加；来源不支持的事实不要编造。
- 只把 `assets/example.html` 和 `assets/example-richtext.html` 当作中性品牌骨架、排版和微信兼容参考。示例中的占位标题、占位内容容器和布局不得覆盖任务提示词；任务提示词给出的精确结构和呈现要求优先。
- 不得照搬示例中的占位文字，也不得从示例推断日期、数据、标题、板块名称、板块数量、图表类型、表格结构或阅读顺序。
- 本 Skill 只约束国泰海通品牌、微信公众号渠道、基础视觉系统、输出格式和兼容性。

## 工作流

1. 读取任务提示词和全部来源文件，先按提示词确定内容结构。
2. 有界检查两个示例和两张品牌图片；不要把示例内容当作输出要求或事实来源。
3. 选择下一个未占用的三位序号 `<seq>`，生成 `html/<seq>.html`，按 `#image-root` 的实际内容高度渲染为 `png/<seq>.png`。
4. 使用相同事实和 `<seq>` 生成 `richtext/<seq>.html`，将长图内容重新映射为微信兼容的移动端单栏富文本，不要机械缩放长图 HTML。
5. 运行 `python <skill_dir>/scripts/validate_wechat_richtext.py richtext/<seq>.html` 并修复全部错误。
6. 查看实际 PNG 和约 390px 宽的富文本预览，点击一次复制按钮；确认文字清晰、无裁切或横向溢出、Logo 不变形、二维码完整可扫。

## 国泰海通品牌与合规

- 长图和富文本都必须同时使用 `assets/gtja-logo.png` 与 `assets/gtja-qrcode.jpg`。不得使用文字代替、重绘、替换、裁切、拆分、拉伸或遗漏任一素材。
- 将完整横版 Logo 作为一个整体居中展示并保持原始宽高比。该图片已经包含“国泰海通”和“GUOTAI HAITONG”，不得在品牌头部再次单独排印这两行文字。
- 二维码居中展示，保留完整白色静区，不加蒙层、不与其他元素重叠，并保持可扫码。二维码附近逐字使用引导语“扫码关注国泰海通融资融券公众号 获取更多两融信息资讯”。
- 在两份产物中逐字放入以下两段文字，不得删改：

  “免责声明：本文内容均基于客观市场行情交易数据产生，数据来源于证券交易所官网公开数据，文中内容不构成任何投资建议，市场有风险，投资需谨慎。”

  “风险提示：融资融券交易有风险，投资者在参与融资融券交易前请务必阅读、了解和掌握有关法律法规和交易所、证券登记结算机构业务规则等相关规则和《风险揭示书》。”

## 长图视觉基线

- 默认使用 1080px 宽的公众号竖版信息流；高度由内容和普通文档流自然撑开。不要预设总高度、最短高度或最长高度，不要为凑尺寸添加空白、压缩内容或裁切板块。
- 固定使用以下业务色板：页面背景 `#f0f7ff`、主标题深蓝 `#003377`、主级标题栏 `#103480`、次级标题栏 `#33a0e8`、表头底色 `#eeeeee`、合规区底色 `#f3efff`、正向/流入/上涨 `#e6212a`、负向/流出/下跌 `#239947`。白色作为主要内容容器底色；不得用近似色替换这些语义色。
- 中国市场方向必须按实际数值动态映射：正值使用红色和 `▲`，负值使用绿色和 `▼`；零值或方向不明时使用中性色且不添加误导性箭头。不得把示例数据的方向当作固定方向。
- 中文使用 PingFang SC、Microsoft YaHei 等系统字体；数字可使用 Roboto、DIN Alternate 或等宽数字特性。禁止远程字体。
- 使用清晰字号层级、圆角、留白和克制阴影。品牌区、主标题、板块标题、关键数字和二维码居中；叙述正文与合规文案左对齐；表格表头和数据单元格居中。按提示词给出的内容密度调整间距，不得用固定高度、`overflow:hidden` 或省略号隐藏重要内容。
- 长图 HTML 必须自包含，使用内联 CSS，不依赖 CDN、远程图片、远程字体或远程脚本。

## 微信公众号兼容富文本

### 复制边界

- 页面必须包含 `#copy-richtext` 按钮和 `#wechat-richtext` 容器。按钮只复制容器的 `innerHTML` 与 `innerText`，分别写入剪贴板的 `text/html` 和 `text/plain`，并保留 `document.execCommand('copy')` 回退逻辑。
- 工具栏、状态提示、页面级 `<style>` 和复制脚本必须位于 `#wechat-richtext` 外；复制片段中不得出现这些内容。
- `#wechat-richtext` 预览宽度不得超过 677px；内部根节点使用 `display:block;width:100%` 和单栏普通文档流。

### 兼容性与排版

- 复制片段内部只使用语义 HTML、HTML 宽高/对齐属性和逐元素 `style`。禁止 `<style>`、`class`、内部 `id`、CSS 变量、伪元素、媒体查询、外部样式表和依赖选择器的样式。
- 禁止 `flex`、`grid`、绝对/固定/粘性定位、transform 布局、渐变背景、背景图、canvas、iframe 和交互组件。SVG 或复杂 CSS 图表如经提示词要求使用，先栅格化为 PNG 再嵌入。
- 所有图片使用 `data:image/...` URI；同时写正整数 `width` 属性、内联像素宽度和 `height:auto!important`。Logo 使用 `data-brand-asset="logo"`，二维码使用 `data-brand-asset="qrcode"`。
- 正文基准使用 15px 字号和约 1.65 行高；板块标题使用约 20px、加粗、居中。关键颜色和对齐直接写在对应元素上，不依赖父级继承。
- 数据表不是必需内容。仅当提示词要求并实际使用数据表时，设置 `width:100%`、`border-collapse:collapse`、`border-spacing:0` 和 `table-layout:auto`；`th` 使用 12px、`td` 使用 13px，并同时写 `align="center"`、`valign="middle"`、`text-align:center` 和 `vertical-align:middle`。约 390px 视口不得横向溢出。

## 大文件与素材处理

- 不要直接读取含大段 base64 的 `assets/example-richtext.html`。先折叠 data URI 并限制超长行：

```bash
sed -E 's#data:image/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+#DATA_URI_ELIDED#g' \
  <skill_dir>/assets/example-richtext.html | cut -c1-300
```

- 生成长 HTML 时先按提示词定义的板块分段写入骨架，以 `LOGO_URI_PLACEHOLDER` 和 `QRCODE_URI_PLACEHOLDER` 占位，再用本地脚本读取品牌文件并替换为 data URI。不要让 base64 经过模型输出，也不要一次性重写整份大文件。
- 注入后确认两种占位符均已消失，再运行富文本 validator。

## 输出约束

- 每次正式运行输出 `html/<seq>.html`、`png/<seq>.png` 和 `richtext/<seq>.html`，三者使用同一未占用序号且不得覆盖已有文件。
- 长图 HTML 只保留一个交付根元素：`<main id="image-root" data-html-anything-skill="margin-trading-wechat-long-image">`；`#image-root` 默认宽 1080px，高度由内容自然计算。Logo 和二维码都编码为 data URI。
- 富文本 HTML 是独立自包含文档，不包含 `#image-root`，必须包含复制外壳和通过校验的 `#wechat-richtext` 片段。
- 最终报告 `html_path`、`png_path`、`richtext_path`、PNG 尺寸、视觉 QA 和富文本校验状态。只有三个文件非空、validator 返回 `"valid": true`、两份产物都能看到 Logo 和二维码、二维码可扫码且没有遗留占位符时，才能报告成功。

## Assets

- Long-image visual reference: `assets/example.html`
- WeChat rich-text compatibility reference: `assets/example-richtext.html`
- Required official wide Logo: `assets/gtja-logo.png`
- Required official QR code: `assets/gtja-qrcode.jpg`
- WeChat rich-text validator: `scripts/validate_wechat_richtext.py`
- 保持两张品牌图片原样；把两个 HTML 示例当作不含业务结构约束的中性视觉与兼容性基线，而不是内容模板。
