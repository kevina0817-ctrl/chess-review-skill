# 运行与验证

## 依赖

需要 Python 3.10+、`chess` Python 包（python-chess 项目）和本地 Stockfish。浏览器测试另外需要 Node.js 18+、Playwright 和 Chromium。生成网页本身不需要 Node.js，浏览成品不需要 Python 或 Stockfish。

在任意项目工作目录创建独立 Python 环境。以下 `SKILL_DIR` 指向安装后的技能文件夹；路径由当前机器决定。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r "$SKILL_DIR/requirements.txt"
```

Windows 使用 `.venv\Scripts\python.exe` 替代 `.venv/bin/python`。若宿主已经提供可用依赖，直接使用它，不覆盖全局环境。

从 [Stockfish 官网](https://stockfishchess.org/download/) 下载适合当前系统的可执行程序，或使用用户已有的本地安装。以 `--engine` 指定实际路径，或将 `stockfish` 加入 PATH。二进制单独安装，不打包进技能。不要硬编码某位用户的路径，不为每盘重复下载。

## 校验与分析

```sh
.venv/bin/python "$SKILL_DIR/scripts/prepare_game.py" game.pgn --out-dir work/prepared
.venv/bin/python "$SKILL_DIR/scripts/analyze_game.py" work/prepared/normalized.pgn --perspective black --engine /actual/path/to/stockfish --out work/analysis.json
```

`--perspective` 必须对应本次确认的执子方。默认逐局面分析 0.3 秒，最值得复查的最多 8 步前后局面各加深 1.5 秒；复杂战术可以进一步增加时间或核对多个候选。`rank_score` 内部用极值排序将死，不能展示为正常分数。

PGN 解析器可能忽略无意义字符，仍须核对原输入的着法数量与顺序。多盘输入用 `--game 0` 等明确索引；只有局面时使用经过验证的 SetUp/FEN 标签，不捏造历史。

## 生成与归档

代理依据引擎结果编写 `review.json`；脚本不会自动生成自然语言讲解。字段见 `review-schema.md`。

```sh
.venv/bin/python "$SKILL_DIR/scripts/build_review.py" work/prepared/normalized.pgn work/review.json --out-dir work/site-staging
```

构建器会校验教学变化、执子方和将死标记，拒绝静默覆盖现有 HTML。验证后把正式 HTML、PGN 移入选定的输出目录（默认 `chess-reviews/`），运行：

```sh
.venv/bin/python "$SKILL_DIR/scripts/build_library.py" chess-reviews
```

总入口内嵌所有复盘。构建器只扫描顶层日期命名的 HTML，跳过符号链接和工作目录；保留已有总入口中的历史棋局，并更新同名修正版。它拒绝覆盖不属于该格式的 index.html。不同对局使用唯一文件名。

## 浏览器检查

在任务工作目录安装测试依赖：

```sh
npm install --no-save playwright
npx playwright install chromium
node "$SKILL_DIR/scripts/check_review.cjs" work/site-staging/DATE_OPPONENT.html work/qa
node "$SKILL_DIR/scripts/check_library.cjs" chess-reviews/index.html work/library-qa
```

如果宿主已有浏览器和 Playwright，可设置 `CHESS_REVIEW_PLAYWRIGHT` 为 Playwright 包路径、`CHESS_REVIEW_BROWSER` 为浏览器可执行路径。两者都基于当前机器。检查器支持从当前工作目录的 node_modules 查找依赖。

检查全部关键步与合法试走、完整回放、下载、笔记隔离及桌面/窄屏。查看桌面和手机截图，确认棋子和中文可读，没有重叠。测试库建立独立副本，不修改用户的实际浏览器笔记。

## 可重复示例

`examples/black.pgn` 与 `examples/white.pgn` 是虚构教学记录，配套 review.json 已人工撰写，未宣称执行过引擎分析。可直接构建以检查模板，或另外运行引擎分析；不要将示例的结论套用到真实对局。

## 公开分享

技能不依赖特定棋谱网站，支持标准 PGN。默认生成文件，可离线打开。上传生成网页到任意静态托管需使用者自己授权与配置。该技能没有服务器、用户登录或自动上传服务；AI 助手在使用者的环境执行流程。
