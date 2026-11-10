"""Deterministic page diagnostics. HTML signals are not visual or lab measurements."""
import json
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse


SECURITY_FINDINGS = frozenset({'mixed_content', 'secure_forms'})


def recommendation_order(finding):
    """Keep observed security failures ahead of cosmetic score opportunities."""
    return (finding.get('id') not in SECURITY_FINDINGS,
            finding.get('priority') != 'high', -finding.get('weight', 0))


def enrich_quality(result, soup, html, url):
    images = soup.find_all('img')
    scripts = soup.find_all('script', src=True)
    forms = soup.find_all('form')
    missing_dimensions = sum(not (str(x.get('width', '')).isdigit() and str(x.get('height', '')).isdigit() and int(x['width']) > 0 and int(x['height']) > 0) for x in images)
    decorative = sum(x.has_attr('alt') and not x['alt'].strip() for x in images)
    invalid_schema = 0
    for x in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(x.string or x.get_text())
            if not isinstance(data, (dict, list)) or not data:
                invalid_schema += 1
        except (ValueError, TypeError):
            invalid_schema += 1
    insecure_assets = sum(urljoin(url, x.get(attr, '')).startswith('http://') for tag, attr in [('img', 'src'), ('script', 'src'), ('link', 'href'), ('iframe', 'src')] for x in soup.find_all(tag, **{attr: True}) if tag != 'link' or 'stylesheet' in (x.get('rel') or [])) if urlparse(url).scheme == 'https' else 0
    insecure_forms = sum(urlparse(urljoin(url, x.get('action') or url)).scheme != 'https' for x in forms)
    blocking = sum(not (x.has_attr('async') or x.has_attr('defer') or x.get('type') == 'module') for x in scripts if x.find_parent('head'))
    empty_links = sum(not (a.get_text(' ', strip=True) or a.get('aria-label') or a.get('aria-labelledby') or any(i.get('alt', '').strip() for i in a.find_all('img'))) for a in soup.find_all('a', href=True))
    metrics = {
        'html_document_bytes_utf8': len(html.encode('utf-8')),
        'images_without_intrinsic_dimensions': missing_dimensions,
        'decorative_images': decorative,
        'render_blocking_head_scripts': blocking,
        'mixed_content_references': insecure_assets,
        'insecure_form_actions': insecure_forms,
        'invalid_json_ld_blocks': invalid_schema,
        'empty_link_names': empty_links,
        'external_script_count': sum(urlparse(urljoin(url, x['src'])).hostname != urlparse(url).hostname for x in scripts),
    }
    definitions = [
        ('image_dimensions', 'Image layout stability signals', missing_dimensions == 0, 'Visual delivery', missing_dimensions, 'Set positive image width and height, or reserve equivalent space with a tested aspect ratio.'),
        ('blocking_scripts', 'Render-blocking head scripts', blocking == 0, 'Technical performance', blocking, 'Defer noncritical scripts; verify dependencies and measure before and after in a lab test.'),
        ('mixed_content', 'Secure embedded resources', insecure_assets == 0, 'Security', insecure_assets, 'Replace HTTP resource references with verified HTTPS URLs.'),
        ('secure_forms', 'Secure form destinations', insecure_forms == 0, 'Security', insecure_forms, 'Send forms to an approved HTTPS destination and test submission handling.'),
        ('schema_validity', 'Parseable structured data', invalid_schema == 0, 'Search and discoverability', invalid_schema, 'Repair malformed JSON-LD, then validate the schema and business facts.'),
        ('accessible_links', 'Accessible link names', empty_links == 0, 'Accessibility', empty_links, 'Give each link a meaningful visible or accessible name describing its destination.'),
        ('main_landmark', 'Main content landmark', bool(soup.find('main') or soup.find(attrs={'role': 'main'})), 'Accessibility', None, 'Wrap primary page content in a semantic main landmark.'),
    ]
    timestamp = datetime.now(timezone.utc).isoformat()
    for key, name, passed, category, count, recommendation in definitions:
        result['findings'].append({'id': key, 'name': name, 'passed': passed, 'weight': 0, 'category': category,
            'priority': 'passed' if passed else 'high' if category == 'Security' else 'medium',
            'recommendation': recommendation, 'implementation_steps': [recommendation, 'Verify the change on mobile and desktop before publishing.'],
            'verification': 'Inspect source and browser behavior; repeat the relevant audit.',
            'evidence': {'source_url': url, 'observed_at': timestamp, 'count': count, 'method': 'static_html'},
            'cost_savings': {'status': 'not_estimated', 'annual_usd': None, 'reason': 'No verified local peer operating costs or business labor measurements supplied.'}})
    # Empty alt attributes are valid for decorative images. Missing attributes are distinct.
    alt_finding = next(x for x in result['findings'] if x['id'] == 'image_alt')
    missing_alt = sum(not x.has_attr('alt') for x in images)
    alt_finding['passed'] = missing_alt == 0
    result['observations']['images_missing_alt'] = missing_alt
    result['observations'].update(metrics)
    result['score'] = sum(x['weight'] for x in result['findings'] if x['passed'])
    for finding in result['findings']:
        finding.setdefault('evidence', {'source_url': url, 'observed_at': timestamp, 'method': 'static_html'})
        finding.setdefault('cost_savings', {'status': 'not_estimated', 'annual_usd': None,
            'reason': 'Local, same-niche cost data is unavailable. Any financial scenario shown separately uses illustrative assumptions.'})
    result['measurement_coverage'] = {
        'static_html': 'measured', 'visual_design_quality': 'not_measured',
        'mobile_rendering': 'not_measured', 'core_web_vitals': 'not_measured_by_html_audit',
        'whole_site_navigation': 'not_measured', 'local_peer_operating_costs': 'not_available',
    }
    result['category_metrics'] = [
        {'category': category, 'checks': len(items), 'passed': sum(x['passed'] is True for x in items),
         'scope': 'Static page indicators; not a rendered design or user-experience score'}
        for category in sorted({x.get('category', 'Core on-page checks') for x in result['findings']})
        if (items := [x for x in result['findings'] if x.get('category', 'Core on-page checks') == category])
    ]
    return result


def local_peer_evidence(findings, competitors, industry, radius_miles):
    """Attach observed local peer prevalence; never infer competitor finances."""
    for finding in findings:
        eligible = [c for c in competitors if c.get('status') == 'audited'
                    and isinstance(c.get('distance_miles'), (float, int)) and 0 <= c['distance_miles'] <= radius_miles]
        observations = [(c, next((f for f in c.get('findings', []) if f.get('id') == finding['id'] and isinstance(f.get('passed'), bool)), None)) for c in eligible]
        observations = [(c, f) for c, f in observations if f is not None]
        finding['local_peer_comparison'] = {'industry': industry, 'radius_miles': radius_miles,
            'sample_size': len(observations), 'passing_count': sum(f['passed'] for _, f in observations),
            'sources': [{'name': c.get('name'), 'url': c.get('website'), 'distance_miles': c['distance_miles']} for c, _ in observations],
            'confidence': 'limited_listing_classification',
            'note': 'Nearby listings were selected by niche; individual business classification and costs are not independently verified.'}
        finding['cost_savings'] = {'status': 'not_estimated', 'annual_usd': None,
            'reason': 'Peer website features do not reveal staff hours, supplier bills, labor rates or causal cost savings. Verified operating data is required.'}
