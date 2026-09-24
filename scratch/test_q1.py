import requests

res = requests.post(
    'http://localhost:8000/api/v1/intelligence/natural-query',
    json={'query': "What was GEVRA's production in FY2024-25?"},
    headers={'X-User-ID': 'USR001'},
    timeout=120
)
print('Status:', res.status_code)
data = res.json()
print('Route:', data.get('query_type'))
print('Summary:', data.get('summary'))
print('Detailed Answer:\n', data.get('detailed_answer'))
facts = data.get('structured_results', {}).get('facts', [])
print('Primary Fact:', facts[0] if facts else None)
