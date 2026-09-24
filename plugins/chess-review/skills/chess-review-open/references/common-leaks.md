# 持续维护常见漏洞对比页

先按下方“首次开启、样本与时间预算”确认本用户是否开启；已开启时，每次新复盘后执行本流程。界面使用双棋盘对比动画；不要再生成或恢复独立文字版、长篇文字清单或文字版下载入口。保留棋盘旁短解释、每步说明和一个可执行习惯。

## 固定呈现与存储

- 默认打开「常见漏洞」标签，「进步记录」放在独立标签，点击后才显示，不占漏洞首屏。切换时暂停回放；支持键盘切换和 `#progress` 直达进步。

- 左边（手机上方）固定为「你原来这样走」，只用真实棋谱；右边（手机下方）固定为「建议这样走」，明确是已核对的示范。两边同一 FEN 起点，默认显示关键第一手，并用中文棋子名称、起止格与 SAN 标出两种选择。
- 两边各有播放、暂停、前后步与进度条；提供回到共同起点、关键一步对比、各自后续结果、先播实战再播建议。分支长度不同，不补造落子。
- 对手本可利用但实战未走的变化，单独放在折叠的「假设、非实战」区域，绝不能接到真实棋谱里。
- 复用 `assets/leaks-template.html`、`scripts/build_leaks.py`、`scripts/check_leaks.cjs`。案例、类别、短对比说明都存入 HTML 的 `visual-data` JSON；这个可版本控制的成品就是持续档案，不依赖旧 `work/` 文件，也没有外部 JSON 或联网引擎依赖。
- 优先找到已有页并更新同一个文件和 URL，不按日期另建孤立页；新用户确认开启后使用 `common-leaks.html`。不同棋手使用不同目录，不预设用户名。

## 每盘的判断

1. 读取现有案例和类别，再看新棋局中已经验证的关键步。按失误机制归类，而非仅按开局名、棋子类型或最终输赢。
2. 同类问题：新增清楚、适合用户水平的真实案例，归入已有 `group_id`。每步选一个主要类别，避免重复收录同一局面。保留旧例子，方便跨局比较。
3. 新机制：建立简洁的新类别，至少配一个已验证的原走法/建议走法对比。第一次只标「新发现」；不同真实对局中出现才标「多盘复现」。模板根据不同 `game_key` 自动区分，不能把同一盘的多个例子算成多盘复现。
4. 没有可靠的新证据时，不为了凑数加类别或把正常走法讲成漏洞。记录本盘已检查及理由；这也算完成本次漏洞检查。
5. 一两步丢子、漏防、回吃、暴露线路优先。复杂残局可作进阶题，不能说成用户每次都必须找到的简单棋。好棋同时进入进步记录；不能因为赢棋就忽略里面的漏洞。

## 增量输入

构建器会从已验证的单盘 HTML 读取该 `ply` 对应的 lesson，再核对同名 PGN。若想收录的关键步还不是单盘 lesson，先补充并验证它。不要直接手写不可靠的棋盘状态。

先导出当前档案供检查（不修改网页）：

```sh
python scripts/build_leaks.py /actual/chess/folder --export work/leaks-existing.json
```

写 `work/leaks-update.json`，只包含此次增加或更新的条目：

```json
{
  "groups": [],
  "cases": [
    {
      "stem": "YYYY-MM-DD_OPPONENT",
      "ply": 8,
      "group_id": "direct-threats",
      "title": "后和象一起攻击 f2",
      "contrast": {
        "actual": "原走法没有解决 f2 的将死威胁。",
        "better": "先挡住黑后的路线，化解这次杀棋。"
      },
      "captions": {
        "actual": ["共同起点的危险。", "用户真实的一步。", "对手实际的回应。"],
        "better": ["相同起点的防守目标。", "示范第一步的作用。"]
      },
      "arrows": {"actual": {"0": [["f6", "f2"]]}}
    }
  ],
  "assessments": [
    {
      "stem": "YYYY-MM-DD_OPPONENT",
      "outcome": "existing",
      "note": "第 5 步再次漏防直接威胁，已加入对应类别。"
    }
  ]
}
```

这只是结构示例；实际 `ply`、格子、说明和数组长度必须来自当前真实棋谱。`captions` 长度等于该 lesson 的 `actualStates` / `betterStates`（含第 0 帧起点）；不能为适配示例长度截掉重要回应。

