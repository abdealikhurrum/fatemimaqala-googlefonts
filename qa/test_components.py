import os, sys, json, subprocess, pytest
HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)

@pytest.fixture(scope="module")
def regress():
    out = "/tmp/fm_comp.ttf"
    subprocess.run(["fontmake","-u",f"{ROOT}/sources/FatemiMaqala-Regular.ufo",
                    "-o","ttf","-a","--output-path",out], check=True, capture_output=True)
    r = subprocess.run([sys.executable, f"{HERE}/collision_regress.py", out],
                       check=True, capture_output=True, text=True)
    return json.loads(r.stdout)

def test_componentB_connecting_kaaf_clears(regress):
    assert regress["kaaf_clearTop"]["kaaf_above"] == 0, regress["kaaf_clearTop"]
    assert regress["kaaf_dotted"]["kaaf_above"] == 0, regress["kaaf_dotted"]
    assert regress["kaaf_longAsc"]["kaaf_above"] == 0, regress["kaaf_longAsc"]
    assert regress["clean"]["kaaf_above"] == 0 and regress["clean"]["belowmark_wawreh"] == 0

def test_componentC_nonjoin_kaaf_clears(regress):
    assert regress["kaaf_nonJoin"]["kaaf_above"] == 0, regress["kaaf_nonJoin"]
    assert regress["clean"]["kaaf_above"] == 0

def test_componentD_belowmark_clears(regress):
    assert regress["belowmark_wawreh"]["belowmark_wawreh"] == 0, regress["belowmark_wawreh"]
    assert regress["clean"]["belowmark_wawreh"] == 0
