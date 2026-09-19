import base64
from copy import deepcopy
from datetime import date
import pytest
from clm.web import create_app


def call(client, path, method="GET", data=None, status=200):
    r=client.open("/api"+path,method=method,json=data)
    assert r.status_code==status, r.get_json()
    return r.get_json()


def switch(client, role): return call(client,"/session","POST",{"role":role})


def approve_dossier(client, cid):
    switch(client,"Relationship manager")
    path="/cases/"+cid+"/wealth"
    w=call(client,path)["dossier"]
    w.update(profile=dict(occupation="Synthetic founder",background="Synthetic company founder with a documented sale.",netWorth=1000000,outflows=0,fundsAmount=100000,remittingBank="Synthetic bank",fundsOrigin="Sale proceeds",enhancedRationale="Synthetic enhanced checks completed",reconciliationNote="Net gain, no double counting."),events=[dict(id="event-1",title="Synthetic business sale",category="Business sale",date=date.today().isoformat(),amount=2000000,currency="SGD",ownership=50,fxRate=1,fxSource="SGD",deductions=0,jurisdiction="Singapore",description="Synthetic sale gain after invested capital.")],evidence=[dict(id="evidence-1",title="Synthetic registry test fixture",issuer="Test publisher",date=date.today().isoformat(),reference="Section 1",excerpt="Synthetic corroboration fixture",url="https://example.com/synthetic-test",documentId="",independent=True,eventIds=["event-1"])],narrative="")
    call(client,path,"PUT",w)
    switch(client,"Compliance")
    w=call(client,path)["dossier"]
    call(client,path+"/evidence/evidence-1/review","POST",dict(revision=w["revision"],status="Verified",note="Synthetic fixture only, reviewed for automated testing"))
    switch(client,"Relationship manager")
    w=call(client,path)["dossier"]
    call(client,path+"/draft","POST",dict(revision=w["revision"]))
    w=call(client,path)["dossier"]
    call(client,path+"/decision","POST",dict(revision=w["revision"],action="submit",note="Prepared synthetic case for independent review"))
    switch(client,"Compliance")
    w=call(client,path)["dossier"]
    call(client,path+"/decision","POST",dict(revision=w["revision"],action="approve",note="Independent synthetic test assessment accepted"))
    return path


@pytest.fixture
def client(tmp_path):
    app=create_app(dict(TESTING=True,DATA_DIR=str(tmp_path),SECRET_KEY="wealth-test"))
    c=app.test_client();c.get("/api/state")
    return c


def create(client):
    return call(client,"/cases","POST",dict(name="Wealth Test",email="wealth@example.com",type="Individual",risk="Low",aum=1),201)["id"]


def test_review_flow_snapshot_and_refresh(client):
    cid=create(client);p=approve_dossier(client,cid)
    result=call(client,p)
    assert result["assessment"]["status"]=="Approved"
    assert result["assessment"]["coverage"]==100
    assert result["assessment"]["gap"]==0
    assert len(result["dossier"]["reviews"])==2
    snapshot=deepcopy(result["dossier"]["reviews"][0]["snapshot"])
    switch(client,"Relationship manager")
    call(client,"/cases/"+cid,"PATCH",dict(risk="High"))
    assert call(client,p)["assessment"]["status"]=="Needs refresh"
    assert call(client,p)["dossier"]["reviews"][0]["snapshot"]==snapshot
    assert client.get("/api"+p+"/export").status_code==200
    switch(client,"Client")
    call(client,p,status=400)
    for row in call(client,"/state")["cases"]:
        assert "wealth" not in row and "wealthSummary" not in row


def test_submission_lock_and_optimistic_concurrency(client):
    cid=create(client);p=approve_dossier(client,cid)
    switch(client,"Relationship manager");w=call(client,p)["dossier"]
    call(client,p,"PUT",w)
    call(client,p,"PUT",w,400)
    w=call(client,p)["dossier"]
    call(client,p+"/decision","POST",dict(revision=w["revision"],action="submit",note="Ready for review"))
    w=call(client,p)["dossier"]
    call(client,p,"PUT",w,400)
    call(client,p+"/decision","POST",dict(revision=w["revision"],action="approve",note="Cannot self approve"),400)
    switch(client,"Compliance")
    call(client,p+"/decision","POST",dict(revision=w["revision"],action="return",note="Clarify ownership"))
    assert call(client,p)["assessment"]["status"]=="Changes requested"


def test_evidence_edits_invalidate_review_and_bad_references_rejected(client):
    cid=create(client);p=approve_dossier(client,cid)
    switch(client,"Relationship manager");w=call(client,p)["dossier"]
    w["evidence"][0]["excerpt"]="Changed supporting claim"
    call(client,p,"PUT",w)
    r=call(client,p)
    assert r["assessment"]["coverage"]==0
    assert r["dossier"]["evidence"][0]["reviewStatus"]=="Pending review"
    w=r["dossier"];w["evidence"][0]["documentId"]="other-client-file"
    call(client,p,"PUT",w,400)
    w["evidence"][0]["documentId"]="";w["evidence"][0]["url"]="javascript:alert(1)"
    call(client,p,"PUT",w,400)


def test_bad_numbers_and_reconciliation_and_citations(client):
    cid=create(client);p=approve_dossier(client,cid)
    switch(client,"Relationship manager");w=call(client,p)["dossier"]
    w["profile"]["netWorth"]=10000000;w["narrative"]="An unsupported statement [E:missing]"
    call(client,p,"PUT",w)
    codes={f["code"] for f in call(client,p)["assessment"]["findings"]}
    assert {"reconcile","citations"} <= codes
    w=call(client,p)["dossier"];w["events"][0]["amount"]=float("nan")
    call(client,p,"PUT",w,400)


def test_policy_change_and_submission_fingerprint(client):
    cid=create(client);p=approve_dossier(client,cid)
    switch(client,"Relationship manager");w=call(client,p)["dossier"]
    call(client,p,"PUT",w);w=call(client,p)["dossier"]
    call(client,p+"/decision","POST",dict(action="submit",revision=w["revision"],note="Please review"))
    switch(client,"Compliance");s=call(client,"/state")
    call(client,"/wealth-policy","PUT",dict(**{**s["wealthPolicy"],"tolerance":5},revision=s["revision"]))
    w=call(client,p)["dossier"]
    call(client,p+"/decision","POST",dict(action="approve",revision=w["revision"],note="Policy changed"),400)


def test_document_corroboration_requires_verified_non_sample(client):
    cid=create(client);p=approve_dossier(client,cid)
    switch(client,"Relationship manager")
    call(client,"/cases/"+cid+"/documents","POST",dict(name="wealth.pdf",type="Source of wealth evidence",content=base64.b64encode(b"%PDF-1.4 synthetic fixture").decode()),201)
    s=call(client,"/state");record=next(x for x in s["cases"] if x["id"]==cid);doc=record["documents"][-1]
    w=call(client,p)["dossier"];w["evidence"][0]["documentId"]=doc["id"];w["evidence"][0]["url"]=""
    call(client,p,"PUT",w);switch(client,"Compliance");w=call(client,p)["dossier"]
    call(client,p+"/evidence/evidence-1/review","POST",dict(revision=w["revision"],status="Verified",note="Claim inspected"))
    assert call(client,p)["assessment"]["coverage"]==0
    call(client,"/cases/"+cid+"/documents/"+doc["id"]+"/review","POST",dict(status="Verified",note="Document checked"))
    assert call(client,p)["assessment"]["coverage"]==100
