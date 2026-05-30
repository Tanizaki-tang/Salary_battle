from app.prompt.dialogue_style import clamp_hr_reply, clamp_player_reply


def test_clamp_hr_reply_short() -> None:
    text = "好的，这块我再帮你确认一下。"
    assert clamp_hr_reply(text) == text


def test_clamp_hr_reply_truncate() -> None:
    long_text = "。".join(["这是很长的一段官方腔回复"] * 20)
    result = clamp_hr_reply(long_text)
    assert len(result) <= 120
    assert result.endswith(("。", "…"))


def test_clamp_player_reply() -> None:
    assert len(clamp_player_reply("我想把 base 谈到 18K，这个对我很关键还要再争取一下")) <= 50
