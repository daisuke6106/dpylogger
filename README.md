# dpylogger
本プロジェクトはロギング処理を行うライブラリ。

出力方式としては以下が指定可能である。

- log
- yaml

出力レベルとしては以下が指定可能である。

- debug
- info
- warn
- error
- critical

## How to install

```
pip install git+https://github.com/daisuke6106/dpylogger.git
```

## How to use

```
# import文
from dpylogger.logger import Logger, YamlLogger, LogLevel

# ロガーインスタンス初期化
# logファイル
logger = Logger(LogLevel.DEBUG, "/filepath/filename.log")
# yamlファイル
logger = YamlLogger(LogLevel.DEBUG, "/filepath/filename.yaml")

# ログ出力
# 以下メソッドを呼び出すことで、所定の出力先に出力が行われる。
logger.debug("example.")
logger.info("example.")
logger.warn("example.")
logger.error("example.")
logger.critical("example.")
```

