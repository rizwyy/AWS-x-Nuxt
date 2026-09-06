import json, os, sys, time, urllib.request

endpoint=os.environ.get("ATLAS_API_URL", "").rstrip("/")
token=os.environ.get("ATLAS_ACCESS_TOKEN", "")
if not endpoint or not token:
    raise SystemExit("Set ATLAS_API_URL and ATLAS_ACCESS_TOKEN.")
tests=json.load(open(os.path.join(os.path.dirname(__file__),"rag-evaluation.json")))
passed=0; results=[]
for case in tests:
    payload=json.dumps({"question":case["question"],"documentIds":[],"conversationId":f"eval-{int(time.time())}"}).encode()
    request=urllib.request.Request(f"{endpoint}/chat",data=payload,method="POST",headers={"Authorization":f"Bearer {token}","Content-Type":"application/json"})
    try:
        answer=json.loads(urllib.request.urlopen(request,timeout=100).read()); text=answer.get("text","").lower(); citations=answer.get("citations",[])
        terms=all(term.lower() in text for term in case.get("expectedTerms",[])); citation_ok=bool(citations)==case.get("mustHaveCitation",False)
        abstains=any(word in text for word in ("could not find","don't have","do not have","insufficient"))
        ok=terms and citation_ok and (not case.get("expectAbstention") or abstains)
        results.append({"id":case["id"],"passed":ok,"latencyMs":answer.get("latencyMs"),"citations":len(citations)})
        passed += int(ok)
    except Exception as error: results.append({"id":case["id"],"passed":False,"error":str(error)})
print(json.dumps({"passed":passed,"total":len(tests),"passRate":round(passed/len(tests),3),"results":results},indent=2))
sys.exit(0 if passed==len(tests) else 1)
