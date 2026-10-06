"""Built-in banners: uploaded once, then reused by file_id; captions over 1024 chars fall back to text."""
from conftest import fake, send, tap

from shop import media, settings


def test_banner_uploaded_once_then_cached():
    for key in list(settings.keys_with_prefix("fid:")):
        settings._raw.pop(key, None)
    send(7001, "/start")
    first = fake.last("sendAnimation", 7001)
    assert first is not None and "_files" in first  # uploaded from assets/main.mp4
    fake.reset()
    send(7002, "/start")
    second = fake.last("sendAnimation", 7002)
    assert second["animation"].startswith("ANIM") and "_files" not in second


def test_every_slot_has_a_default_asset():
    for slot, file_name in media.SLOTS.items():
        if file_name:
            assert media.slot(slot), f"missing assets/{file_name}"


def test_edit_between_photo_and_text_screens():
    send(7003, "/start")
    tap(7003, "cat", content={"message_id": 77, "date": 1, "chat": {"id": 7003, "type": "private"},
                              "animation": {"file_id": "X", "file_unique_id": "x", "width": 1, "height": 1,
                                            "duration": 1},
                              "document": {"file_id": "X", "file_unique_id": "x"}})
    assert fake.last("editMessageMedia", 7003) is not None
    tap(7003, "lang", content={"message_id": 78, "date": 1, "chat": {"id": 7003, "type": "private"},
                               "photo": [{"file_id": "P", "file_unique_id": "p", "width": 1, "height": 1}]})
    # language screen has no banner: the photo message is replaced by a text message
    assert fake.last("deleteMessage", 7003)["message_id"] == 78
    assert fake.last("sendMessage", 7003) is not None
