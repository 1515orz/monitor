import sys
from unittest.mock import MagicMock

# ultralytics 仅在 Jetson 上安装，测试环境（Mac/CI）无此包。
# 在任何测试模块导入前注入 mock，防止 ImportError。
sys.modules["ultralytics"] = MagicMock()
