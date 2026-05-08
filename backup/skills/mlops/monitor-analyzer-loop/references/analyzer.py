（见 ~/.hermes/evolution_logs/skill_optimizer/analyzer.py）
完整代码约 298 行，包含：
- load_trends_dynamic()：从 trends.json 提取特征
- compute_frequency()：动态评分 frequency
- compute_impact()：动态评分 impact
- compute_auto_fix()：动态评分 auto_fix_potential
- decide_action()：决策（deep_review / new_skill / add_rule / archive）
- run()：主流程

关键 Bug 修复记录：
1. _ft_get() helper：defaultdict.get() 返回 None 而非 0，导致 TypeError
2. effective_failed = max(failed, 1 if has_ft else 0)：合并双数据源信号
