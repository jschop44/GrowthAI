"""Reported outcomes must not be promoted to verified facts."""
from unittest.mock import patch
from backend.main import IntelligenceFeedbackRequest, intelligence_feedback

def test_feedback_stored_as_unverified():
    request=IntelligenceFeedbackRequest(
        website='https://example.com',recommendation_id='contact_form',
        improved=True,source='manual follow-up')
    with patch('backend.main.validate_url',return_value='https://example.com'), \
         patch('backend.learning_engine.store',return_value={'stored':True,'persistent':True,'storage':'postgres'}) as save:
        response=intelligence_feedback(request)
    args,kwargs=save.call_args
    assert args[0]=='https://example.com'
    assert args[1]=='recommendation_outcome'
    assert args[2]['improved'] is True
    assert args[2]['causal_claim'] is False
    assert kwargs['verified'] is False
    assert response['verification']=='user_reported_unverified'
    assert response['accepted'] is True
