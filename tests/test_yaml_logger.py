import threading

import yaml

from dpylogger.logger import LogLevel, YamlLogger


def test_yaml_single_list(tmp_path):
    filepath = tmp_path / "app.yaml"
    logger = YamlLogger(LogLevel.DEBUG, str(filepath))
    logger.info("first")
    logger.warn("second")
    logger.close()

    with open(filepath, encoding="utf-8") as f:
        records = yaml.safe_load(f)

    assert isinstance(records, list)
    assert len(records) == 2
    assert records[0]["level"] == "INFO"
    assert records[0]["message"] == "first"
    assert "timestamp" in records[0]
    assert records[1]["level"] == "WARN"
    assert records[1]["message"] == "second"


def test_yaml_level_filtering(tmp_path):
    filepath = tmp_path / "app.yaml"
    logger = YamlLogger(LogLevel.ERROR, str(filepath))
    logger.info("ignored")
    logger.error("kept")
    logger.close()

    with open(filepath, encoding="utf-8") as f:
        records = yaml.safe_load(f)

    assert len(records) == 1
    assert records[0]["message"] == "kept"


def test_yaml_message_with_special_characters(tmp_path):
    filepath = tmp_path / "app.yaml"
    logger = YamlLogger(LogLevel.DEBUG, str(filepath))
    tricky_message = "line1\nline2: colon, dash - and emoji 🚀"
    logger.info(tricky_message)
    logger.close()

    with open(filepath, encoding="utf-8") as f:
        records = yaml.safe_load(f)

    assert records[0]["message"] == tricky_message


def test_yaml_thread_safety(tmp_path):
    filepath = tmp_path / "app.yaml"
    logger = YamlLogger(LogLevel.DEBUG, str(filepath))

    thread_count = 10
    messages_per_thread = 30

    def worker(thread_id):
        for i in range(messages_per_thread):
            logger.info(f"thread-{thread_id}-message-{i}")

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(thread_count)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    logger.close()

    with open(filepath, encoding="utf-8") as f:
        records = yaml.safe_load(f)

    assert isinstance(records, list)
    assert len(records) == thread_count * messages_per_thread

    messages = {r["message"] for r in records}
    expected_messages = {
        f"thread-{t}-message-{i}"
        for t in range(thread_count)
        for i in range(messages_per_thread)
    }
    assert messages == expected_messages
