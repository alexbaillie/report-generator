"""Seed the Psycho-Educational and Sunny Hill CDBC report templates.

These are stored in the database (data/reports.db, git-ignored), so this script
makes them reproducible and recoverable: run it on a fresh install, or after a
database reset, to (re)create the templates.

Run from the backend/ directory:
    python seed_templates.py

Idempotent: a template whose name already exists is left untouched, so re-running
is safe and never duplicates. Base templates (Standard Intake, etc.) live in
seed_data.py; this script only adds the Psycho-Ed and CDBC templates.
"""
import json

from database.db import SessionLocal, init_db
from database.models import Template


# ---- field builders (match the app's JSON section-schema field vocabulary) ----
def _ph(field, placeholder):
    if placeholder:
        field["placeholder"] = placeholder
    return field


def text(label, placeholder=None):
    return _ph({"label": label, "type": "text"}, placeholder)


def textarea(label, placeholder=None):
    return _ph({"label": label, "type": "textarea"}, placeholder)


def date(label):
    return {"label": label, "type": "date"}


def date_multi(label):
    return {"label": label, "type": "date_multi"}


def select(label, options):
    return {"label": label, "type": "select", "options": options}


def checkboxes(label, options):
    return {"label": label, "type": "checkboxes", "options": options}


def table(label, placeholder):
    return {"label": label, "type": "table", "placeholder": placeholder}


def section(title, *fields):
    return {"title": title, "fields": list(fields)}


PSYCHED_TESTS = [
    "ABAS-3", "Achenbach (CBCL/TRF/YSR)", "ADHD-5 Rating Scales", "ASRS", "BASC-3", "Bayley-4",
    "Beery VMI-6", "BRIEF-2", "BRIEF-P", "Bracken-3:R", "CEFI", "CCTT", "CVLT-C", "D-KEFS", "DAS-II",
    "Feifer (Reading/Math/Writing)", "NEPSY-II", "PPVT-4", "MASC-2", "Rey Complex Figure", "SCARED",
    "SIB-R", "CTOPP-2", "WASI", "WAIS-IV", "WIAT-III / WIAT-4", "WISC-V", "WNV", "WPPSI-IV", "WRAML-3",
    "WSR-II", "Vanderbilt", "Vineland-3", "KTEA-3", "GORT-5", "TOWL-4", "Other",
]

