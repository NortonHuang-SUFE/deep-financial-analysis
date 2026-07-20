---
name: margin-trading-wechat-long-image
zh_name: "两融公众号长图"
en_name: "Margin Trading WeChat Long Image"
emoji: "📊"
description: "为国泰海通融资融券公众号生成‘两融聚焦’长图和融资融券市场数据看板；当用户提到‘给融资融券公众号做长图’‘两融聚焦长图’或‘融资融券公众号市场概览’时使用。仅限该品牌与渠道场景，普通财报、通用数据看板或其他公众号内容不要使用。"
category: finance
scenario: finance
aspect_hint: "1080px 宽竖版公众号长图，高度随内容自适应"
tags: ["融资融券", "两融", "公众号", "长图", "国泰海通"]
---

# 两融公众号长图

生成国泰海通融资融券公众号专用的“两融聚焦”券商数据长图。保持品牌视觉、合规内容和中国市场颜色语义一致，同时根据来源内容自由组织信息结构。

## 工作流

1. 读取用户提供的来源文件和全部品牌素材；不得仅根据任务摘要编造数据。
2. 先检查 `assets/example.html`，把它作为品牌视觉、排版节奏和可复用组件的参考，而不是必须逐项复刻的固定模板。
3. 分析来源内容的数量、层级和阅读密度，先选择合适的组件，再由实际排版自然决定长图高度。默认宽度为 1080px；除非用户明确指定，否则不要预设总高度、最短高度或最长高度，也不要为凑尺寸添加空白、压缩内容或裁切模块。
4. 根据内容自由添加、合并、拆分、排序或省略模块。表格、折线图、柱状图、面积图、迷你图、KPI 卡、色块、重点结论、标签、分隔带和说明文字都可以在本视觉框架内使用；不要求固定模块数量、固定图表类型、固定表格列数或固定榜单行数。
5. 来源缺少已核验数值或用户要求模板时，使用 `——`、`***.**`、`+***.**`、`-***.**` 等占位符，不得补造行情。
   未核验榜单名称、排序或涨跌方向时，使用中性示例名称与 `——`，不得根据示例折线或颜色推断真实方向。
6. 生成单个自包含 HTML，并按 `#image-root` 的实际内容高度渲染、查看 PNG；修复裁切、重叠、过小文字、Logo 变形、宽版品牌标识模糊、信息断层和表格拥挤后再交付。

## 画布与视觉系统

- 默认使用 1080px 宽的公众号竖版信息流；总高度必须由内容自然撑开，不设置固定像素高度。内容较少时保持简洁，内容较多时继续向下延展。
- 用户明确指定其他宽度或媒介尺寸时可以调整，但仍应保留竖向阅读逻辑，避免直接套用横版、16:9 或桌面仪表板布局。
- 使用冰蓝到浅薰衣草渐变背景、白色大卡片、深蓝 `#1E4D8C`、亮青 `#31B7E9`、克制紫色 `#5A42F5` 和品牌金 `#C9A96E`。
- 卡片可参考 24px 左右圆角、40–50px 内边距和柔和蓝灰阴影；允许根据内容密度调整卡片尺寸、留白和模块间距。
- 主卡可使用青蓝到紫色渐变标题签、金色小标、色块标题或其他同体系的分区方式，形成清晰的连续竖向阅读节奏，不要求所有模块使用完全相同的标题结构。
- 承载标题、正文、表格或图表说明的容器优先使用 `auto`、`min-height`、内边距和自然换行。除 Logo、宽版品牌标识、装饰图形等尺寸明确的素材外，不要为匹配示例而对内容容器写死高度，也不要用 `overflow: hidden` 或省略号隐藏重要信息。
- 中文使用 PingFang SC 等系统字体；数字使用 Roboto、DIN Alternate 或等宽数字特性，不加载远程字体。
- 中国市场统一红涨 `#E53E3E`、绿跌 `#2F9E44`；上涨使用 `▲`，下跌使用 `▼`。
- `assets/example.html` 同时展示红涨和绿跌仅用于说明视觉语义，不代表真实市场方向。

## 品牌锚点与可选组件

以下内容是每个正式输出必须保留的品牌与合规锚点：

- 使用真实紧凑版 Logo `gtja-logo.png`，不得重绘、拉伸、裁切、替换或省略。
- 使用真实宽版品牌标识 `gtja-brand-lockup.png`，保持原始宽高比并完整展示，不得重绘、拉伸、裁切、替换或省略。
- 逐字放入以下两段免责声明，不得删改：

  “免责声明：本文内容均是基于客观市场行情交易数据产生，数据均来源于证券交易所官网公开数据，文中内容不构成任何投资建议，市场有风险，投资需谨慎。”

  “风险提示：融资融券交易有风险，投资者在参与融资融券交易前请务必阅读、了解和掌握有关法律法规和交易所、证券登记结算机构业务规则等相关规则和《风险揭示书》。”

- 红涨绿跌、占位符、数据来源和事实准确性遵守本 Skill 的统一规则。

除上述锚点外，内容结构按来源自由设计。可选组件包括但不限于：

- Hero、主标题、副标题、日期、摘要条和栏目导航；
- 融资融券余额、融资余额、融券余额等 KPI 卡片；
- 行业、个股、ETF 或其他维度的表格与排行榜；
- 折线图、柱状图、面积图、组合图、迷你趋势图和图例；
- 洞察结论、数字强调、色块、标签、药丸、提示卡、分隔带、方法说明和数据来源。

可按来源增减榜单组、行列和图表，或将多个主题合并为一张卡片；不要为了匹配示例而展示没有来源支撑的模块。宽版品牌标识和免责声明通常放在信息流底部，其他模块的顺序由阅读逻辑决定。

## 输出约束

- 输出完整 HTML 文档，内联 CSS，禁止 CDN、远程图片、远程字体和远程脚本。
- 只保留一个交付根元素：`<main id="image-root" data-html-anything-skill="margin-trading-wechat-long-image">`。
- 示例允许相对引用同目录素材；将最终 HTML 写到其他目录时，把紧凑版 Logo 和宽版品牌标识编码为 data URI，使 HTML 可独立渲染。
- `#image-root` 默认设置 `width: 1080px`，高度使用 `auto` 或由普通文档流自然计算；不要为根元素写死总高度。
- 可保留表格 hover 样式，但以静态截图完整可读、微信缩放后仍有清晰层级为首要目标。

## Assets

- Example HTML: `assets/example.html`
- Required compact logo: `assets/gtja-logo.png`
- Required wide brand lockup: `assets/gtja-brand-lockup.png`
- After reading this `SKILL.md`, inspect `assets/example.html` in bounded slices before writing HTML. Treat it as a component library, visual quality bar, and implementation reference for layout rhythm, typography scale, spacing, palette, and export-ready patterns. Its section count, row count, chart choice, composition, and rendered height are examples rather than output requirements.
- Inspect both required images before generating. Include both in every output, preserve their full frames and original aspect ratios, and do not replace, redraw, omit, or substitute either asset.
