from app.modules.card_game.card_engine import CardGameEngine, compute_delta, count_conditions


def test_initial_stats() -> None:
    engine = CardGameEngine()
    state = engine.create_initial_state("card_test", "u1", "张三", "hr_honest")
    assert state.stats.satisfaction == 6
    assert state.stats.salary_k == 15
    assert state.round_index == 1


def test_strong_push_hurts_satisfaction() -> None:
    delta = compute_delta("strong_push", "hr_aggressive", 5, [])
    assert delta.satisfaction < 0
    assert delta.salary_k > 0


def test_settle_score_range() -> None:
    engine = CardGameEngine()
    state = engine.create_initial_state("card_test2", "u1", "李四", "hr_newbie")
    state, _ = engine.play_turn(state, "concede")
    result = engine.settle(state)
    assert 0 <= result.final_score <= 110
    assert result.breakdown.salary >= 0


def test_collapse_on_zero_satisfaction() -> None:
    engine = CardGameEngine()
    state = engine.create_initial_state("card_test3", "u1", "王五", "hr_aggressive")
    for _ in range(4):
        if state.status != "ongoing":
            break
        state, result = engine.play_turn(state, "strong_push")
    assert state.status == "collapsed" or state.stats.satisfaction <= 0 or result.is_game_over


def test_accept_requires_round_three() -> None:
    engine = CardGameEngine()
    state = engine.create_initial_state("card_test4", "u1", "赵六", "hr_honest")
    try:
        engine.accept_offer(state)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_play_turn_uses_player_text() -> None:
    engine = CardGameEngine()
    state = engine.create_initial_state("card_test5", "u1", "赵六", "hr_honest")
    custom = "我想把 base 谈到 18K，这个对我很关键。"
    state = state.model_copy(update={"option_replies": {**state.option_replies, "strong_push": custom}})
    next_state, result = engine.play_turn(state, "strong_push", custom)
    assert result.player_text_used == custom
    assert next_state.last_player_text == custom


def test_conditions_count() -> None:
    from app.shared_types.card_game_types import CardGameStats

    stats = CardGameStats(satisfaction=5, salary_k=19, work_hours=8, security=4)
    assert count_conditions(stats) == 4
