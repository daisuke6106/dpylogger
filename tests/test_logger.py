import re
import threading

import pytest

from dpylogger.logger import LogLevel, Logger

LINE_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6} \[(?P<level>\w+)\] (?P<message>.*)$"
)


def test_level_filtering(tmp_path):
    filepath = tmp_path / "app.log"
    logger = Logger(LogLevel.WARN, str(filepath))
    logger.debug("debug message")
    logger.info("info message")
    logger.warn("warn message")
    logger.error("error message")
    logger.critical("critical message")
    logger.close()

    lines = filepath.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert "[WARN]" in lines[0]
    assert "[ERROR]" in lines[1]
    assert "[CRITICAL]" in lines[2]


def test_log_line_format(tmp_path):
    filepath = tmp_path / "app.log"
    logger = Logger(LogLevel.DEBUG, str(filepath))
    logger.info("example.")
    logger.close()

    line = filepath.read_text(encoding="utf-8").splitlines()[0]
    match = LINE_PATTERN.match(line)
    assert match is not None
    assert match.group("level") == "INFO"
    assert match.group("message") == "example."


def test_creates_parent_directory(tmp_path):
    filepath = tmp_path / "nested" / "dir" / "app.log"
    logger = Logger(LogLevel.DEBUG, str(filepath))
    logger.info("example.")
    logger.close()

    assert filepath.exists()


def test_write_after_close_raises(tmp_path):
    filepath = tmp_path / "app.log"
    logger = Logger(LogLevel.DEBUG, str(filepath))
    logger.close()

    with pytest.raises(ValueError):
        logger.info("example.")


def test_context_manager(tmp_path):
    filepath = tmp_path / "app.log"
    with Logger(LogLevel.DEBUG, str(filepath)) as logger:
        logger.info("example.")

    with pytest.raises(ValueError):
        logger.info("after close")


def test_thread_safety(tmp_path):
    filepath = tmp_path / "app.log"
    logger = Logger(LogLevel.DEBUG, str(filepath))

    thread_count = 20
    messages_per_thread = 50

    def worker(thread_id):
        for i in range(messages_per_thread):
            logger.info(f"thread-{thread_id}-message-{i}")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(thread_count)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    logger.close()

    lines = filepath.read_text(encoding="utf-8").splitlines()
    assert len(lines) == thread_count * messages_per_thread

    seen_messages = set()
    for line in lines:
        match = LINE_PATTERN.match(line)
        assert match is not None, f"corrupted line: {line!r}"
        seen_messages.add(match.group("message"))

    expected_messages = {
        f"thread-{t}-message-{i}"
        for t in range(thread_count)
        for i in range(messages_per_thread)
    }
    assert seen_messages == expected_messages
