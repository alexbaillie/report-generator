import os
import sys
import json

# Ensure backend root is on sys.path so 'database' package can be imported when running as a script
CURR_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURR_DIR, '..'))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from database.db import SessionLocal
from database.models import Template


def sections_schema():
    s = []
    # 1. REPORT METADATA (Front Page)
    s.append({
        "title": "Report Metadata (Front Page)",
        "fields": [
            {"label": "Program name", "type": "select", "options": [
                "Complex Developmental Behavioural Conditions Program",
                "Psychology Services",
                "Other"
            ]},
            {"label": "Other program name (if Other)", "type": "text"},
            # Removed Clinic address and Clinic logo per request
        ]
    })
    # 1.2 Client & Administrative Information
    s.append({
        "title": "Client & Administrative Information",
        "fields": [
            {"label": "Client full name", "type": "text", "required": True},
            {"label": "Preferred name", "type": "text"},
            {"label": "Chart number", "type": "text"},
            {"label": "Date of birth", "type": "date", "required": True},
            {"label": "Age at assessment", "type": "text"},
            {"label": "Date(s) of assessment", "type": "date_multi", "required": True},
            {"label": "Date of conference", "type": "date"},
            {"label": "Legal guardian(s)", "type": "text"},
            {"label": "Assessing clinician(s)", "type": "text"},
            {"label": "Other team members", "type": "text"}
        ]
    })
    # 2. SUMMARY - 2.1 Diagnostic Summary
    s.append({
        "title": "Diagnostic Summary",
        "fields": [
            {"label": "Diagnoses", "type": "multi_select", "options": [
                "Specific Learning Disorder – Reading",
                "Specific Learning Disorder – Written Expression",
                "Specific Learning Disorder – Mathematics",
                "ADHD",
                "ASD",
                "Intellectual Developmental Disorder",
                "Anxiety Disorder",
                "Selective Mutism",
                "Other"
            ]}
        ]
    })
    # 2.2 Summary of Findings
    s.append({
        "title": "Summary of Findings",
        "fields": [
            {"label": "Referral source", "type": "select", "options": ["Parent","School","Pediatrician","Clinic","Other"]},
            {"label": "Strengths", "type": "checkboxes", "options": ["Cognitive","Academic","Social","Emotional","Adaptive","Other"]},
            {"label": "Strengths details", "type": "textarea"},
            {"label": "Key concerns", "type": "checkboxes", "options": ["Attention","Anxiety","Mood","Learning","Behaviour","Communication","Other"]}
        ]
    })
    # 3. SUPPORTING INFORMATION
    s.append({
        "title": "Reason for Referral",
        "fields": [
            {"label": "Referring provider", "type": "text"},
            {"label": "Referral context", "type": "select", "options": [
                "Multidisciplinary clinic","Pediatrician referral","School referral","Parent request"
            ]},
            {"label": "Referral goals", "type": "checkboxes", "options": ["Assessment","Diagnosis","School support","Therapy planning","Other"]}
        ]
    })
    s.append({
        "title": "Sources of Information",
        "fields": [
            {"label": "Sources", "type": "checkboxes", "options": [
                "Parent interview","Teacher interview","File review","Standardized testing","Behavioural observation","Questionnaires"
            ]}
        ]
    })
    # 3.3 Background Information - domains
    s.append({
        "title": "Presenting Concerns",
        "fields": [
            {"label": "Domains", "type": "checkboxes", "options": [
                "Attention / Executive Function","Anxiety / Mood","Communication","Social functioning","Behaviour","Learning"
            ]},
            {"label": "Notes per domain", "type": "textarea"}
        ]
    })
    s.append({
        "title": "Family History",
        "fields": [
            {"label": "Living situation", "type": "select", "options": ["Two parents","Single parent","Shared custody","Other"]},
            {"label": "Languages at home", "type": "multi_select", "options": []},
            {"label": "Relevant family history", "type": "checkboxes", "options": [
                "Anxiety","Depression","Learning difficulties","Speech/language delay"
            ]},
            {"label": "Recent stressors", "type": "textarea"}
        ]
    })
    s.append({
        "title": "Developmental & Medical History",
        "fields": [
            {"label": "Birth history", "type": "select", "options": ["Uncomplicated","Complications","Unknown"]},
            {"label": "Prenatal exposure", "type": "checkboxes", "options": ["Alcohol","Tobacco","Medications","Other","None"]},
            {"label": "Exposure Frequency", "type": "select", "options": [
                "None",
                "One-time",
                "Occasional",
                "Weekly",
                "Daily",
                "Unknown",
                "Other"
            ]},
            {"label": "Medical concerns", "type": "checkboxes", "options": ["Seizures","Head injury","Chronic illness","None","Other"]},
            {"label": "Sensory/hearing concerns", "type": "select", "options": ["Yes","No","Unknown"]}
        ]
    })
    s.append({
        "title": "Educational History",
        "fields": [
            {"label": "Current grade", "type": "select", "options": ["K","1","2","3","4","5","6","7","8","9","10","11","12","Graduated High School","College / University","Graduate School","Not Currently in School"]},
            {"label": "School name", "type": "text"},
            {"label": "Supports received", "type": "checkboxes", "options": [
                "Learning support teacher","1:1 aide","SLP","IEP"
            ]},
            {"label": "Academic performance", "type": "textarea"}
        ]
    })
    # 4. BEHAVIOURAL OBSERVATIONS
    s.append({
        "title": "Behavioural Observations",
        "fields": [
            {"label": "Observation checklist", "type": "checkboxes", "options": [
                "Eye contact","Verbal responsiveness","Anxiety signs","Engagement","Attention"
            ]},
            {"label": "Session context", "type": "select", "options": ["Clinic","School","Home"]},
            {"label": "Observation notes", "type": "textarea"}
        ]
    })
    # 5. TESTS ADMINISTERED
    s.append({
        "title": "Tests Administered",
        "fields": [
            {"label": "Tests", "type": "multi_select", "options": [
                "WISC-V","WIAT-III","ABAS-3","BASC-3","BRIEF-2","WSR-II"
            ]},
            {"label": "Upload test protocols", "type": "file"},
            {"label": "Scores (tables or summary)", "type": "table"}
        ]
    })
    # 6. TEST RESULTS & INTERPRETATION
    s.append({
        "title": "Cognitive Functioning (WISC-V)",
        "fields": [
            {"label": "Index table", "type": "table", "placeholder": "Index, Standard score, Percentile, Descriptor"},
            {"label": "Validity concerns", "type": "checkbox"},
            {"label": "Non-verbal index preferred", "type": "checkbox"}
        ]
    })
    # Removed individual test interpretation sections; upload and free-form tables handled in UI
    # 7. SOCIAL / EMOTIONAL FUNCTIONING
    s.append({
        "title": "Social / Emotional Functioning",
        "fields": [
            {"label": "Domain flags", "type": "checkboxes", "options": [
                "Anxiety","Depression","Withdrawal","Social skills"
            ]},
            {"label": "Severity", "type": "select", "options": ["Average","Elevated","Clinically Elevated"]}
        ]
    })
    # 8. DIAGNOSTIC IMPRESSIONS
    s.append({
        "title": "Diagnostic Impressions",
        "fields": [
            {"label": "Auto-generated rationale", "type": "textarea"},
            {"label": "Clinician approved", "type": "checkbox"}
        ]
    })
    # 9. RELATIVE STRENGTHS & WEAKNESSES
    s.append({
        "title": "Relative Strengths & Weaknesses",
        "fields": [
            {"label": "Strengths", "type": "checkboxes", "options": ["Attention","Memory","Language","Visual-spatial","Executive","Academic"]},
            {"label": "Weaknesses", "type": "checkboxes", "options": ["Attention","Memory","Language","Visual-spatial","Executive","Academic"]},
            {"label": "Custom bullets", "type": "textarea"}
        ]
    })
    # 10. RECOMMENDATIONS
    s.append({
        "title": "Education Recommendations",
        "fields": [
            {"label": "Education recommendations", "type": "checkboxes", "options": [
                "IEP",
                "Classroom accommodations",
                "Reader/scribe",
                "Modified workload"
            ]}
        ]
    })
    s.append({
        "title": "Community / Therapy Recommendations",
        "fields": [
            {"label": "SLP", "type": "checkbox"},
            {"label": "OT", "type": "checkbox"},
            {"label": "Counselling", "type": "checkbox"},
            {"label": "Resource links", "type": "textarea"}
        ]
    })
    # 11. STRATEGIES
    s.append({
        "title": "Strategies",
        "fields": [
            {"label": "Strategy category", "type": "select", "options": [
                "Classroom", "Home", "Homework", "Emotional regulation", "Other"
            ]},
            {"label": "Strategy suggestions", "type": "multi_select", "options": [
                "Preferential seating",
                "Extra time",
                "Visual schedules",
                "Chunking tasks",
                "Frequent breaks",
                "Noise-cancelling headphones",
                "Simplified instructions",
                "Graphic organizers",
                "Task checklist",
                "Timer for tasks",
                "Movement breaks",
                "Positive reinforcement system",
                "Social stories/practice",
                "Emotion regulation toolkit",
                "Homework planner",
                "Reduced homework load",
                "Reading supports",
                "Writing scaffolds",
                "Math manipulatives",
                "OT/SLP strategies",
                "Other"
            ]},
            {"label": "Strategy details", "type": "textarea"}
        ]
    })
    # 12. CONCLUSION
    s.append({
        "title": "Conclusion",
        "fields": [
            {"label": "Auto-generated conclusion", "type": "textarea"},
            {"label": "Clinician edits", "type": "textarea"}
        ]
    })
    # 13. APPENDICES
    s.append({
        "title": "Appendix A: Report Card Review",
        "fields": [
            {"label": "Upload PDFs or bullet summaries", "type": "file"},
            {"label": "Notes", "type": "textarea"}
        ]
    })
    s.append({
        "title": "Appendix B: Detailed Recommendations",
        "fields": [
            {"label": "Strategy details", "type": "textarea"}
        ]
    })
    return s


def main():
    db = SessionLocal()
    try:
        ts = db.query(Template).order_by(Template.id.asc()).all()
        if not ts:
            print("No templates found")
            return
        t = ts[0]
        t.content = json.dumps(sections_schema())
        db.add(t)
        db.commit()
        print(f"Updated template ID {t.id} with JSON schema sections={len(json.loads(t.content))}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
