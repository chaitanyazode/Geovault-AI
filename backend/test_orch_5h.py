from app.core.database import SessionLocal
from app.security.context import UserContext, AuthorizedScope
from app.ai.orchestrator import UnifiedAIOrchestrator

db = SessionLocal()
user = UserContext(user_id='USR001', username='mining_eng', email='eng@geovault.internal', role='Mining Engineer', department='Mining', clearance_level='INTERNAL')
scope = AuthorizedScope(user_id='USR001', role='Mining Engineer', allowed_mines={'GEVRA', 'GV001'}, allowed_departments={'Mining', 'Geology'}, max_clearance='INTERNAL')

orch = UnifiedAIOrchestrator(db, user, scope)
res = orch.orchestrate("What was GEVRA's production in FY2024-25?")
print('Route:', res.query_type)
print('Summary:', res.summary)
print('Detailed Answer:', res.detailed_answer)
print('Facts:', res.structured_results['facts'][0] if res.structured_results else None)
print('Evidence count:', len(res.evidence))
