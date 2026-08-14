import os
import json
import glob
import datetime
import cv2
from llm_gemini import readDie, sixNineSubagent, DieReadError
from concurrent.futures import ThreadPoolExecutor

def processRecord(r, crop_dir, pad_ratio, upscale, use_specialist):
    image_path = r["png"]
    if crop_dir:
        image_path = deriveCrop(r, crop_dir, pad_ratio, upscale)
        if image_path is None:
            print(r["name"], "crop failed")
            return None

    try:
        reading = readDie(image_path)
    except DieReadError as e:
        print(r["name"], "error:", e)
        reading = None

    first_pass = reading.value if reading else None
    predicted = first_pass
    sixnine = None

    if use_specialist and first_pass in (6, 9):
        try:
            sixnine = sixNineSubagent(image_path, reading.top_face_position)
        except DieReadError as e:
            print(r["name"], "specialist error:", e)
        if sixnine and sixnine.is_six_or_nine and sixnine.dot_present and sixnine.value:
            predicted = int(sixnine.value)

    print(r["name"], "truth", r.get("value"), "->", predicted,
          f"(first pass {first_pass})" if predicted != first_pass else "")

    return {
        "name": r["name"],
        "truth": r.get("value"),
        "reject_reason": r.get("reject_reason"),
        "light": r.get("light"),
        "predicted": predicted,
        "first_pass": first_pass,
        "confidence": reading.confidence if reading else None,
        "sixnine_value": sixnine.value if sixnine else None,
        "sixnine_dot": sixnine.dot_position if sixnine else None,
        "others": reading.other_face_numerals if reading else [],
    }

def deriveCrop(record, out_dir, pad_ratio=0.5, upscale=4):
    img = cv2.imread(record["png"])
    if img is None:
        return None
    x, y, w, h = record["bbox"]
    pad = int(max(w, h) * pad_ratio)

    y1 = max(0, y - pad)
    x1 = max(0, x - pad)
    y2 = min(img.shape[0], y + h + pad)
    x2 = min(img.shape[1], x + w + pad)
    crop = img[y1:y2, x1:x2]

    if upscale != 1:
        crop = cv2.resize(crop, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)

    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, record["name"] + ".png")
    cv2.imwrite(out_path, crop)
    return out_path


def saveTestResults(results, summary=None):
    test_result_repo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results")
    stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    file_name = f"test_results_{stamp}.json"
    file_location = os.path.join(test_result_repo, file_name)
    payload = {"summary": summary, "results": results} if summary else results
    with open(file_location , "w") as f:
            json.dump(payload, f, indent=4)

def runTestSet(records, crop_dir=None, pad_ratio=0.5, upscale=4, use_specialist=True):
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(
            lambda r: processRecord(r, crop_dir, pad_ratio, upscale, use_specialist),
            records
        ))
    return [r for r in results if r is not None]

def runTestSetUnthreaded(records, crop_dir=None, pad_ratio=0.5, upscale=4, use_specialist=True):
    results = []
    for r in records:
        image_path = r["png"]
        if crop_dir:
            image_path = deriveCrop(r, crop_dir, pad_ratio, upscale)
            if image_path is None:
                print(r["name"], "crop failed")
                continue

        try:
            reading = readDie(image_path)
        except DieReadError as e:
            print(r["name"], "error:", e)
            reading = None

        # step 1 result
        first_pass = reading.value if reading else None
        predicted = first_pass
        sixnine = None

        # step 2, only when step 1 says 6 or 9
        if use_specialist and first_pass in (6,9):
            try:
                sixnine = sixNineSubagent(image_path, reading.top_face_position)
            except DieReadError as e:
                print(r["name"], "specialist error:", e)
            if sixnine and sixnine.is_six_or_nine and sixnine.dot_present and sixnine.value:
                predicted = int(sixnine.value)

        results.append({
            "name": r["name"],
            "truth": r.get("value"),
            "reject_reason": r.get("reject_reason"),
            "light": r.get("light"),
            "predicted": predicted,
            "first_pass": first_pass,
            "confidence": reading.confidence if reading else None,
            "sixnine_value": sixnine.value if sixnine else None,
            "sixnine_dot": sixnine.dot_position if sixnine else None,
            "others": reading.other_face_numerals if reading else [],
        })
        print(r["name"], "truth", r.get("value"), "->", predicted,
              f"(first pass {first_pass})" if predicted != first_pass else "")
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
    rejects = [r for r in records if r.get("reject_reason")]
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

def scoreSplit(results):
    sixnine = [r for r in results if r["truth"] in (6, 9)]
    other   = [r for r in results if r["truth"] not in (6, 9) and r["truth"] is not None]
    print("--- 6/9 subset ---")
    scoreResults(sixnine)
    print("--- everything else ---")
    scoreResults(other)


def summaryFromScored(scored):
    total = len(scored["correct"]) + len(scored["wrong"]) + len(scored["abstained"])
    return {
        "total": total,
        "correct": len(scored["correct"]),
        "wrong": len(scored["wrong"]),
        "abstained": len(scored["abstained"]),
        "accuracy": round(len(scored["correct"]) / total, 3) if total else None,
        "rejects_ok": len(scored["rejects_ok"]),
        "rejects_missed": len(scored["rejects_missed"]),
    }

###How to run

if __name__ == "__main__":
    tests_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_images")

    records, problems = loadTestSet(tests_directory)
    results = runTestSet(records, crop_dir="crops_p50_u4", pad_ratio=0.5, upscale=4, use_specialist=True)
    scored = scoreResults(results)
    scoreSplit(results)
    saveTestResults(results, summaryFromScored(scored))
