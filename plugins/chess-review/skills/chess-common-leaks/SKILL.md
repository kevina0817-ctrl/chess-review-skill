---
name: chess-common-leaks
description: 在同一棋手累计至少 10 盘已完成互动复盘后，按需建立常见漏洞与进步档案；开启后随每盘新复盘增量更新。用于用户询问 common leaks、反复出现的失误或跨局进步。复用同插件 chess-review-open 的数据与工具，不用于首次单盘复盘或后台监控。
---

# 常见漏洞与进步

这是 Chess Review plugin 的跨局入口。单盘复盘由相邻的 [chess-review-open](../chess-review-open/SKILL.md) 负责；这里复用它的引擎证据、棋谱、教学数据和模板，不另装一份引擎，不复制历史。

## 首次开启

1. 找到用户当前复盘目录，读取 `.chess-review-account.json` 或以用户已确认的 PGN 身份为准。不同棋手分目录，每盘身份独立确认。
2. 使用相邻 skill 的 `scripts/plan_common_leaks.py` 统计不同对局的**已完成复盘**。原始 PGN、重复棋谱、无法匹配棋谱的 HTML 不计入门槛。至少 10 盘方可首次建立跨局档案；这是产品门槛，不是统计结论的保证。
3. 未满 10 盘：告知已完成数量和还差多少盘，继续用户请求的单盘复盘，不自动抓取或分析历史补满。用户可明确要求补做若干盘。
4. 已满 10 盘：用户主动请求 common leaks 即为开启授权；若只是单盘任务，先交付单盘，再可选提示一次。默认不自动启动首次整理。用户拒绝后不反复询问。偏好存本地 `.chess-review-preferences.json`；可记录 `common_leaks_offered: true` 避免重复提示。
5. 开启时选最近 10 盘已完成复盘，先报约 8–20 分钟估计；预算 25 分钟，最后 5 分钟验证，目标约半小时内。大量历史列为后续；不重算全部引擎结果，不把估计说成性能保证。

从插件中解析 `REVIEW_SKILL_DIR` 为相邻 `chess-review-open` 的实际路径，用当前可用 Python：

```sh
python "$REVIEW_SKILL_DIR/scripts/plan_common_leaks.py" chess-reviews --user CONFIRMED_USERNAME --enable --out work/leaks-plan.json
```

只有用户已授权开启才能传 `--enable`。用户明确关闭时用 `--disable`，保留历史页面。达到数量不等于默认授权。

## 归类与交付

读取 [完整格式与校验流程](../chess-review-open/references/common-leaks.md)。按 `plan.selected` 逐盘检查，全部记录 assessment；同类问题加入稳定 `group_id`，不同机制可新建分类。某类至少出现在两盘不同真实对局才叫“多盘复现”；单例标“新发现”。没有可信问题时记录 `none`，不得制造漏洞以凑数。

3.0 的单盘页包含双方关键步。只使用用户本人走棋前的局面作为漏洞或进步证据；`actor: opponent` 的好棋或失误不能算成用户的表现，引擎示范也不是已发生的进步。参考分变化只是辅助指标，不能单凭平均分上涨判断某类漏洞已修复。

以动画对比展示：同一起点的真实走法、建议走法、结果和一个训练动作。常见漏洞是默认标签，真实好棋与有证据的进步放在独立“进步记录”标签。没有相近机会不能断言已修复；成功、反例与样本范围都保留。

生成同一个 `common-leaks.html`，浏览器验证后重建 `index.html`；已有文件沿用原路径。没有可收录案例时可交付检查结论、保留本地 assessment 工作记录，后续有证据再建动画页，不伪造空洞类别。

## 后续自动增量

此用户已开启时，每次 `chess-review-open` 完成新棋局后，在同一请求里执行这一步，无需用户再说“run common leaks”。只传本次新完成棋局的 stems；新增一盘也可以更新，首次 10 盘的门槛不重新阻塞已有档案。

```sh
python "$REVIEW_SKILL_DIR/scripts/plan_common_leaks.py" chess-reviews --user CONFIRMED_USERNAME --stems NEW_REVIEW_STEM --out work/leaks-plan.json
python "$REVIEW_SKILL_DIR/scripts/build_leaks.py" chess-reviews --merge work/leaks-update.json
```

按稳定游戏 ID 和关键步去重；补充旧类别、新类别或正向证据，保留以前的案例和笔记。未发现新漏洞也记录已检查。输出一句本次变化并提供动画入口，不再另做纯文字长报告。

这是 coding agent 响应用户复盘请求时的自动流程，不是轮询账号、定时任务或云端服务。默认只交付使用者本地的 HTML 文件，不提交、不推送、不部署到插件源码仓库。仅在使用者明确要求发布且确认自己的目标仓库或托管项目后，才另行处理发布。
