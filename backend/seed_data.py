"""
Seed database with initial templates
"""
from database.db import SessionLocal, init_db
from database.models import Template

def seed_templates():
    """Create default report templates"""
    db = SessionLocal()
    
    templates = [
        {
            "name": "Standard Intake Assessment",
            "description": "Comprehensive initial assessment template",
            "template_type": "intake",
            "is_default": True,
            "content": """Generate a professional psychological intake assessment report with the following sections:

1. IDENTIFYING INFORMATION
   - Patient demographics
   - Referral source
   - Date of assessment

2. PRESENTING PROBLEM
   - Chief complaint
   - History of present illness
   - Onset and duration

3. MENTAL STATUS EXAMINATION
   - Appearance and behavior
   - Speech and thought process
   - Mood and affect
   - Cognitive functioning

4. CLINICAL HISTORY
   - Psychiatric history
   - Medical history
   - Substance use history
   - Family history

5. PSYCHOSOCIAL HISTORY
   - Developmental history
   - Educational/occupational history
   - Social relationships
   - Current living situation

6. DIAGNOSTIC IMPRESSIONS
   - Primary diagnosis
   - Differential diagnoses
   - Severity assessment

7. TREATMENT RECOMMENDATIONS
   - Recommended interventions
   - Frequency of sessions
   - Goals of treatment
   - Prognosis

Please write in a professional, clinical tone using third person. Base the report on the provided documents and additional information."""
        },
        {
            "name": "Progress Note",
            "description": "Session progress note template",
            "template_type": "progress",
            "is_default": False,
            "content": """Generate a concise progress note with the following sections:

1. SESSION INFORMATION
   - Date and duration
   - Session number

2. SUBJECTIVE
   - Patient's reported mood and symptoms
   - Recent events and stressors
   - Progress toward goals

3. OBJECTIVE
   - Clinical observations
   - Mental status
   - Behavior during session

4. ASSESSMENT
   - Clinical impressions
   - Progress evaluation
   - Symptom changes

5. PLAN
   - Interventions used
   - Homework assigned
   - Next session goals
   - Treatment plan modifications

Use clear, professional language. Keep it concise but comprehensive."""
        },
        {
            "name": "Psychological Evaluation",
            "description": "Comprehensive psychological evaluation template",
            "template_type": "evaluation",
            "is_default": False,
            "content": """Generate a comprehensive psychological evaluation report with:

1. REASON FOR REFERRAL
2. BACKGROUND INFORMATION
3. BEHAVIORAL OBSERVATIONS
4. TESTS ADMINISTERED
5. TEST RESULTS AND INTERPRETATION
   - Cognitive functioning
   - Emotional functioning
   - Personality assessment
   - Behavioral assessment
6. SUMMARY AND DIAGNOSTIC IMPRESSIONS
7. RECOMMENDATIONS

Include test scores, interpretations, and clinical integration. Use professional psychological terminology."""
        },
        {
            "name": "Discharge Summary",
            "description": "Treatment discharge summary template",
            "template_type": "discharge",
            "is_default": False,
            "content": """Generate a discharge summary with:

1. TREATMENT SUMMARY
   - Admission date and reason
   - Length of treatment
   - Treatment modalities used

2. COURSE OF TREATMENT
   - Progress made
   - Interventions provided
   - Response to treatment

3. DISCHARGE STATUS
   - Current symptoms
   - Functional status
   - Mental status at discharge

4. DISCHARGE DIAGNOSIS
5. MEDICATIONS AT DISCHARGE
6. FOLLOW-UP RECOMMENDATIONS
   - Continuing care needs
   - Referrals made
   - Relapse prevention plan

Write in a clear, professional manner summarizing the entire treatment episode."""
        }
    ]
    
    for template_data in templates:
        # Check if template already exists
        existing = db.query(Template).filter(Template.name == template_data["name"]).first()
        if not existing:
            template = Template(**template_data)
            db.add(template)
            print(f"Created template: {template_data['name']}")
        else:
            print(f"Template already exists: {template_data['name']}")
    
    db.commit()
    db.close()
    print("\nSeed data created successfully!")

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Seeding templates...")
    seed_templates()
