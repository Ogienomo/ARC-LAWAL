import csv
import os
import re
import shutil
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

SRC_DIR = Path("audio_exports")
OUT_DIR = Path("exports/interview_audio")
OUT_DIR.mkdir(parents=True, exist_ok=True)


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
        raise RuntimeError(f"Unexpected response: {data}")
    result = data["result"]
    cols = [col["name"] for col in result["cols"]]
    rows = []
    for row in result["rows"]:
        rows.append({cols[i]: normalize_value(row[i]) for i in range(len(cols))})
    return rows


def safe_label(value):
    if not value:
        return "unknown"
    label = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("_")
    return label or "unknown"


def build_exports():
    schools = query("SELECT id, sn, lgea, name FROM School")
    school_lookup = {school["id"]: school for school in schools}

    interviews = query(
        "SELECT id, schoolId, interviewType, participantPseudonym, interviewerName, dateOfInterview, createdAt, updatedAt FROM Interview"
    )
    interview_lookup = {interview["id"]: interview for interview in interviews}

    audio_rows = query(
        "SELECT id, interviewId, questionCode, questionText, responseText, fieldNotes, emotionalTone FROM InterviewResponse WHERE questionCode = 'AUDIO_FILE'"
    )

    manifest_rows = []
    copied = 0

    for item in audio_rows:
        interview = interview_lookup.get(item.get("interviewId"), {})
        school = school_lookup.get(interview.get("schoolId"), {})
        source_name = item.get("responseText")
        if not source_name:
            continue

        source_path = SRC_DIR / source_name
        if not source_path.exists():
            # Try matching by suffix if the files were exported with a different name prefix
            matches = list(SRC_DIR.glob(f"*{source_name.split('/')[-1]}"))
            if matches:
                source_path = matches[0]
            else:
                continue

        interview_type = safe_label(interview.get("interviewType"))
        participant = safe_label(interview.get("participantPseudonym"))
        school_name = safe_label(school.get("name"))
        school_sn = safe_label(school.get("sn"))
        school_lgea = safe_label(school.get("lgea"))

        target_name = f"{school_sn}_{school_lgea}_{school_name}_{interview_type}_{participant}{source_path.suffix}"
        target_path = OUT_DIR / target_name

        # avoid collisions by adding a short suffix if needed
        counter = 1
        while target_path.exists():
            target_path = OUT_DIR / f"{target_name[:-len(source_path.suffix)]}_{counter}{source_path.suffix}"
            counter += 1

        shutil.copy2(source_path, target_path)

        manifest_rows.append(
            {
                "sourceFile": source_path.name,
                "exportedFile": target_path.name,
                "schoolId": interview.get("schoolId"),
                "schoolSn": school.get("sn"),
                "schoolLgea": school.get("lgea"),
                "schoolName": school.get("name"),
                "interviewId": interview.get("id"),
                "interviewType": interview.get("interviewType"),
                "participantPseudonym": interview.get("participantPseudonym"),
                "interviewDate": interview.get("dateOfInterview"),
                "responseText": item.get("responseText"),
                "fieldNotes": item.get("fieldNotes"),
            }
        )
        copied += 1

    with (OUT_DIR / "interview_audio_manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "sourceFile",
                "exportedFile",
                "schoolId",
                "schoolSn",
                "schoolLgea",
                "schoolName",
                "interviewId",
                "interviewType",
                "participantPseudonym",
                "interviewDate",
                "responseText",
                "fieldNotes",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    with zipfile.ZipFile(OUT_DIR / "interview_audio_exports.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for path in OUT_DIR.glob("*.webm"):
            zf.write(path, path.name)
        zf.write(OUT_DIR / "interview_audio_manifest.csv", "interview_audio_manifest.csv")

    print(f"Copied {copied} interview audio files")
    print(f"Manifest: {OUT_DIR / 'interview_audio_manifest.csv'}")
    print(f"Archive: {OUT_DIR / 'interview_audio_exports.zip'}")


if __name__ == "__main__":
    build_exports()
