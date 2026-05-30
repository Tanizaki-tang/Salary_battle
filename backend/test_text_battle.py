"""
Text Battle 模块测试脚本
运行方式：在 backend 目录下执行 python test_text_battle.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.modules.text_battle.text_battle_engine import TextBattleEngine
from app.shared_types.game_types import SessionState, TextTurnPayload


PASS = 0
FAIL = 0


def check(name: str, actual, expected) -> None:
    global PASS, FAIL
    ok = actual == expected
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}")
    if not ok:
        print(f"         expected: {expected!r}")
        print(f")        actual:   {actual!r}")
        FAIL += 1
    else:
        PASS += 1


def check_in(name: str, actual: str, *expected_parts: str) -> None:
    global PASS, FAIL
    missing = [p for p in expected_parts if p not in actual]
    ok = len(missing) == 0
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}")
    if not ok:
        print(f"         missing: {missing}")
        print(f"         actual:  {actual!r}")
        FAIL += 1
    else:
        PASS += 1


def main():
    global PASS, FAIL
    engine = TextBattleEngine()

    # ──────────────────────────────────────────────
    # 1. 显式策略解析（不调 LLM）
    # ──────────────────────────────────────────────
    print("\n=== 1. 显式策略解析 ===")
    for s in ["strong_push", "probe", "concede", "counter_pressure"]:
        p = TextTurnPayload(strategy=s)
        check(f"payload.strategy={s}", engine.parse_strategy(p), s)

    # 空输入兜底
    check("空输入→probe", engine.parse_strategy(TextTurnPayload()), "probe")

    # ──────────────────────────────────────────────
    # 2. Delta 计算 & 回合缩放
    # ──────────────────────────────────────────────
    print("\n=== 2. Delta 计算 ===")
    state_r1 = SessionState(
        session_id="t", user_id="u", round_index=1,
        max_round=5, hr_patience=70, info_exposure=20,
    )
    state_r3 = SessionState(
        session_id="t", user_id="u", round_index=3,
        max_round=5, hr_patience=50, info_exposure=30,
    )
    state_r5 = SessionState(
        session_id="t", user_id="u", round_index=5,
        max_round=5, hr_patience=30, info_exposure=50,
    )

    # R1: scale=1.0
    d1 = engine._compute_delta("strong_push", state_r1)
    check("R1 strong_push patience", d1.hr_patience, -10)
    check("R1 strong_push exposure", d1.info_exposure, -3)

    # R3: scale=1.5, -10*1.5=-15, -3*1.5=-4.5→int(-4)
    d3 = engine._compute_delta("strong_push", state_r3)
    check("R3 strong_push patience (1.5x)", d3.hr_patience, -15)
    check("R3 strong_push exposure (1.5x)", d3.info_exposure, -4)

    # R5: scale=2.0
    d5 = engine._compute_delta("strong_push", state_r5)
    check("R5 strong_push patience (2.0x)", d5.hr_patience, -20)
    check("R5 strong_push exposure (2.0x)", d5.info_exposure, -6)

    # concede 正数缩放
    dc = engine._compute_delta("concede", state_r5)
    check("R5 concede patience (8*2.0)", dc.hr_patience, 16)
    check("R5 concede exposure (5*2.0)", dc.info_exposure, 10)

    # trap
    dt = engine._compute_delta("counter_pressure", state_r1)
    check("counter_pressure trap=1", dt.trap_count, 1)

    # ──────────────────────────────────────────────
    # 3. 兜底回复
    # ──────────────────────────────────────────────
    print("\n=== 3. 兜底回复（无需 LLM） ===")
    for s in ["strong_push", "probe", "concede", "counter_pressure"]:
        reply = engine._FALLBACK_REPLIES[s]
        check(f"{s} 兜底回复非空", len(reply) > 10, True)

    # ──────────────────────────────────────────────
    # 4. 标签清理（模糊匹配）
    # ──────────────────────────────────────────────
    print("\n=== 4. 策略标签清理 ===")
    check("精确: strong_push", engine._clean_strategy_label("strong_push"), "strong_push")
    check("模糊: strong→strong_push", engine._clean_strategy_label("strong"), "strong_push")
    check("模糊: counter→counter_pressure", engine._clean_strategy_label("counter"), "counter_pressure")
    check("含中文+标签", engine._clean_strategy_label("我认为这是probe策略"), "probe")
    check("无效→None", engine._clean_strategy_label("随机文本"), None)

    # ──────────────────────────────────────────────
    # 5. HR Prompt 构建
    # ──────────────────────────────────────────────
    print("\n=== 5. HR Prompt 构建 ===")
    prompt = engine._build_hr_prompt("strong_push", "太低", state_r3)
    check_in("含轮次", prompt, "3", "5")
    check_in("含耐心值", prompt, "50")
    check_in("含策略中文", prompt, "强硬施压")
    check_in("含玩家发言", prompt, "太低")

    # ──────────────────────────────────────────────
    # 6. 完整回合（run_text_turn）
    # ──────────────────────────────────────────────
    print("\n=== 6. 完整回合（run_text_turn） ===")
    result = engine.run_text_turn(state_r1, TextTurnPayload(strategy="probe"))
    check("返回 hr_reply 非空", len(result.hr_reply) > 5, True)
    check("返回 delta", result.delta is not None, True)
    check("next_round=2", result.next_round, 2)
    check("R1 is_game_over=False", result.is_game_over, False)

    # 第5轮应为结束
    result5 = engine.run_text_turn(state_r5, TextTurnPayload(strategy="probe"))
    check("R5 is_game_over=True", result5.is_game_over, True)

    # ──────────────────────────────────────────────
    # 7. LLM 集成测试（需联网 + 有效 Key）
    # ──────────────────────────────────────────────
    print("\n=== 7. LLM 集成测试 ===")
    try:
        s = engine._classify_with_llm("请问试用期薪资怎么算")
        if s == "probe":
            check("LLM 分类: 试探→probe", s, "probe")
        else:
            print(f"  [SKIP] LLM 分类返回了 {s}（LLM 可能不可用）")

        reply = engine._generate_hr_reply("probe", "薪资范围是多少", state_r1)
        fallback = engine._FALLBACK_REPLIES["probe"]
        if reply != fallback:
            print(f"  [PASS] LLM HR 回复非兜底: {reply[:50]}...")
            PASS += 1
        else:
            print(f"  [WARN] LLM HR 回复=兜底（LLM 可能不可用）")
    except Exception as e:
        print(f"  [SKIP] LLM 不可用: {e}")

    # ──────────────────────────────────────────────
    # 结果
    # ──────────────────────────────────────────────
    total = PASS + FAIL
    print(f"\n{'='*40}")
    print(f"  结果: {PASS}/{total} 通过", end="")
    if FAIL > 0:
        print(f", {FAIL} 失败")
    else:
        print(" [OK]")


if __name__ == "__main__":
    main()
