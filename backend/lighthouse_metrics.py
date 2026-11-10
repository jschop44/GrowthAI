"""Parse measured Lighthouse results without inventing missing scores or field data."""
import math

CATEGORIES = ('performance', 'accessibility', 'best-practices', 'seo')
METRICS = {
    'first_contentful_paint_ms': 'first-contentful-paint',
    'largest_contentful_paint_ms': 'largest-contentful-paint',
    'total_blocking_time_ms': 'total-blocking-time',
    'cumulative_layout_shift': 'cumulative-layout-shift',
    'speed_index_ms': 'speed-index',
    'total_resource_bytes': 'total-byte-weight',
    'main_thread_work_ms': 'mainthread-work-breakdown',
}
DIAGNOSTICS = ('color-contrast', 'image-aspect-ratio', 'image-size-responsive',
               'unsized-images', 'font-display', 'tap-targets', 'viewport',
               'document-title', 'meta-description', 'link-name', 'button-name', 'label')


def number(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def lighthouse_params(url, strategy, key=None):
    params = {'url': url, 'strategy': strategy, 'category': list(CATEGORIES)}
    if key:
        params['key'] = key
    return params


def parse_lighthouse(payload):
    lighthouse = payload.get('lighthouseResult') if isinstance(payload, dict) else None
    lighthouse = lighthouse if isinstance(lighthouse, dict) else {}
    audits = lighthouse.get('audits') or {}
    categories = lighthouse.get('categories') or {}
    if not isinstance(audits, dict) or not isinstance(categories, dict) or lighthouse.get('runtimeError'):
        return {'category_scores': {}, 'metrics': {}, 'diagnostics': [], 'measurement_status': 'unavailable'}
    scores, metrics, diagnostics = {}, {}, []
    for category in CATEGORIES:
        item = categories.get(category)
        value = item.get('score') if isinstance(item, dict) else None
        if number(value) and 0 <= value <= 1:
            scores[category] = round(value * 100)
            metrics['lighthouse_' + category.replace('-', '_') + '_score'] = scores[category]
    for label, key in METRICS.items():
        item = audits.get(key)
        value = item.get('numericValue') if isinstance(item, dict) else None
        if number(value) and value >= 0:
            metrics[label] = round(value, 3)
    for key in DIAGNOSTICS:
        item = audits.get(key)
        if not isinstance(item, dict) or item.get('scoreDisplayMode') in ('manual', 'notApplicable', 'error'):
            continue
        score = item.get('score')
        if not number(score) or not 0 <= score <= 1:
            continue
        details = item.get('details')
        items = details.get('items') if isinstance(details, dict) else None
        diagnostics.append({'id': key, 'name': str(item.get('title') or key)[:160],
            'status': 'passed' if score == 1 else 'needs_attention', 'score': round(score * 100),
            'affected_items': len(items) if isinstance(items, list) else None,
            'display_value': str(item.get('displayValue') or '')[:200], 'method': 'third_party_rendered_lab_check'})
    return {'category_scores': scores, 'metrics': metrics, 'diagnostics': diagnostics,
        'measurement_status': 'measured' if scores or metrics else 'unavailable',
        'category_coverage': {key: 'measured' if key in scores else 'not_returned' for key in CATEGORIES},
        'scope': 'Automated lab measurements and checks. These are not a visual design rating, complete accessibility certification or real-user field measurements.'}
