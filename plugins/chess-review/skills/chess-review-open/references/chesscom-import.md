# 用 Chess.com 用户名导入已结束棋局

用户说“review 最新一盘”且没有 PGN 时，先读取当前复盘目录 `.chess-review-account.json` 中已确认的用户名；没有记录才问一次 Chess.com 用户名。用户提供用户名并请求复盘，即授权本次只读抓取。不得硬编码开发者账号、询问密码或操作正在进行的对局。

## 仅连接用户名

用户只说“连接我的账号”时，使用 `--connect-only` 读取公开资料、确认用户名并保存到当前复盘目录。无需登录或密码，不自动开始分析。没有已完成棋局的新账号也可以先保存设置。

```sh
python "$SKILL_DIR/scripts/fetch_chesscom.py" chess-reviews --user CONFIRMED_USERNAME --connect-only
```

下次“帮我 review”再默认获取最新一盘。这里的连接是记住用户名并读取公开棋谱，不是 OAuth 登录或持续监控。

## 导入与继续复盘

```sh
python "$SKILL_DIR/scripts/fetch_chesscom.py" chess-reviews --user CONFIRMED_USERNAME
# 以后复用本地用户名，默认最新 1 盘：
python "$SKILL_DIR/scripts/fetch_chesscom.py" chess-reviews
# 用户明确要求多盘时（每批 1–5 盘）：
python "$SKILL_DIR/scripts/fetch_chesscom.py" chess-reviews --count 3
```

可传 `--timezone` 指定已确认的 IANA 时区；不推测所在地，未设置用 UTC 开始时间及原 PGN 日期。首次获取成功后用户名和时区存本地；切换账号用单独目录。这里的用户名是用户声明的复盘对象，不是账号登录认证。

脚本依次访问官方 archives 列表、从新到旧的月档案，默认最多查 6 个月档案、总体取数预算 120 秒，避免扫完全部历史。按 `end_time` 选最新已结束标准棋局，逐盘核对 PGN 合法性、账号与颜色。非标准变体单独列出，不把它们说成已复盘；明确描述获取的是“最新可获取的标准棋局”。需要搜索更多月份时，按用户范围调整 `--max-months`，不要自动扩展。

原始 PGN、源 JSON、各盘摘要和 `latest.json` 保存在所选目录的 `work/chesscom/`。这些是导入材料，**不是完成的复盘**。读取返回的 `games` 后继续 prepare → analyze → review.json → build → 浏览器检查 → 归档。不得以“已下载 PGN”结束用户的复盘任务。

- 简短告诉用户选中的日期、对手及其执子方，然后继续，不增加确认关卡。每盘颜色单独识别。
- 使用 `start_time`（由 PGN UTCDate/UTCTime 转换）命名本地日期，不把结束时间当作开始时间。
- `already_reviewed` 非空时，给出原有复盘入口；不悄悄换成更早的一盘。明确要求重新分析时才重做。
- 去重同时检查 Chess.com 游戏 ID 的不同 URL 写法，以及无链接棋谱的玩家/走法/日期。发现同 ID 不同棋谱或数据冲突时停止覆盖并核对。
- 用户指定日期、对手或某一局时，以其条件为准；此脚本只实现最新 N 盘，不支持筛选时不能仍把最新一盘当成用户指定的棋。可按官方月份档案或浏览器历史找到确切对局，再用同样校验流程。
- `partial` / `no_public_games` / 网络错误要如实报告数量与缺口；不能把少于要求的棋局说成全部完成。已有可靠材料仍可继续处理。

## 数据延迟与浏览器补充

公开接口无需登录，但有缓存，刚结束的棋局可能暂时没有。用户说“刚刚那局”、已知对手或时间与接口不符，或最新返回的是已有旧复盘时，使用可用浏览器工具检查其已结束对局历史并通过站点界面取 PGN。没有浏览器能力时说明缺口；可以接受用户的确切对局链接或 PGN 作为补充，不把复制粘贴作为默认步骤。需要登录时让用户自己登录，不索要密码或验证码；不能绕过访问限制。

请求保持串行，遇到 429/403 不无限重试。按需运行，不创建定时任务或后台监控。`.chess-review-account.json`、`.chess-review-preferences.json`、抓取资料和笔记不作为公开技能示例提交。

官方依据：[Published Data API](https://www.chess.com/news/view/published-data-api)、[PGN 导出说明](https://support.chess.com/en/articles/8705305-how-do-i-get-a-pgn-of-my-game)。这些接口是只读公开数据，不能用于走棋或修改账号。
