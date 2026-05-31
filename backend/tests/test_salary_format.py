from app.prompt.salary_format import fix_misformatted_salary_k, format_salary_k, apply_opening_placeholders


def test_format_salary_k() -> None:
    assert format_salary_k(13000) == "13K"
    assert format_salary_k(15000) == "15K"
    assert format_salary_k(15500) == "15.5K"


def test_fix_misformatted_salary_k() -> None:
    assert fix_misformatted_salary_k("我们给到13000K") == "我们给到13K"
    assert fix_misformatted_salary_k("月薪15K") == "月薪15K"
    assert fix_misformatted_salary_k("1500K") == "1500K"


def test_apply_opening_placeholders_newbie_template() -> None:
    raw = "您好您好！我这边是 XX 公司的 HR...面试结果出来了，给您定的薪资是 15K。您有什么想法吗？"
    out = apply_opening_placeholders(raw, offer_token="15K", company_name="灵创科技")
    assert "15K15K" not in out
    assert "灵创科技" in out
    assert "XX" not in out


def test_apply_opening_placeholders_salary_x() -> None:
    raw = "offer是X，14薪"
    out = apply_opening_placeholders(raw, offer_token="15K", company_name="灵创科技")
    assert out == "offer是15K，14薪"