PSYCHED = [
    section("Report Metadata (Front Page)",
            text("Report title", "Psycho-Educational Assessment Report"),
            textarea("Confidentiality statement"),
            text("Client full name"), text("Preferred name"),
            date("Date of birth"), date_multi("Date(s) of assessment"), date("Date of report"),
            date("Date of conference"),
            text("Chronological age"), text("Examiner"), text("Credentials"),
            textarea("Assessment team"), text("Copies to")),
    section("Reason for Referral",
            textarea("Referral source and reason"), textarea("Presenting concerns summary"),
            textarea("Purpose of the assessment"), textarea("Sources of information")),
    section("Presenting Concerns (as reported by parents)",
            textarea("Attention", "organization, hyperactivity, focus, planning, distractibility, following instructions"),
            textarea("Anxiety"), textarea("Communication / Socialization"),
            textarea("Behaviour", "frustration triggers, aggression, eating, sensory issues"),
            textarea("Learning")),
    section("Teacher's Perspective", textarea("Teacher's note (optional)")),
    section("Child's Perspective", textarea("Child's perspective (optional)")),
    section("Areas of Relative Strength & Interests",
            textarea("Reported strengths"), textarea("Interests and hobbies"),
            textarea("Recreational / community programs"), textarea("Effective strategies parents have found")),
    section("Family History",
            text("Where the child lives / who they live with"), text("Language of the home / ESL"),
            textarea("Parent education and occupations"), textarea("Recent / current family stressors"),
            textarea("Family history of learning or mental-health conditions"), textarea("Other relevant information")),
    section("Developmental & Medical History",
            textarea("Pregnancy and birth information"), textarea("Early infancy information"),
            textarea("Developmental milestones"), textarea("Hearing and vision testing"),
            textarea("Major illness, head injury, seizures, fevers"), textarea("Medication history and current use")),
    section("Educational History",
            text("Current school, grade, and program"), text("Designation and current supports (e.g., LAC)"),
            textarea("Most recent IEP major goals"), textarea("Extra-curricular programs at school"),
            textarea("Current extra-curricular tutoring"), textarea("Previous schools and programming"),
            textarea("Previous school concerns")),
    section("Previous Assessments & Interventions",
            table("Previous assessments", "Type, Clinician, Location, Date/Age, Key findings, Diagnoses/recommendations"),
            textarea("Previous interventions")),
    section("Tests Administered",
            checkboxes("Tests administered", PSYCHED_TESTS), textarea("Other tests or questionnaires")),
    section("Behavioural Observations",
            textarea("Behavioural observations", "presentation, glasses/medication, rapport, attention, language used")),
    section("Cognitive & Neuropsychological Results",
            table("Cognitive score table (WPPSI / WISC / WAIS)", "Index/Subtest, Score, Percentile, Range"),
            textarea("General cognitive interpretation"),
            table("Memory score table (WRAML-3 / CVLT-C)", "Index, Score, Percentile, Range"),
            textarea("Memory interpretation"),
            textarea("Visual-motor integration (VMI / Rey Complex Figure)"),
            textarea("Executive functioning (NEPSY-II, D-KEFS, BRIEF-2)")),
    section("Academic Achievement",
            table("Academic score table (WIAT / KTEA)", "Subtest, Score, Percentile, Range"),
            textarea("Reading"), textarea("Mathematics"), textarea("Written expression"),
            textarea("Phonological processing (CTOPP-2)")),
    section("Adaptive, Behavioural & Social-Emotional Functioning",
            table("Adaptive behaviour (ABAS-3)", "Scale, Parent, Teacher"),
            textarea("Adaptive functioning interpretation"),
            textarea("Behaviour rating scales (BASC-3, ASEBA)"),
            textarea("Anxiety measures (SCARED, MASC-2)"),
            textarea("ADHD measures (WSR-II, ADHD-5)")),
    section("Summary of Assessment Results",
            textarea("General cognitive abilities"), textarea("Adaptive functioning"),
            textarea("School achievement"), textarea("Visual-motor integration"), textarea("Memory"),
            textarea("Attention"), textarea("Executive functioning"),
            textarea("Behavioural, social, and emotional functioning"),
            textarea("Relative strengths"), textarea("Relative weaknesses / areas for improvement")),
    section("Diagnoses (DSM-5-TR)",
            table("Descriptors / diagnoses (DSM-5-TR)", "Code, Diagnosis/descriptor, Notes"),
            textarea("Developmental domains impacted",
                     "Physical, Communication, Social-Emotional, Academic, Self-Determination — none/mild/moderate/complex")),
    section("Highlighted Recommendations", textarea("Top 3-5 recommendations")),
    section("Recommendations",
            textarea("Follow-up meetings (doctor, school)"), textarea("Community support programs"),
            textarea("School programming and classroom placement"),
            textarea("Academic strategies (reading, math, writing, spelling)"),
            textarea("Home and classroom strategies"), textarea("Organization and technology supports"),
            textarea("Social skills and emotional support"),
            textarea("Self-regulation, anxiety, anger / frustration"),
            textarea("Sleep, exercise, and other"), textarea("Follow-up / reassessment")),
]

CDBC_TESTS = [
    "ABAS-3", "ADHD-5 Rating Scales", "ADOS-2", "ASRS", "Achenbach (CBCL/TRF)", "BASC-3", "Bayley-4",
    "Beery VMI-6", "BRIEF-2", "CVLT-C", "D-KEFS", "DAS-II", "MASC-2", "NEPSY-II", "PPVT-4",
    "Rey Complex Figure", "SCARED", "SIB-R", "Vineland-3", "WASI", "WAIS-IV", "WIAT-III / WIAT-4",
    "WISC-V", "WPPSI-IV", "WRAML-3", "WSR-II", "Weiss Symptom Record", "Other",
]

