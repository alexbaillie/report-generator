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
            "description": "Comprehensive neuropsychological assessment template",
            "template_type": "evaluation",
            "is_default": True,
            "content": """Generate a professional neuropsychological report following this exact structure:

Psych Report Template

PATIENT
Name:
Chart number:
Date of birth:
Date of assessment:
Age at assessment:	
Date of conference:	
Legal guardian:	
		
TEAM
Developmental Pediatrician:	
Psychologist:	
Assessing Clinician:	
Speech Language Pathologist:	
Social worker:	
Case manager:   

CONTENTS

SUMMARIES
Diagnostic summary:
Summary of findings:

RECOMMENDATIONS FOR SERVICE

STRATEGIES
Allowances:
Accommodations:
Instructional Strategies:

SUPPORTING INFORMATION
Reason for referral:
Sources of information:
Background information:
- Presenting concerns (as provided by...)
- Family History
- Developmental and Medical History
- Educational History
- Previous Schools and Programming
- Previous Assessments & Interventions
Behavioural Observations:
Tests administered:
Parent/teacher report measures administered:
Information on the interpretation of test scores:

APPENDICES 

Please fill in each section with appropriate content based on the provided documents and additional information. Use professional psychological terminology and ensure the report is comprehensive and clinically accurate."""
        }
    ]
    
    for template_data in templates:
        # Check if template already exists
        existing = db.query(Template).filter(Template.name == template_data["name"]).first()
        if existing:
            # Update existing template
            for key, value in template_data.items():
                if key != "name":  # Don't update name
                    setattr(existing, key, value)
            db.commit()
            print(f"Updated template: {template_data['name']}")
        else:
            template = Template(**template_data)
            db.add(template)
            print(f"Created template: {template_data['name']}")
    
    db.commit()
    db.close()
    print("\nSeed data created successfully!")

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("Seeding templates...")
    seed_templates()