# Chess Review Open · 国际象棋互动复盘技能

适用于任意棋手的 Agent Skill：把 PGN、棋谱文件或清晰截图转成带中文讲解的互动复盘网页。不绑定用户名、设备目录或托管平台。

提供完整回放、关键步分析、实战/改进对比、合法试走、提示、笔记和 PGN 下载。支持将多盘复盘汇总到一个离线 `index.html`。

## 安装与使用

1. 下载本仓库，把 `skills/chess-review-open` 整个文件夹放进支持 Agent Skills 的助手的技能目录。Codex 的默认用户技能目录是 `~/.codex/skills/`，安装后目录名保持 `chess-review-open`。
2. 准备 Python 3.10+。**Stockfish 19 已包含在技能文件夹中，无需单独下载或设置路径。**Python 依赖列在技能的 `requirements.txt`。浏览器测试额外需要 Node.js 18+、Playwright 和 Chromium；完整步骤见 [运行说明](skills/chess-review-open/references/workflow.md)。
3. 在助手中选择该技能，贴入 PGN。例如：

> 使用 $chess-review-open 分析这份棋谱。我执黑，输出到当前项目的 chess-reviews 文件夹。请指出最关键的失误和更好的下法，并生成互动网页。

也可以提供棋谱文件或清晰截图。执子方不明时助手会询问；不要求注册特定棋谱网站账号。默认界面为中文。

## 包内引擎

仓库实际包含五份官方 Stockfish 19 压缩包，总计约 406 MB，普通 Git clone 或 GitHub「Code → Download ZIP」都会包含它们，不使用 Git LFS 指针。请复制整个技能文件夹，包含 `vendor/stockfish/`。

- macOS：Apple Silicon 与 Intel（同一通用包）。
- Windows：x86-64 与 ARM64。
- Linux：x86-64 与 ARM64。

首次分析自动选择本机版本、校验 SHA-256 并解压。无需联网下载引擎；缓存默认位于分析结果 JSON 旁的 `engine-cache/`。后续复用缓存，损坏时从包内重新解压。安装 Python 依赖仍可能需要联网。其他系统或架构可用 `--engine` 指定自有引擎。

验证包内引擎：

```sh
.venv/bin/python skills/chess-review-open/scripts/bundled_engine.py --verify
.venv/bin/python skills/chess-review-open/scripts/analyze_game.py skills/chess-review-open/examples/black.pgn --perspective black --out work/analysis.json
```

macOS 已实际启动并完成示例分析；Windows/Linux 包已核对官方校验值、二进制、源码和许可证，但未在本项目维护环境中实际运行。

## 它怎样工作

PGN → python-chess 合法性检查 → 本地 Stockfish 分析 → AI 助手撰写教学讲解 → 生成并验证 HTML → 更新复盘目录。

该项目是一套由 AI 助手执行的技能，不是独立的聊天模型或上传服务器。Stockfish 在本机分析阶段运行，不在成品网页里实时运行。截图转写使用宿主助手的图像能力。没有引擎时必须如实注明人工分析。

默认输出在使用者当前工作目录的 `chess-reviews/`，可指定其他目录。不会自动发布网站。笔记只保存在当前浏览器，可导出，不跨设备自动同步。

## 不用真实棋局也能试用

以下示例在 macOS/Linux 终端从仓库根目录执行；Windows 使用 `.venv\Scripts\python.exe` 替代 `.venv/bin/python`。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r skills/chess-review-open/requirements.txt
.venv/bin/python skills/chess-review-open/scripts/build_review.py skills/chess-review-open/examples/black.pgn skills/chess-review-open/examples/black-review.json --out-dir chess-reviews
.venv/bin/python skills/chess-review-open/scripts/build_review.py skills/chess-review-open/examples/white.pgn skills/chess-review-open/examples/white-review.json --out-dir chess-reviews
.venv/bin/python skills/chess-review-open/scripts/build_library.py chess-reviews
```

打开 `chess-reviews/index.html`。两个样例是虚构教学记录，附有已写好的示例讲解；上面的演示构建无需 Stockfish。重新执行构建时使用新的暂存目录，脚本不会覆盖已有单盘 HTML。

## 目录

- `skills/chess-review-open/SKILL.md`：助手工作流程。
- `scripts/`：棋谱校验、引擎调用、网页构建及浏览器检查。
- `assets/`：单盘和总入口 HTML 模板。
- `references/`：运行说明与复盘 JSON 格式。
- `examples/`：虚构白方、黑方教学样例。

## 许可证

GPL-3.0-or-later。详见 [LICENSE](LICENSE) 和 [第三方说明](skills/chess-review-open/NOTICE.md)。Stockfish 的官方二进制、源码和许可证随包保留；python-chess、Playwright 仍单独安装并保留各自许可证。公开分享生成网页时保留其中棋子图形的署名。