新类别放进 `groups`：`id`（稳定语义标识）、`title`、`short`（短按钮文字）、`desc`、`habit`。可以使用的类别 ID 例子是 `direct-threats`、`recapture`、`opened-lines`、`development`，不要每次换名或重建。

可选 `threat`：`{"moves":["..."],"captions":["共同起点说明","每一步说明", "..."]}`。从同一个起点给合法 SAN 序列；标题由模板强制标为假设。

`assessments` 每个新复盘至少一条，`outcome` 为 `existing`（归入已有类）、`new`（新增类）或 `none`（没有可信的可收录问题）；`note` 记录简短依据。同一盘同时出现旧类和新类时用 `new`，并在 note 说明两者。已有同局面如需改正，明确使用 `--replace-cases`，不要用新 ID 绕过去。

## 构建、核对与交付

```sh
python scripts/build_leaks.py /actual/chess/folder --merge work/leaks-update.json
CHESS_REVIEW_PLAYWRIGHT=/actual/path/to/playwright CHESS_REVIEW_BROWSER=/actual/path/to/chrome node scripts/check_leaks.cjs /actual/chess/folder/common-leaks.html work/leaks-qa
python scripts/build_library.py /actual/chess/folder
```

使用当前可用 Python、python-chess、Node、Playwright；详见 `workflow.md`，不要把本机 runtime 绝对路径写进通用脚本。多个历史 leak 文件存在时，传 `--page 已有文件名.html` 指定同一档案，不覆盖未知文件。

构建器按 Chess.com 数字 game ID（兼容 URL 格式）和 `ply` 去重；无网址时根据棋谱签名及日期时间识别。它核对用户颜色、真实分支逐手匹配原 PGN、同一起点、建议/假设分支合法、将军将死和动画起止格。完整 JSON 导出包含 `game_key`、`signature`、稳定案例 `id` 及 `assessments`，旧记录不得丢失。

浏览器检查全部案例、独立/顺序播放、默认关键第一手、桌面并排、390/320 像素上下布局、离线资源。查看截图，确认标题一直清晰，实际与推荐不用猜。首尾帧及归类依据仍需人工审查，合法不等于好棋。

`build_library.py` 自动保留漏洞页入口；更新后旧棋局和笔记键应保持不变。默认将正式 HTML/PGN 保存在使用者本地复盘目录，不执行提交、推送或部署。插件源码仓库不是复盘结果的上传目标。仅在使用者明确要求发布且确认自己的目标仓库或托管项目后，才另行发布并验证。最终回复简述本盘新增到哪个类别或发现了什么新问题，链接同一个对比页即可，不再附长篇纯文字复盘清单。


## 进步记录：每盘同时寻找正向证据

用户希望在练习中看见自己正在做对什么。每次复盘同时检查 `progress`，将可核对的好棋加入同一个页面；不要求每盘必须产生“进步”，也不根据输赢、等级分或模型猜测的心理状态下结论。

三种证据分开标注：

- `good_move`（这一步值得保留）：一手经过验证的真实好棋。解释它的具体作用，以及下次可以重复的动作。
- `comparison`（一次可见改善）：较早漏掉的机会与后来做对的相近任务。两盘必须时间先后正确、机制可比，不能拿两种完全不同的难度证明整体提高。
- `repeated`（已有多次成功例子）：在不同对局中多次做对同一类事情。它仍不自动等于稳定掌握；遇到后续反例，应在简短说明中承认不稳定。

不要从一两盘说“已经明显变强”“以后不会犯”“练习一定奏效”。没有足够前后证据时只肯定这次真实的好棋。若将来要声称稳定改善，需要说明所比较的多盘样本和机会，而非只选择成功案例。

展示仍以棋盘动画为主：较早的实际走法与这次的实际走法可并排/上下回放，明确写“不同局面，两边都是真实棋谱”，不可冒充同一起点的推荐分支。只有一条证据时展示单个实际棋盘。每条都写清“做对了什么”“值得保留的动作”和证据范围；不要恢复独立长篇文字版。

在同一个增量 JSON 中增加 `progress` 数组。每条包括 `kind`、`title`、`skill`（比较的能力）、`explanation`（具体证据）、`habit`（可重复的动作）、`limit`（简短范围说明）、`current`，比较类还必须有 `prior`。每个棋局片段使用 `{"stem":"YYYY-MM-DD_OPPONENT","ply":8,"captions":["起点说明","每步说明"]}`，帧数与对应单盘 lesson 的 `actualStates` 完全相同。`current` 必须来自已经验证并标记 `positive: true` 的 lesson；`repeated` 的 `prior` 也必须是已验证好棋。不要为了通过校验而把失误改成 positive。没有现成 lesson 时先补充并核对单盘复盘。

