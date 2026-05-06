# 前端复刻实现清单

## 第一阶段：Shell 框架

- [ ] 建立全屏黑底 terminal shell。
- [ ] 固定顶部 function key bar。
- [ ] 固定顶部 market ticker。
- [ ] 建立桌面左侧 icon rail。
- [ ] 建立桌面右侧 information rail。
- [ ] 建立底部 status bar。
- [ ] 移动端隐藏左/右 rail，改为 hamburger drawer 和主内容优先。

## 第二阶段：视觉 tokens

- [ ] 字体：IBM Plex Mono, Courier New, monospace。
- [ ] 背景：纯黑或接近纯黑。
- [ ] 主文字：米白。
- [ ] 强调色：终端橙。
- [ ] 涨跌：绿/红。
- [ ] 状态：cyan/green。
- [ ] 边框：1px 暗棕或橙色。
- [ ] 圆角：尽量 0-2px，避免 SaaS 卡片圆角。

## 第三阶段：核心组件

- [ ] FunctionKeyButton。
- [ ] IconRailButton。
- [ ] MarketTickerTape。
- [ ] TerminalStatusBar。
- [ ] RightRailNews。
- [ ] WatchlistMiniTable。
- [ ] Sparkline。
- [ ] MetricCard。
- [ ] DenseDataTable。
- [ ] SegmentedControl。
- [ ] AgentComposer。
- [ ] EmptyStatePanel。
- [ ] NewsFeedList。
- [ ] SettingsTabs。
- [ ] CreditPackCard。

## 第四阶段：页面

- [ ] Dashboard。
- [ ] Markets。
- [ ] Watchlist empty state。
- [ ] Portfolio empty state。
- [ ] News。
- [ ] Economics。
- [ ] Research。
- [ ] Agentic World placeholder/workspace。
- [ ] Fund Managers。
- [ ] Dataroom。
- [ ] Plans & Credits。
- [ ] History empty state。
- [ ] Alerts empty state。
- [ ] Settings with mock profile data。

## 第五阶段：可访问性和交互修正

- [ ] F1-F8 使用原生 button，不用 span role button。
- [ ] 所有 icon-only button 增加 `aria-label`。
- [ ] 搜索框和 textarea 增加 label 或 `aria-label`。
- [ ] 移动端点击目标高度至少 40px。
- [ ] 键盘支持 Enter/Space 激活导航按钮。
- [ ] 当前页面用 `aria-current` 或明确 selected 状态。
- [ ] tab 组件使用正确 `tablist`、`tab`、`tabpanel` 语义。

## 第六阶段：验证

- [ ] 桌面 1700 x 900 截图对齐。
- [ ] 移动 390 x 844 截图对齐。
- [ ] 页面无横向溢出。
- [ ] 右侧 rail 在桌面固定，在移动端折叠。
- [ ] 所有空状态与截图一致。
- [ ] mock 数据更新不会撑破表格、按钮或状态栏。

