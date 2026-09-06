from gateway import Platform, build_plan, detect_platform


def test_platform_detection():
    assert detect_platform("https://www.facebook.com/share/r/19b56K4KxL/") == Platform.FACEBOOK
    assert detect_platform("https://www.instagram.com/reel/abc/") == Platform.INSTAGRAM
    assert detect_platform("https://youtu.be/abc") == Platform.YOUTUBE
    assert detect_platform("https://www.tiktok.com/@x/video/1") == Platform.TIKTOK
    assert detect_platform("https://www.douyin.com/video/1") == Platform.DOUYIN


def test_facebook_requires_fallback_chain():
    plan = build_plan("https://www.facebook.com/share/r/19b56K4KxL/")
    assert plan.platform == Platform.FACEBOOK
    assert [s.engine for s in plan.steps] == ["yt-dlp", "yt-dlp", "cobalt"]
    assert plan.steps[1].authenticated is True


def test_learning_only_and_provenance():
    plan = build_plan("https://youtu.be/abc")
    assert plan.phase == "learning_only"
    assert plan.preserve_provenance is True
    assert plan.transcript_policy == "native_subtitles_first_then_whisper"
