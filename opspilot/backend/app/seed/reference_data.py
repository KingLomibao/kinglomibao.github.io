"""
Static reference data for Ironbridge Field Operations, the fictional
company OpsPilot models.

Keeping this as plain Python data (rather than scattering role names,
qualification names, and requirement rules across the seed script) is
what the "no magic strings" guideline means in practice: every other
part of the codebase refers to a role or qualification by its `code`,
and this is the one place that code is defined.
"""

from app.models.enums import RoleCategory, SiteStatus

ROLES = [
    {"code": "FIELD_TECH", "name": "Field Technician", "category": RoleCategory.TECHNICAL},
    {"code": "SR_FIELD_TECH", "name": "Senior Field Technician", "category": RoleCategory.TECHNICAL},
    {"code": "ELEC_TECH", "name": "Electrical Technician", "category": RoleCategory.TECHNICAL},
    {"code": "MECH_TECH", "name": "Mechanical Technician", "category": RoleCategory.TECHNICAL},
    {"code": "INST_TECH", "name": "Instrument Technician", "category": RoleCategory.TECHNICAL},
    {"code": "SITE_SUPV", "name": "Site Supervisor", "category": RoleCategory.SUPERVISORY},
    {"code": "OPS_SUPV", "name": "Operations Supervisor", "category": RoleCategory.SUPERVISORY},
]

# Approximate headcount to generate per role across the whole company.
# Sums to ~250 employees, matching the target company size.
ROLE_HEADCOUNT = {
    "FIELD_TECH": 90,
    "SR_FIELD_TECH": 40,
    "ELEC_TECH": 30,
    "MECH_TECH": 30,
    "INST_TECH": 25,
    "SITE_SUPV": 20,
    "OPS_SUPV": 15,
}

QUALIFICATIONS = [
    {"code": "SITE_INDUCTION", "name": "Site Safety Induction", "description": "General site safety orientation, required at every operational site."},
    {"code": "FIRST_AID", "name": "First Aid & CPR Certification", "description": "Basic first aid and CPR competency."},
    {"code": "WORK_HEIGHT", "name": "Working at Height Certification", "description": "Authorization to perform work above standard fall-risk thresholds."},
    {"code": "CONFINED_SPACE", "name": "Confined Space Entry Certification", "description": "Authorization to enter and work in confined spaces."},
    {"code": "ELEC_SAFETY", "name": "Electrical Safety Authorization", "description": "Authorization to work on or near energized electrical equipment."},
    {"code": "EQUIP_AUTH", "name": "Equipment Operation Authorization", "description": "Authorization to operate site heavy equipment."},
    {"code": "INSTR_CAL", "name": "Instrumentation Calibration Certification", "description": "Competency in calibrating and testing field instrumentation."},
]

# Mandatory qualifications per role. The eligibility engine reads this
# relationship from the database (RoleQualificationRequirement), never
# from this dict directly - it lives here only because this is where
# the seed script builds those database rows from.
ROLE_QUALIFICATION_REQUIREMENTS = {
    "FIELD_TECH": ["SITE_INDUCTION", "FIRST_AID"],
    "SR_FIELD_TECH": ["SITE_INDUCTION", "FIRST_AID", "WORK_HEIGHT"],
    "ELEC_TECH": ["SITE_INDUCTION", "FIRST_AID", "ELEC_SAFETY"],
    "MECH_TECH": ["SITE_INDUCTION", "FIRST_AID", "CONFINED_SPACE"],
    "INST_TECH": ["SITE_INDUCTION", "FIRST_AID", "INSTR_CAL"],
    "SITE_SUPV": ["SITE_INDUCTION", "FIRST_AID", "WORK_HEIGHT"],
    "OPS_SUPV": ["SITE_INDUCTION", "FIRST_AID"],
}

SITES = [
    {"code": "NFCS", "name": "Northfield Compression Station", "location": "Alberta, Canada", "status": SiteStatus.ACTIVE},
    {"code": "MSA", "name": "Meridian Solar Array", "location": "Nevada, USA", "status": SiteStatus.ACTIVE},
    {"code": "RWTF", "name": "Riverbend Water Treatment Facility", "location": "Ohio, USA", "status": SiteStatus.ACTIVE},
    {"code": "CWF", "name": "Cascade Wind Farm", "location": "Oregon, USA", "status": SiteStatus.ACTIVE},
    {"code": "URYD", "name": "Union Rail Yard Depot", "location": "Texas, USA", "status": SiteStatus.ACTIVE},
    {"code": "HLT", "name": "Harborview Logistics Terminal", "location": "Georgia, USA", "status": SiteStatus.ACTIVE},
    {"code": "SRTF", "name": "Summit Ridge Telecom Facility", "location": "Colorado, USA", "status": SiteStatus.ACTIVE},
    {"code": "DPP", "name": "Delta Petrochemical Plant", "location": "Louisiana, USA", "status": SiteStatus.ACTIVE},
    {"code": "VDC", "name": "Vantage Data Center Campus", "location": "Virginia, USA", "status": SiteStatus.ACTIVE},
    {"code": "RMS", "name": "Ridgeline Mining Support Site", "location": "Nevada, USA", "status": SiteStatus.DEMOBILIZING},
]

# Minimum headcount required per role at each site. Not every role is
# needed at every site (e.g. small sites don't need an Operations
# Supervisor). Deliberately conservative numbers so the generated
# assignments can realistically meet most of them, with a couple of
# spots deliberately left short (see generate_synthetic_data.py) to
# demonstrate the Staffing Shortages feature.
STAFFING_PROFILES = {
    "NFCS": {"SITE_SUPV": 1, "SR_FIELD_TECH": 2, "FIELD_TECH": 5, "ELEC_TECH": 2, "MECH_TECH": 2},
    "MSA": {"SITE_SUPV": 1, "SR_FIELD_TECH": 1, "FIELD_TECH": 4, "ELEC_TECH": 2, "INST_TECH": 1},
    "RWTF": {"SITE_SUPV": 1, "SR_FIELD_TECH": 2, "FIELD_TECH": 5, "MECH_TECH": 2, "INST_TECH": 1},
    "CWF": {"SITE_SUPV": 1, "SR_FIELD_TECH": 1, "FIELD_TECH": 4, "ELEC_TECH": 2, "MECH_TECH": 1},
    "URYD": {"OPS_SUPV": 1, "SR_FIELD_TECH": 1, "FIELD_TECH": 4, "MECH_TECH": 2},
    "HLT": {"OPS_SUPV": 1, "SR_FIELD_TECH": 1, "FIELD_TECH": 4, "ELEC_TECH": 1},
    "SRTF": {"SITE_SUPV": 1, "SR_FIELD_TECH": 1, "FIELD_TECH": 3, "INST_TECH": 2},
    "DPP": {"OPS_SUPV": 1, "SR_FIELD_TECH": 2, "FIELD_TECH": 6, "ELEC_TECH": 2, "MECH_TECH": 2, "INST_TECH": 2},
    "VDC": {"SITE_SUPV": 1, "FIELD_TECH": 3, "ELEC_TECH": 2, "INST_TECH": 1},
    "RMS": {"SITE_SUPV": 1, "FIELD_TECH": 2, "MECH_TECH": 1},
}
