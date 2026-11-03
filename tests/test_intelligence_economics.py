"""Financial scenario tests use explicit inputs, not invented business revenue."""
from backend.main import IntelligenceEconomicsRequest, intelligence_economics

def test_margin_aware_scenario():
    result=intelligence_economics(IntelligenceEconomicsRequest(
        monthly_visits=10000,conversion_rate_percent=2,
        average_order_value=100,gross_margin_percent=50,
        conversion_lift_percent=10,one_time_cost=1000,monthly_recurring_cost=50))
    assert result['baseline_annual_revenue']==240000
    assert result['incremental_annual_revenue_scenario']==24000
    assert result['incremental_annual_gross_profit_scenario']==12000
    assert result['year_one_cost']==1600
    assert result['year_one_net_profit_scenario']==10400
    assert result['year_one_roi_percent']==650
    assert result['scenario_only'] is True

def test_zero_cost_and_zero_uplift():
    result=intelligence_economics(IntelligenceEconomicsRequest(
        monthly_visits=0,conversion_rate_percent=0,
        average_order_value=0,conversion_lift_percent=0,one_time_cost=0))
    assert result['year_one_roi_percent'] is None
    assert result['payback_months'] is None
