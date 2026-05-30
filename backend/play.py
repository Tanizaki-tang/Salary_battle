"""
Text Battle 交互式游戏
运行方式：在 backend 目录下执行 python play.py
输入 /quit 退出，输入 /state 查看状态
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.modules.text_battle.text_battle_engine import TextBattleEngine
from app.modules.flow_controller.session_state_machine import advance_game_flow
from app.shared_types.game_types import SessionState, TextTurnPayload


def main():
    engine = TextBattleEngine()

    state = SessionState(
        session_id="playground",
        user_id="player1",
        status="ongoing",
        round_index=1,
        max_round=5,
        hr_patience=70,
        info_exposure=20,
        trap_count=0,
    )

    print("=" * 50)
    print("  薪资谈判游戏 - Text Battle")
    print("=" * 50)
    print()

    # LLM 动态生成开场白
    opening = engine.generate_opening()
    print(f"HR：{opening}")
    print()
    print("提示：输入你的回复与HR谈判，输入 /quit 退出，输入 /state 查看状态")
    print()

    while True:
        # 玩家输入
        try:
            user_input = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            print("再见！")
            break

        if user_input == "/state":
            print()
            print(f"  回合: {state.round_index}/{state.max_round}")
            print(f"  HR耐心: {state.hr_patience}/100")
            print(f"  信息暴露: {state.info_exposure}/100")
            print(f"  陷阱次数: {state.trap_count}")
            print(f"  状态: {state.status}")
            print()
            continue

        # 执行回合
        payload = TextTurnPayload(player_text=user_input)
        result = engine.run_text_turn(state, payload)

        # 更新状态
        state = advance_game_flow(state, result)

        # 显示 HR 回复
        print(f"HR：{result.hr_reply}")
        print(f"  {result.delta.hr_patience} 耐心，{result.delta.info_exposure} 信息，{result.delta.trap_count} 陷阱")
        if result.is_trap_hit:
            print("  ⚡ 触发了陷阱！")
        print()

        # 检查游戏是否结束
        if result.is_game_over or state.status == "settled":
            print("=" * 50)
            print("  谈判结束！")
            print(f"  最终HR耐心: {state.hr_patience}/100")
            print(f"  信息暴露: {state.info_exposure}/100")
            print(f"  陷阱次数: {state.trap_count}")
            print("=" * 50)
            break


if __name__ == "__main__":
    main()
