import csv
import os
import zipfile
from pathlib import Path

import requests


BASE_URL = "https://turso-db-create-inclusive-research-ogienomo.aws-eu-west-1.turso.io/v1/execute"
TOKEN = os.environ.get("TURSO_AUTH_TOKEN") or ""
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "Content-Type": "application/json",
}

OUT_DIR = Path("exports")
OUT_DIR.mkdir(exist_ok=True)


def normalize_value(value):
    if isinstance(value, dict):
        if value.get("type") == "null":
            return None
        return value.get("value")
    return value


def query(sql):
    payload = {"stmt": {"sql": sql, "args": []}}
    response = requests.post(BASE_URL, headers=HEADERS, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    if "result" not in data:
        raise RuntimeError(f"Unexpected response for SQL: {sql}\n{data}")
    cols = [col["name"] for col in data["result"]["cols"]]
    rows = []
    for row in data["result"]["rows"]:
        rows.append({cols[i]: normalize_value(row[i]) for i in range(len(cols))})
    return rows


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})


def build_exports():
    schools = query("SELECT id, sn, lgea, name, address, headTeacher, phone, lcda, type FROM School")
    school_lookup = {school["id"]: school for school in schools}

    architecture_audits = query(
        "SELECT id, schoolId, schoolType, dateOfAudit, auditorName, weatherConditions, hasRamps, hasDoors, hasToilets, hasFurniture, gpsLat, gpsLng, createdAt, updatedAt FROM ArchitecturalAudit"
    )
    audit_lookup = {audit["id"]: audit for audit in architecture_audits}

    questionnaire_rows = query(
        "SELECT id, schoolId, respondentType, role, roleOther, yearsExperience, pupilsWorkWith, relationship, childMobilityAid, childMobilityOther, B1, B2, B3, B4, B5, C1, C2, C3, C4, D1, D2, D3, D4, PB1, PB2, PB3, PB4, PB5, PB6, PB7, PB8, openComments, totalScore, sectionBScore, sectionCScore, sectionDScore, parentSectionBScore, shareToken, isSharedResponse, gpsLat, gpsLng, createdAt, updatedAt FROM Questionnaire"
    )
    questionnaire_export = []
    for row in questionnaire_rows:
        school = school_lookup.get(row.get("schoolId"), {})
        enriched = dict(row)
        enriched["schoolSn"] = school.get("sn")
        enriched["schoolLgea"] = school.get("lgea")
        enriched["schoolName"] = school.get("name")
        enriched["schoolAddress"] = school.get("address")
        enriched["schoolHeadTeacher"] = school.get("headTeacher")
        enriched["schoolPhone"] = school.get("phone")
        enriched["schoolLcda"] = school.get("lcda")
        enriched["schoolType"] = school.get("type")
        questionnaire_export.append(enriched)

    audit_summary_rows = query(
        "SELECT id, auditId, rampCompositeScore, rampComplianceLevel, doorCompositeScore, doorComplianceLevel, toiletCompositeScore, toiletComplianceLevel, furnitureCompositeScore, furnitureComplianceLevel, overallScore, overallCompliance, keyBarriers FROM AuditSummary"
    )
    audit_export = []
    for row in audit_summary_rows:
        audit = audit_lookup.get(row.get("auditId"), {})
        school = school_lookup.get(audit.get("schoolId"), {})
        enriched = dict(row)
        enriched["auditDate"] = audit.get("dateOfAudit")
        enriched["auditSchoolType"] = audit.get("schoolType")
        enriched["auditAuditorName"] = audit.get("auditorName")
        enriched["auditWeatherConditions"] = audit.get("weatherConditions")
        enriched["auditHasRamps"] = audit.get("hasRamps")
        enriched["auditHasDoors"] = audit.get("hasDoors")
        enriched["auditHasToilets"] = audit.get("hasToilets")
        enriched["auditHasFurniture"] = audit.get("hasFurniture")
        enriched["schoolId"] = audit.get("schoolId")
        enriched["schoolSn"] = school.get("sn")
        enriched["schoolLgea"] = school.get("lgea")
        enriched["schoolName"] = school.get("name")
        enriched["schoolAddress"] = school.get("address")
        audit_export.append(enriched)

    behavioural_map_rows = query(
        "SELECT id, schoolId, pupilPseudonym, mobilityAid, mobilityAidOther, dateOfObservation, observerName, weatherConditions, scheduleStart, scheduleBreak, scheduleLunch, scheduleEnd, gpsLat, gpsLng, createdAt, updatedAt FROM BehavioralMap"
    )
    behavioural_export = []
    for row in behavioural_map_rows:
        school = school_lookup.get(row.get("schoolId"), {})
        enriched = dict(row)
        enriched["schoolSn"] = school.get("sn")
        enriched["schoolLgea"] = school.get("lgea")
        enriched["schoolName"] = school.get("name")
        enriched["schoolAddress"] = school.get("address")
        enriched["schoolHeadTeacher"] = school.get("headTeacher")
        behavioural_export.append(enriched)

    questionnaire_fields = [
        "id",
        "schoolId",
        "schoolSn",
        "schoolLgea",
        "schoolName",
        "schoolAddress",
        "schoolHeadTeacher",
        "schoolPhone",
        "schoolLcda",
        "schoolType",
        "respondentType",
        "role",
        "roleOther",
        "yearsExperience",
        "pupilsWorkWith",
        "relationship",
        "childMobilityAid",
        "childMobilityOther",
        "B1",
        "B2",
        "B3",
        "B4",
        "B5",
        "C1",
        "C2",
        "C3",
        "C4",
        "D1",
        "D2",
        "D3",
        "D4",
        "PB1",
        "PB2",
        "PB3",
        "PB4",
        "PB5",
        "PB6",
        "PB7",
        "PB8",
        "openComments",
        "totalScore",
        "sectionBScore",
        "sectionCScore",
        "sectionDScore",
        "parentSectionBScore",
        "shareToken",
        "isSharedResponse",
        "gpsLat",
        "gpsLng",
        "createdAt",
        "updatedAt",
    ]
    audit_fields = [
        "id",
        "auditId",
        "auditDate",
        "auditSchoolType",
        "auditAuditorName",
        "auditWeatherConditions",
        "auditHasRamps",
        "auditHasDoors",
        "auditHasToilets",
        "auditHasFurniture",
        "schoolId",
        "schoolSn",
        "schoolLgea",
        "schoolName",
        "schoolAddress",
        "rampCompositeScore",
        "rampComplianceLevel",
        "doorCompositeScore",
        "doorComplianceLevel",
        "toiletCompositeScore",
        "toiletComplianceLevel",
        "furnitureCompositeScore",
        "furnitureComplianceLevel",
        "overallScore",
        "overallCompliance",
        "keyBarriers",
    ]
    behavioural_fields = [
        "id",
        "schoolId",
        "schoolSn",
        "schoolLgea",
        "schoolName",
        "schoolAddress",
        "schoolHeadTeacher",
        "pupilPseudonym",
        "mobilityAid",
        "mobilityAidOther",
        "dateOfObservation",
        "observerName",
        "weatherConditions",
        "scheduleStart",
        "scheduleBreak",
        "scheduleLunch",
        "scheduleEnd",
        "gpsLat",
        "gpsLng",
        "createdAt",
        "updatedAt",
    ]

    write_csv(OUT_DIR / "questionnaire_responses_by_school.csv", questionnaire_export, questionnaire_fields)
    write_csv(OUT_DIR / "audit_scores_by_school.csv", audit_export, audit_fields)
    write_csv(OUT_DIR / "behavioural_mapping_by_school.csv", behavioural_export, behavioural_fields)

    with (OUT_DIR / "export_summary.json").open("w", encoding="utf-8") as fh:
        fh.write(
            __import__("json").dumps(
                {
                    "questionnaire_rows": len(questionnaire_export),
                    "audit_summary_rows": len(audit_export),
                    "behavioural_mapping_rows": len(behavioural_export),
                    "schools_included": len(school_lookup),
                },
                indent=2,
            )
        )

    with zipfile.ZipFile(OUT_DIR / "turso_exports_by_school.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for filename in [
            "questionnaire_responses_by_school.csv",
            "audit_scores_by_school.csv",
            "behavioural_mapping_by_school.csv",
            "export_summary.json",
        ]:
            zf.write(OUT_DIR / filename, filename)

    print("Exported files:")
    for filename in [
        "questionnaire_responses_by_school.csv",
        "audit_scores_by_school.csv",
        "behavioural_mapping_by_school.csv",
        "export_summary.json",
        "turso_exports_by_school.zip",
    ]:
        print((OUT_DIR / filename).resolve())


if __name__ == "__main__":
    build_exports()
