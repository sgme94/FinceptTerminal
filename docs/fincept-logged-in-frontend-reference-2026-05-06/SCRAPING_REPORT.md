# 抓取报告

## browser-harness

用途：连接用户已登录的 Chrome，读取真实渲染后的 DOM、布局尺寸、交互控件、资源摘要，并截取桌面/移动截图。

结果文件：

- `data/browser-harness-dashboard-analysis.json`
- `data/browser-harness-settings-redacted.json`
- `screenshots/dashboard-desktop.png`
- `screenshots/dashboard-mobile.png`
- `screenshots/dashboard-mobile-menu.png`
- `screenshots/feature-*.png`

覆盖范围：

- Dashboard 桌面和移动端。
- 移动端菜单打开态。
- 14 个登录后功能入口。
- 结构化字段：URL、title、viewport、horizontalOverflow、headings、layoutCandidates、interactive、inputs、roleButtons、iconsOnly、smallTargets、tables、lists、styleSamples、resourceSummary。

关键结论：

- 登录态读取正常，`/dashboard` 没有跳转到 login。
- 桌面端无横向页面溢出。
- 移动端无页面级横向溢出，但控件触达面积偏小。
- 页面核心行情、新闻、watchlist 等依赖客户端渲染和接口数据。

## Scrapling

用途：保存静态 HTML、Markdown/text 抽取结果，以及 DynamicFetcher 的浏览器渲染抽取结果。

结果文件：

- `data/scrapling-dashboard-auth.html`
- `data/scrapling-dashboard-auth.md`
- `data/scrapling-dashboard-auth.txt`
- `data/scrapling-dashboard-dynamic-auth.md`
- `data/scrapling-home.md`

认证方式：

- 从已登录 Chrome 读取站点会话 cookie 作为临时请求头。
- cookie 仅用于本地 Scrapling 请求。
- 临时 cookie 文件已删除，参考包中未保存 cookie 值或 cookie 名。

抓取表现：

| 抽取方式 | 结果 |
| --- | --- |
| `scrapling extract get /dashboard` 带 cookie | 成功返回登录后初始 HTML |
| `scrapling extract get /dashboard` 不带 cookie | 会落到 login，符合预期 |
| `scrapling extract fetch /dashboard` 带 cookie header | 可抓到更多 hydrated 文本内容 |
| `scrapling extract get /` | 首页 SEO 和营销内容可正常抽取 |

限制：

- Scrapling 静态 GET 更适合保存 Next.js 初始 HTML 和基础文本。
- dashboard 的实时行情、新闻和交互态需要 browser-harness 真实浏览器确认。
- 市场价格、新闻标题、时间戳是实时数据，不应作为固定 mock 文案逐字复刻。

## 脱敏处理

已处理：

- 邮箱替换为 `[email]`。
- 用户名替换为 `[user]`。
- 手机号替换为 `[phone]`。
- 明显 credits 文本在文本文件中替换为 `###`。
- Settings 截图已重新捕获为脱敏版本。

保留：

- 市场行情示例。
- 新闻标题示例。
- 页面功能名称。
- 视觉状态文本，如 API operational、connection live。

## 复刻使用建议

- 用 browser-harness JSON 作为布局和组件来源。
- 用截图作为视觉校准来源。
- 用 Scrapling HTML 作为初始 DOM/SSR 结构参考。
- 用 DynamicFetcher Markdown 作为 hydrated 内容和文案密度参考。
- 复刻时使用 mock market data，不要依赖抓取时的实时数值。
