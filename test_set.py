import os
import json
import glob
import datetime
import cv2
from llm_gemini import readDie, DieReadError

def saveTestResults(results):
    test_result_repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results")
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"test_results_{stamp}.json"
    file_location = os.path.join(test_result_repo, file_name)
    with open(file_location , "w") as f:
            json.dump(results, f, indent=4)

def runTestSet(records):
    results = []
    for r in records:
        try:
            reading = readDie(r["png"])
        except DieReadError as e:
            print(r["name"], "error:", e)
            reading = None

        results.append({
            "name": r["name"],
            "truth": r.get("value"),
            "reject_reason": r.get("reject_reason"),
            "light": r.get("light"),
            "predicted": reading.value if reading else None,
            "confidence": reading.confidence if reading else None,
            "others": reading.other_face_numerals if reading else [],
        })
        print(r["name"], "truth", r.get("value"), "->", reading.value if reading else None)
    return results

def loadTestSet(directory):
    records = []
    problems = []

    for json_path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        png_path = json_path[:-5] + ".png"

        if not os.path.isfile(png_path):
            problems.append(f"{os.path.basename(json_path)}: no matching PNG")
            continue

        try:
            with open(json_path) as f:
                meta = json.load(f)
        except json.JSONDecodeError as e:
            problems.append(f"{os.path.basename(json_path)}: bad JSON - {e}")
            continue

        value = meta.get("value")
        if value is not None and not (1 <= value <= 20):
            problems.append(f"{os.path.basename(json_path)}: value {value} out of range")

        meta["png"] = png_path
        meta["name"] = os.path.basename(json_path)[:-5]
        records.append(meta)

    #PNGs with no sidecar
    for png_path in sorted(glob.glob(os.path.join(directory, "*.png"))):
        if not os.path.isfile(png_path[:-4] + ".json"):
            problems.append(f"{os.path.basename(png_path)}: no matching JSON")

    return records, problems

def summarize(records, problems):
    labeled = [r for r in records if r.get("value") is not None]
    rejects = [r for r in records if r.get("reject reason")]
    unlabeled = [r for r in records if r.get("value") is None and not r.get("reject_reason")]

    print(f"records: {len(records)}")
    print(f"labeled: {len(labeled)}")
    print(f"rejects: {len(rejects)}")
    print(f"unlabeled: {len(unlabeled)}")

    on = [r for r in labeled if r.get("light") is True]
    off = [r for r in labeled if r.get("light") is False]
    missing = [r for r in labeled if "light" not in r]
    print(f"light on/off/unset: {len(on)}/{len(off)}/{len(missing)}")

    if labeled:
        values = sorted(r["value"] for r in labeled)
        print(f"values: {values}")

    for r in unlabeled:
        print(f" unlabeled: {r['name']}")

    for p in problems:
        print(f" PROBLEM: {p}")


def scoreResults(results):
    scored = {"correct": [], "wrong": [], "abstained": [], "rejects_ok": [], "rejects_missed": []}

    for r in results:
        if r["reject_reason"]:
            key = "rejects_ok" if r["predicted"] is None else "rejects_missed"
            scored[key].append(r)
        elif r["truth"] is None:
            continue
        elif r["predicted"] is None:
            scored["abstained"].append(r)
        elif r["predicted"] == r["truth"]:
            scored["correct"].append(r)
        else:
            scored["wrong"].append(r)

    total = len(scored["correct"]) + len(scored["wrong"]) + len(scored["abstained"])
    print(f"correct:   {len(scored['correct'])}/{total}")
    print(f"wrong:     {len(scored['wrong'])}/{total}")
    print(f"abstained: {len(scored['abstained'])}/{total}")
    print(f"rejects handled: {len(scored['rejects_ok'])}/"
          f"{len(scored['rejects_ok']) + len(scored['rejects_missed'])}")

    print("\nwrong answers:")
    for r in scored["wrong"]:
        seen = "truth visible in others" if r["truth"] in r["others"] else ""
        print(f"  {r['name'][5:20]}  {r['truth']} -> {r['predicted']}  {seen}")

    return scored

###How to run

tests_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images")

records, problems = loadTestSet(tests_directory)
results = runTestSet(records)
scoreResults(results)
saveTestResults(results)
