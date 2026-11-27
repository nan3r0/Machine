# Contract change: tests/test_lipsync_wiring.py::test_acceptance

Test: `test_acceptance` in tests/test_lipsync_wiring.py.

Why: it calls `test_render_one_passes_the_voice_levels_to_the_scenes` and then
`test_router_hands_the_levels_to_every_host` with the same `monkeypatch`. The first call patches
`router.build_scenes_ass` with a fake (returns the string "[Script Info]\n"), and that patch is
still active in the second call, which then calls the fake instead of the real router. So
`host_events` is never reached and `got == []`. The two tests pass on their own; only the
combined acceptance test fails. The implementation is correct (verified by the two tests alone).

Fix: in `test_acceptance`, undo the first patch before the second call, for example run the
router half first and then the render half, or use `with monkeypatch.context() as m:` for each
half and pass `m` to it.
