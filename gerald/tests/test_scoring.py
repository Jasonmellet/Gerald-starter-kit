from app.schemas import OpportunityScores


def test_overall_score_computation():
    expected = 0.30 * 80 + 0.25 * 70 + 0.20 * 60 + 0.15 * 50 + 0.10 * 40
    scores = OpportunityScores(
        urgency_score=80,
        fit_score=70,
        buyer_score=60,
        outreach_score=50,
        confidence_score=40,
        overall_score=expected,
        summary="Test opportunity",
        why_now="Testing formula",
        recommended_angle="Testing",
    )
    assert abs(scores.overall_score - expected) < 1e-6