`build_leaks.py` 自动保存真实回放、稳定 `progress:<game_key>:<ply>` ID，检查先后时间与合法性，增量追加并去重；如需更正旧条目仍使用 `--replace-cases`。旧 `progress` 必须保留。新复盘的 `assessments` 可附 `progress_note` 简述本次正向发现或未能形成比较的原因，即使 `outcome` 是 `none`（无新漏洞）也仍检查正向表现。

运行 `check_leaks.cjs` 时同时检查所有进步回放及手机布局。用户交付时简短指出具体做对的一件事及证据强度，链接同一个页面，不用长篇夸奖替代棋盘证据。

## 首次开启、样本与时间预算

此部分由同插件的 [chess-common-leaks](../../chess-common-leaks/SKILL.md) 入口执行。当前通用版门槛为 **至少 10 盘同一棋手、不同对局且已完成互动复盘的标准棋局**，这是产品默认，不是统计证明。规划器核对 HTML 内嵌棋谱、执子身份、完整回放和教学数据；仅有 PGN、空 HTML 或重复对局都不算。

1–9 盘时正常交付单盘和好棋，告知距离门槛还差多少；不自动抓取并分析历史来凑数。达到 10 盘后，用户明确要求 common leaks 即视为开启；否则单盘交付后提示一次可选开启。拒绝后不反复询问，已有开启偏好不重复问。用户自己的私人旧档案不受这个通用版首次门槛追溯影响。

偏好保存在用户复盘目录 `.chess-review-preferences.json`，不公开发布。首次由用户选择后才传 `--enable`；关闭用 `--disable`，保留旧文件。

```sh
python scripts/plan_common_leaks.py /actual/chess/folder --user CONFIRMED_USERNAME --enable --out work/leaks-plan.json
```

首次默认从最近 **10 盘已完成复盘**提取证据；更多历史列为 deferred，不静默全量计算。每一盘写入 assessment，包括没有可归类问题的 `none`。一类至少在两盘中出现才标“多盘复现”，单例标“新发现”。门槛为 10 盘不等于每类问题都要重复 10 次。

首次整理可预估约 8–20 分钟，后续 1 盘通常按约 2–6 分钟估计；依赖环境与证据难度，这些不是性能保证。预算目标 25 分钟，最后 5 分钟留给验证与保存。到 `stop_new_work_at` 停止扩展范围，到 `finish_by` 交付已完成范围并说明剩余，目标约半小时内。若首次未检查够 10 盘，保存工作记录并说明档案尚未完成，不伪称达到门槛。

优先复用已有单盘教学和引擎结果，仅为确有必要的候选局面补查；不对这 10 盘重复全盘计算。常规单盘任务默认 1 盘，10 盘门槛不是第一次运行必须分析 10 盘。当前不创建后台 job、定时监控或自动唤醒。

首次建立档案需要已授权计划，以及每个被选棋局的检查记录：

```sh
python scripts/build_leaks.py /actual/chess/folder --user CONFIRMED_USERNAME --plan work/leaks-plan.json --merge work/leaks-update.json
```

构建器再次核对至少 10 盘真实完整复盘、独立游戏 ID 与全体 assessment；不能只修改计划数字绕过门槛。后续新增 1 盘即可更新，默认每批最多 5 盘：

```sh
python scripts/plan_common_leaks.py /actual/chess/folder --user CONFIRMED_USERNAME --stems NEW_REVIEW_STEM --out work/leaks-plan.json
python scripts/build_leaks.py /actual/chess/folder --merge work/leaks-update.json
```

只处理本次新复盘。规划器遇到已有档案却未指定本次棋局时返回 `specify_new_games`，不要自动重算所有历史。加入旧类、新类或正向记录，保留原案例与稳定身份。无可信新问题也算完成本次检查。

## 什么时候可以说一个漏洞在改善

对每次同类**可比机会**记录实际处理结果，不能只数“多少盘没犯错”。根本没有出现这种机会，不是修复证据。先展示“这次处理正确”和“已有多次正确例子”；有足够后续可比对局，再描述具体证据，例如“最近 3 次遇到这个威胁都正确处理”。报告样本与反例，避免说“永久修复”“已经不会犯”。如果再次出现，保留之前做对的例子并更新当前训练重点。不要为了鼓励而隐藏失误，也不要因为失误否定真实进步。
