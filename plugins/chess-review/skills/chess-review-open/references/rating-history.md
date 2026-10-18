# 可选的 Chess.com 评分成长趋势

用户要求跟踪历史评分时，可通过官方公开只读 API 同步历史对局。无需账号密码；不运行后台监控，也不由浏览器请求接口。

在用户的复盘输出目录创建 `.chess-review-ratings.json`（本地配置，不复制到公开技能仓库）：

```json
{"username":"用户确认的账号","cache_dir":"用户指定的工作缓存目录"}
```

`username` 必须与成长档案的 `user` 匹配。已配置时，每次 `build_leaks.py 输出目录`（包括带 `--merge` 的复盘更新）顺序请求 archives、所有月度 archives 和 stats，然后把完整历史快照嵌入同一个成长 HTML。没有配置时不请求网络。`--export` 只导出；`--skip-rating-sync` 只适用于离线重建或测试，不可据此宣称更新了评分。

首次同步失败会停止构建；已有快照时，失败保留旧数据及其同步时间，并在页面明确显示本次同步未完成。只有全部请求成功才替换 cache/history.json，不把部分月份当完整历史。官方接口可能缓存延迟。

评分展示规则：

- 数据源为 https://www.chess.com/news/view/published-data-api 。游戏 white/black.rating 按官方文档为赛后评分，不从 PGN 推测或挪用下一盘分数。
- 按 end_time 排列；标准棋的 rapid、blitz、bullet、daily 独立展示。保留全部公开已完成对局数据，非标准变体、不计分对局不进入标准棋评分曲线。
- 当前评分来自各池 stats.last；区间变化为所选首末记录之差；历史最高只称“区间最高”，不等同 stats.best 或终身最高。
- 相邻记录差不保证全部来自一盘（调整和缓存会影响）；缺少评分不编造；结果未知时显示未知。
- 成长标签主要呈现评分趋势；原来的真实好棋与改善证据折叠保留，不能用单次好棋宣称长期进步。未配置评分时继续原来的证据页。
- 保留已有 #progress、#positive-section 深链接及默认常见漏洞标签。总入口可直达成长趋势。

验证：运行 tests/test_rating_history.py，完整 check_leaks.cjs，检查不同池/时间范围/空范围/窄屏/离线显示；确认旧案例、证据、单盘复盘和笔记键未变。首次整合或模板改变后做完整回归。