CDBC = [
    section("Report Metadata (Front Page)",
            text("Report title", "Psychology Assessment Report"),
            text("Program", "Complex Developmental Behavioural Conditions Program"),
            text("Client full name"), text("Chart number"),
            date("Date of birth"), date_multi("Date(s) of assessment"), date("Date of report"),
            date("Date of conference"),
            text("Age at assessment"), text("Legal guardian"),
            textarea("Sunny Hill team",
                     "Developmental Pediatrician, Psychologist, Assessing Clinician, SLP, OT, PT, Social worker, Case manager")),
    section("Diagnostic Summary (DSM-5-TR)",
            table("Diagnoses (DSM-5-TR)", "Code, Diagnosis/descriptor, Notes"),
            textarea("Other diagnoses (see multidisciplinary report)")),
    section("Summary of Findings",
            textarea("Reason for referral and previous diagnoses"), textarea("Cognitive ability"),
            textarea("Academic ability"), textarea("Behaviour"), textarea("Social and emotional"),
            textarea("Summary"), textarea("Main recommendations"), textarea("School-based accommodations")),
    section("Summary of Assessment Results",
            textarea("General cognitive abilities"), textarea("Adaptive functioning"),
            textarea("School achievement"), textarea("Visual-motor integration"), textarea("Memory"),
            textarea("Attention"), textarea("Executive functioning"),
            textarea("Behavioural, social, and emotional functioning")),
    section("Highlighted Recommendations", textarea("Highlighted recommendations only")),
    section("Resources", textarea("Key websites and resources")),
    section("Reason for Referral", textarea("Reason for referral")),
    section("Sources of Information",
            textarea("Sources of information", "parent interview, review of records, standardized testing, observation")),
    section("Presenting Concerns (as provided by parents)",
            textarea("Attention / Impulsivity / Activity / Executive Functions"),
            textarea("Anxiety / Mood"), textarea("Communication"), textarea("Social concerns"),
            textarea("Behaviour"), textarea("Learning"), textarea("School-related")),
    section("Areas of Relative Strength & Interests",
            textarea("Reported strengths"), textarea("Interests and hobbies"),
            textarea("Recreational / community programs"), textarea("Effective strategies parents have found")),
    section("Family History",
            text("Where the child lives / who they live with"), text("Language / ESL"),
            text("If in care, number of foster placements"), textarea("Parent / caregiver occupations"),
            textarea("Recent / current family stressors"), textarea("Other relevant information")),
    section("Developmental & Medical History",
            textarea("Pregnancy and birth information"), textarea("Developmental milestones"),
            textarea("Early infancy"), textarea("Hearing and vision"),
            textarea("Major illnesses, head injury, fevers, or seizures"),
            textarea("Sleep"), textarea("Screen time"), textarea("Medication"), textarea("Family history")),
    section("Educational History",
            text("Current school, grade, and program"), text("Designation and current supports"),
            textarea("Most recent IEP major goals"), textarea("Extra-curricular programs at school"),
            textarea("Current extra-curricular tutoring"), textarea("Previous schools and programming"),
            textarea("Previous school concerns")),
    section("Previous Assessments & Interventions",
            table("Previous assessments", "Type, Clinician, Date, Key findings, Diagnoses/recommendations"),
            textarea("Previous interventions")),
    section("Behavioural Observations",
            textarea("Behavioural observations",
                     "presentation, stated age, rapport, language used, eye contact and conversation")),
    section("Tests Administered",
            checkboxes("Tests administered", CDBC_TESTS), textarea("Parent / teacher / self-report measures")),
    section("Cognitive, Memory & Academic Results",
            table("Cognitive scores (WPPSI / WISC / WAIS)", "Index/Subtest, Score, Percentile, Range"),
            textarea("General cognitive interpretation"), textarea("Validity testing"),
            table("Memory scores (WRAML-3)", "Index, Score, Percentile, Range"),
            textarea("Memory interpretation"), textarea("Academic achievement")),
    section("Recommendations", textarea("Recommendations")),
]


TEMPLATES = [
    ("Psycho-Educational Assessment - Boy", "psychoeducational",
     "Psycho-educational assessment report (boy)", PSYCHED),
    ("Psycho-Educational Assessment - Girl", "psychoeducational",
     "Psycho-educational assessment report (girl)", PSYCHED),
    ("SunnyHill CDBC Psychology Assessment - Boy", "cdbc",
     "Sunny Hill CDBC psychology assessment report (boy)", CDBC),
    ("SunnyHill CDBC Psychology Assessment - Girl", "cdbc",
     "Sunny Hill CDBC psychology assessment report (girl)", CDBC),
]


def seed_templates():
    """Insert the Psycho-Ed and CDBC templates if they are not already present."""
    init_db()
    db = SessionLocal()
    try:
        existing = {name for (name,) in db.query(Template.name).all()}
        added = 0
        for name, template_type, description, schema in TEMPLATES:
            if name in existing:
                print(f"Skipping (already exists): {name}")
                continue
            db.add(Template(
                name=name,
                description=description,
                template_type=template_type,
                content=json.dumps(schema),
                is_default=False,
            ))
            db.commit()
            added += 1
            print(f"Added: {name} "
                  f"({len(schema)} sections, {sum(len(s['fields']) for s in schema)} fields)")
        print(f"Done. {added} template(s) added, {len(TEMPLATES) - added} already present.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_templates()
