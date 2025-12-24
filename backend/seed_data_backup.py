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
        },
        {
            "name": "Comprehensive Psychological Assessment",
            "description": "Detailed psychological assessment report with structured sections",
            "template_type": "assessment",
            "is_default": False,
            "content": """PSYCHOLOGICAL ASSESSMENT REPORT

1. REPORT METADATA (Front Page)
1.1 Report Header
Clinic name: [dropdown: clinic_options]
Clinic address: [static]
Program name: [dropdown: Complex Developmental Behavioural Conditions Program, Psychology Services, Other]
AI_use: static_display

1.2 Client & Administrative Information
Client full name: [text: required]
Preferred name: [text]
Chart number: [text]
Date of birth: [date: required]
Age at assessment: [auto_calculated: read_only]
Date(s) of assessment: [date_multi: required]
Date of conference: [date]
Legal guardian(s): [text]
Assessing clinician(s): [multi_select: staff_list]
Other team members: [multi_select: Pediatrician, SLP, SW, etc.]
AI_use: insert_consistently

2. SUMMARY
2.1 Diagnostic Summary
Diagnosis: [table_rows: dropdown_options]
- Specific Learning Disorder – Reading
- Specific Learning Disorder – Written Expression
- Specific Learning Disorder – Mathematics
- ADHD
- ASD
- Intellectual Developmental Disorder
- Anxiety Disorder
- Selective Mutism
- Other
DSM code: [auto_fill]
Severity: [dropdown: Mild, Moderate, Severe]
Specifiers: [checkboxes: context_sensitive]
AI_use: rephrase_narrative, no_diagnosis_changes

2.2 Summary of Findings
Referral source: [dropdown]
Reason for referral: [checkboxes_text]
- Learning difficulties
- Attention concerns
- Anxiety / mood
- Language concerns
- Adaptive functioning
- Other
Strengths: [checkboxes_bullets]
Key concerns: [checkboxes]
AI_use: generate_cohesive_paragraph

3. SUPPORTING INFORMATION
3.1 Reason for Referral
Referring provider: [text]
Referral context: [dropdown: Multidisciplinary clinic, Pediatrician referral, School referral, Parent request]
Referral goals: [checkboxes]
AI_use: generate_standard_paragraph

3.2 Sources of Information
Sources: [multi_select_checklist]
- Parent interview
- Teacher interview
- File review
- Standardized testing
- Behavioural observation
- Questionnaires
AI_use: insert_standardized_sentence

3.3 Background Information
A. Presenting Concerns
Attention / Executive Function: [checklist_bullets]
Anxiety / Mood: [checklist_bullets]
Communication: [checklist_bullets]
Social functioning: [checklist_bullets]
Behaviour: [checklist_bullets]
Learning: [checklist_bullets]
AI_use: expand_paragraph_per_domain

B. Family History
Living situation: [dropdown]
Languages spoken at home: [multi_select]
Relevant family history: [checkboxes]
- Anxiety
- Depression
- Learning difficulties
- Speech/language delay
Recent stressors: [checkbox_text]
AI_use: generate_family_history_paragraph

C. Developmental & Medical History
Birth history: [dropdown]
Prenatal exposure: [checkboxes]
Medical concerns: [checkboxes]
Sensory/hearing concerns: [yes_no]
AI_use: generate_standardized_text

D. Educational History
Current grade: [dropdown]
School name: [text]
Supports received: [checkboxes]
- Learning support teacher
- 1:1 aide
- SLP
IEP: [yes_no]
Academic performance: [dropdown_per_domain]
AI_use: generate_educational_narrative

4. BEHAVIOURAL OBSERVATIONS
Observation checklist: [checklist]
- Eye contact
- Verbal responsiveness
- Anxiety signs
- Engagement
- Attention
Session context: [dropdown: Clinic, School, Home]
Optional notes: [bullets]
AI_use: convert_checklist_narrative

5. TESTS ADMINISTERED
Test list: [multi_select]
- WISC-V
- WIAT-III
- ABAS-3
- BASC-3
- BRIEF-2
- WSR-II
Test protocols: [file_upload: PDF/scan]
Score entry: [tables_or_upload]
AI_use: insert_standardized_descriptions, summarize_tables

6. TEST RESULTS & INTERPRETATION
6.1 Cognitive Functioning (WISC-V)
Score table: [structured_table]
- Index
- Standard score
- Percentile
- Qualitative descriptor
Validity concerns: [checkbox]
Non-verbal index preferred: [checkbox]
AI_use: generate_index_interpretation, insert_cautions

6.2 Academic Achievement (WIAT-III)
Subtest scores: [table]
Refusal/not administered: [checkboxes_per_subtest]
AI_use: generate_domain_academic_interpretation

6.3 Executive Functioning (BRIEF-2)
Parent T-scores: [table]
Teacher T-scores: [table]
Classification: [auto: Average, Elevated, Clinically Elevated]
AI_use: summarize_parent_teacher_patterns

6.4 Adaptive Behaviour (ABAS-3)
Parent tables: [table]
Teacher tables: [table]
Strength/weakness flags: [flags]
AI_use: generate_comparative_adaptive_narrative

7. SOCIAL / EMOTIONAL FUNCTIONING
Domain flags: [flags]
- Anxiety
- Depression
- Withdrawal
- Social skills
Severity: [dropdowns]
AI_use: generate_integrated_emotional_summary

8. DIAGNOSTIC IMPRESSIONS
Auto-generated: [from_diagnoses_findings]
Clinician approval: [checkbox]
AI_use: draft_diagnostic_rationale, clinician_edits

9. RELATIVE STRENGTHS & WEAKNESSES
Strengths: [checklist_custom_bullets]
Weaknesses: [checklist_custom_bullets]
AI_use: generate_concise_summary_lists

10. RECOMMENDATIONS
10.1 Education
Recommendation presets: [checkboxes]
- IEP
- Classroom accommodations
- Reader/scribe
- Modified workload
AI_use: insert_standardized_recommendation_paragraphs

10.2 Community / Therapy
SLP: [yes_no]
OT: [yes_no]
Counselling: [yes_no]
Resource links: [auto_fill]
AI_use: generate_community_support_section

11. STRATEGIES
Strategy library: [checkbox_driven]
- Classroom
- Home
- Homework
- Emotional regulation
Severity filtering: [auto]
AI_use: compile_organize_strategy_lists

12. CONCLUSION
Auto-generated: [content]
Clinician approval/edit: [checkbox]
AI_use: polished_closing_paragraph

13. APPENDICES
Appendix A: Report Card Review
Upload PDFs: [file_upload]
Bullet summaries: [bullets]

Appendix B: Detailed Recommendations
Auto-populated: [from_strategies]"""
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
