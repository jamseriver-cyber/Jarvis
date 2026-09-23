# 贡献指南

欢迎报告问题、提出改进或提交 PR。本项目目前处于 Alpha 阶段，主要支持 Windows。

1. 提交问题时请写明 Windows、Python、Ollama 和模型版本，以及可复现步骤。不要上传真实录音、`data/` 数据库、窗口标题或个人日志。
2. 修改代码时尽量保持工具操作受控，不要给模型直接开放任意命令行、文件删除或未经确认的外发操作。
3. 新功能请尽可能附带不操作真实桌面和网络的自动化测试。
4. 提交前运行 `python -m unittest discover -s tests -p "test_*.py" -v` 和 `python -m compileall -q main.py core llm voice scripts`。
5. PR 中说明改动、测试方式及已知限制。涉及第三方模型或媒体资源时，请提供明确的授权来源，不要直接提交权重或个人数据。
