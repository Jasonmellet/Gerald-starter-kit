from app.schemas import DraftOutput
from app.constants import DraftChannel


def test_draft_output_basic_constraints():
    dm = DraftOutput(
        channel=DraftChannel.DM,
        message_type="dm_intro",
        subject=None,
        body="Hey, saw your post about needing more pipeline. I help founders fix that with focused GTM and light automation. Worth a quick chat?",
        personalization_notes="Mention their specific tweet about pipeline if available.",
        cta="Offer a short call to share 1-2 ideas.",
        recommended_angle="Pipeline and GTM support",
    )
    assert dm.channel == DraftChannel.DM
    assert "quick chat" in dm.body.lower()
    assert dm.subject is None

