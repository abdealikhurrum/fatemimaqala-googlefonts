import os, sys, json, subprocess
HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)

def build_and_regress(out="/tmp/fm_comp.ttf"):
    subprocess.run(["fontmake","-u",f"{ROOT}/sources/FatemiMaqala-Regular.ufo",
                    "-o","ttf","-a","--output-path",out], check=True, capture_output=True)
    r = subprocess.run([sys.executable, f"{HERE}/collision_regress.py", out],
                       check=True, capture_output=True, text=True)
    return json.loads(r.stdout)

def test_componentB_connecting_kaaf_clears():
    res = build_and_regress()
    assert res["kaaf_clearTop"]["kaaf_above"] == 0, res["kaaf_clearTop"]
    assert res["kaaf_dotted"]["kaaf_above"] == 0, res["kaaf_dotted"]
    assert res["kaaf_longAsc"]["kaaf_above"] == 0, res["kaaf_longAsc"]
    assert res["clean"]["kaaf_above"] == 0 and res["clean"]["belowmark_wawreh"] == 0

def test_componentC_nonjoin_kaaf_clears():
    res = build_and_regress()
    assert res["kaaf_nonJoin"]["kaaf_above"] == 0, res["kaaf_nonJoin"]
    assert res["clean"]["kaaf_above"] == 0
