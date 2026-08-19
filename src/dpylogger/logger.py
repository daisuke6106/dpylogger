"""スレッドセーフなファイルロガー実装。

プレーンテキスト形式（:class:`Logger`）とYAML形式（:class:`YamlLogger`）の
2種類の出力形式をサポートする。いずれも :class:`_BaseLogger` を継承し、
ログレベルによるフィルタリングとスレッド間の排他制御を共通処理として提供する。
"""

from __future__ import annotations

import abc
import os
import threading
from datetime import datetime
from enum import IntEnum

import yaml


class LogLevel(IntEnum):
    """出力ログレベル。値が大きいほど重要度が高い。"""

    DEBUG = 10
    INFO = 20
    WARN = 30
    ERROR = 40
    CRITICAL = 50


class _BaseLogger(abc.ABC):
    """ログ出力の共通処理を担う基底クラス。

    インスタンスごとに1つのロックを保持し、複数スレッドから同時に
    ログ出力メソッドが呼び出されてもファイルへの書き込みが競合・破損
    しないようにする。1つの出力先ファイルに対しては、このロガーの
    インスタンスを1つだけ生成して使い回すこと（別インスタンスが
    それぞれ別のロックを持つため、同一ファイルへ複数インスタンスから
    書き込むと競合を防げない）。
    """

    def __init__(self, level: LogLevel, filepath: str) -> None:
        """ロガーを初期化し、出力先ファイルを追記モードで開く。

        Args:
            level (LogLevel): 出力する最小のログレベル。このレベル未満のログは無視される。
            filepath (str): ログの出力先ファイルパス。親ディレクトリが存在しない
                場合は自動的に作成される。

        Raises:
            OSError: 出力先ファイルを開けなかった場合。
        """
        self._level = LogLevel(level)
        self._filepath = filepath
        self._lock = threading.Lock()
        self._closed = False

        dirname = os.path.dirname(os.path.abspath(filepath))
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        self._file = open(filepath, "a", encoding="utf-8")

    def debug(self, message: str) -> None:
        """DEBUGレベルでログを出力する。

        Args:
            message (str): 出力するログメッセージ。
        """
        self._log(LogLevel.DEBUG, message)

    def info(self, message: str) -> None:
        """INFOレベルでログを出力する。

        Args:
            message (str): 出力するログメッセージ。
        """
        self._log(LogLevel.INFO, message)

    def warn(self, message: str) -> None:
        """WARNレベルでログを出力する。

        Args:
            message (str): 出力するログメッセージ。
        """
        self._log(LogLevel.WARN, message)

    def error(self, message: str) -> None:
        """ERRORレベルでログを出力する。

        Args:
            message (str): 出力するログメッセージ。
        """
        self._log(LogLevel.ERROR, message)

    def critical(self, message: str) -> None:
        """CRITICALレベルでログを出力する。

        Args:
            message (str): 出力するログメッセージ。
        """
        self._log(LogLevel.CRITICAL, message)

    def close(self) -> None:
        """出力先ファイルを閉じる。

        既に閉じている場合は何もしない（複数回呼び出しても安全）。
        """
        with self._lock:
            if not self._closed:
                self._file.close()
                self._closed = True

    def __enter__(self) -> "_BaseLogger":
        """コンテキストマネージャとして自身を返す。"""
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """コンテキストマネージャ終了時にファイルを閉じる。"""
        self.close()

    def _log(self, level: LogLevel, message: str) -> None:
        """ログレベルを判定し、閾値以上であればファイルへ書き込む。

        Args:
            level (LogLevel): このログエントリのログレベル。
            message (str): 出力するログメッセージ。

        Raises:
            ValueError: ロガーが既に閉じられている場合。
        """
        if self._closed:
            raise ValueError("I/O operation on closed logger")
        if level < self._level:
            return
        timestamp = datetime.now()
        with self._lock:
            self._write(level, timestamp, message)
            self._file.flush()

    @abc.abstractmethod
    def _write(self, level: LogLevel, timestamp: datetime, message: str) -> None:
        """1件のログエントリを出力先ファイルへ書き込む（サブクラスで実装）。

        Args:
            level (LogLevel): このログエントリのログレベル。
            timestamp (datetime): ログ出力時刻。
            message (str): 出力するログメッセージ。
        """
        raise NotImplementedError


class Logger(_BaseLogger):
    """プレーンテキスト形式でログを出力する。"""

    def _write(self, level: LogLevel, timestamp: datetime, message: str) -> None:
        """`YYYY-MM-DD HH:MM:SS.ffffff [LEVEL] message` 形式の1行を書き込む。

        Args:
            level (LogLevel): このログエントリのログレベル。
            timestamp (datetime): ログ出力時刻。
            message (str): 出力するログメッセージ。
        """
        line = f"{timestamp:%Y-%m-%d %H:%M:%S.%f} [{level.name}] {message}\n"
        self._file.write(line)


class YamlLogger(_BaseLogger):
    """YAML形式でログを出力する。

    各ログエントリをYAMLのブロックシーケンス項目としてファイル末尾に
    追記する。ブロックシーケンスは閉じ括弧を持たないため、追記のたびに
    ファイル全体を読み直す必要がなく、かつファイル全体は常に単一の
    有効なYAMLリストとして`yaml.safe_load()`で読み込める状態を保つ。
    """

    def _write(self, level: LogLevel, timestamp: datetime, message: str) -> None:
        """ログエントリをYAMLブロックシーケンス項目として書き込む。

        Args:
            level (LogLevel): このログエントリのログレベル。
            timestamp (datetime): ログ出力時刻。
            message (str): 出力するログメッセージ。
        """
        record = {
            "timestamp": timestamp.isoformat(timespec="milliseconds"),
            "level": level.name,
            "message": message,
        }
        dumped = yaml.safe_dump(
            [record],
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
        self._file.write(dumped)
