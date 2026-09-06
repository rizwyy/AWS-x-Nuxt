import base64, json, logging, mimetypes, os, re, time, uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from botocore.config import Config

LOG = logging.getLogger()
LOG.setLevel(logging.INFO)
CFG = Config(connect_timeout=3, read_timeout=90, retries={"max_attempts": 2})
REGION = os.environ.get("AWS_REGION", "us-east-1")
BUCKET = os.environ["DOCUMENT_BUCKET"]
KB_ID = os.environ["KNOWLEDGE_BASE_ID"]
DATA_SOURCE_ID = os.environ.get("DATA_SOURCE_ID", "")
TABLE_NAME = os.environ["TABLE_NAME"]
MAX_FILE_BYTES = int(os.environ.get("MAX_FILE_BYTES", str(20 * 1024 * 1024)))
ALLOWED_TYPES = {"application/pdf", "text/plain", "text/markdown", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
s3 = boto3.client("s3", config=CFG)
bedrock = boto3.client("bedrock-agent-runtime", region_name=REGION, config=CFG)
bedrock_admin = boto3.client("bedrock-agent", region_name=REGION, config=CFG)
table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)


class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def utc_now(): return datetime.now(timezone.utc).isoformat()
def json_default(value): return float(value) if isinstance(value, Decimal) else str(value)
def reply(status, body=None):
    return {"statusCode": status, "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"}, "body": "" if body is None else json.dumps(body, default=json_default)}


def user_id(event):
    claims = (((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt") or {}).get("claims") or {}
    if not claims.get("sub"): raise ApiError(401, "Authentication required.")
    return claims["sub"]


def body(event):
    raw = event.get("body") or "{}"
    if event.get("isBase64Encoded"): raw = base64.b64decode(raw).decode()
    try: return json.loads(raw)
    except (TypeError, ValueError): raise ApiError(400, "Invalid JSON request.")


def safe_name(value):
    name = str(value or "").split("/")[-1].split("\\")[-1]
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    if not name or len(name) > 180: raise ApiError(400, "Invalid filename.")
    return name


def put(pk, sk, **values): table.put_item(Item={"pk": pk, "sk": sk, **values})
def items(pk, prefix):
    return table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)", ExpressionAttributeValues={":pk": pk, ":sk": prefix}).get("Items", [])


def public_doc(item):
    return {"id": item["documentId"], "name": item["name"], "category": item.get("category", "Uncategorized"), "size": f"{max(1, round(int(item.get('size', 0)) / 1024))} KB", "updated": item["updatedAt"], "status": item.get("status", "Processing"), "excerpt": item.get("excerpt", "Uploaded document")}


def upload_url(event, uid):
    data = body(event); name = safe_name(data.get("filename")); size = int(data.get("size") or 0)
    content_type = data.get("contentType") or mimetypes.guess_type(name)[0] or "application/octet-stream"
    if content_type not in ALLOWED_TYPES: raise ApiError(400, "Unsupported document type.")
    if size < 1 or size > MAX_FILE_BYTES: raise ApiError(400, "Document must be between 1 byte and 20 MB.")
    doc_id = str(uuid.uuid4()); key = f"users/{uid}/{doc_id}/{name}"; created = utc_now()
    put(f"USER#{uid}", f"DOC#{doc_id}", entity="document", documentId=doc_id, name=name, size=size, contentType=content_type, s3Key=key, category=data.get("category", "Uncategorized"), status="Uploading", updatedAt=created)
    s3.put_object(Bucket=BUCKET, Key=f"{key}.metadata.json", ContentType="application/json", Body=json.dumps({"metadataAttributes":{"owner":uid,"access":"private","documentId":doc_id}}).encode())
    url = s3.generate_presigned_url("put_object", Params={"Bucket": BUCKET, "Key": key, "ContentType": content_type, "Metadata": {"owner": uid, "document-id": doc_id}}, ExpiresIn=300)
    return reply(200, {"documentId": doc_id, "uploadUrl": url, "headers": {"Content-Type": content_type, "x-amz-meta-owner": uid, "x-amz-meta-document-id": doc_id}})


def ingest(doc_id, uid):
    key = {"pk": f"USER#{uid}", "sk": f"DOC#{doc_id}"}; found = table.get_item(Key=key).get("Item")
    if not found: raise ApiError(404, "Document not found.")
    try: s3.head_object(Bucket=BUCKET, Key=found["s3Key"])
    except Exception: raise ApiError(409, "Upload has not completed.")
    if not DATA_SOURCE_ID: raise ApiError(503, "DATA_SOURCE_ID is not configured.")
    job = bedrock_admin.start_ingestion_job(knowledgeBaseId=KB_ID, dataSourceId=DATA_SOURCE_ID, description=f"Atlas upload {doc_id}")
    table.update_item(Key=key, UpdateExpression="SET #s=:s, ingestionJobId=:j, updatedAt=:u", ExpressionAttributeNames={"#s":"status"}, ExpressionAttributeValues={":s":"Processing", ":j":job["ingestionJob"]["ingestionJobId"], ":u":utc_now()})
    return reply(202, {"documentId": doc_id, "status": "Processing"})


def list_documents(uid):
    docs = sorted(items(f"USER#{uid}", "DOC#"), key=lambda x: x["updatedAt"], reverse=True)
    if DATA_SOURCE_ID:
        for doc in docs:
            if doc.get("status") == "Processing" and doc.get("ingestionJobId"):
                try:
                    job = bedrock_admin.get_ingestion_job(knowledgeBaseId=KB_ID, dataSourceId=DATA_SOURCE_ID, ingestionJobId=doc["ingestionJobId"])["ingestionJob"]
                    mapped = {"COMPLETE":"Ready", "FAILED":"Failed", "STOPPED":"Failed"}.get(job.get("status"), "Processing")
                    if mapped != doc["status"]:
                        doc["status"] = mapped
                        table.update_item(Key={"pk":doc["pk"],"sk":doc["sk"]}, UpdateExpression="SET #s=:s, updatedAt=:u", ExpressionAttributeNames={"#s":"status"}, ExpressionAttributeValues={":s":mapped,":u":utc_now()})
                except Exception: LOG.warning("Could not refresh ingestion job %s", doc.get("ingestionJobId"))
    return reply(200, [public_doc(x) for x in docs])


def answer_question(event, uid, request_id):
    data = body(event); question = str(data.get("question") or "").strip(); conversation_id = str(data.get("conversationId") or uuid.uuid4())
    if not question or len(question) > 4000: raise ApiError(400, "Question must contain 1 to 4,000 characters.")
    started = time.perf_counter(); retrieval_filter={"orAll":[{"equals":{"key":"access","value":"shared"}},{"equals":{"key":"owner","value":uid}}]}; args = {"agenticRetrieveConfiguration":{"foundationModelType":"MANAGED","maxAgentIteration":5}, "messages":[{"role":"user","content":{"text":question}}], "retrievers":[{"configuration":{"knowledgeBase":{"knowledgeBaseId":KB_ID,"retrievalOverrides":{"filter":retrieval_filter,"maxNumberOfResults":8}}},"description":"Authorized Acme company documents"}], "generateResponse":True}
    guardrail_id, guardrail_version = os.environ.get("GUARDRAIL_ID"), os.environ.get("GUARDRAIL_VERSION")
    if guardrail_id and guardrail_version: args["policyConfiguration"] = {"bedrockGuardrailConfiguration":{"guardrailId":guardrail_id,"guardrailVersion":guardrail_version}}
    result = bedrock.agentic_retrieve_stream(**args); text_parts, retrieved, citation_refs, blocked = [], [], [], False
    for event_item in result["stream"]:
        if "responseEvent" in event_item: text_parts.append(event_item["responseEvent"].get("text", ""))
        if "result" in event_item:
            value = event_item["result"]; retrieved = value.get("results", retrieved); generated = value.get("generatedResponse") or {}
            if generated.get("answer") and not text_parts: text_parts.append(generated["answer"])
            citation_refs.extend(generated.get("citations") or [])
        trace = event_item.get("traceEvent", {}).get("attributes", {})
        blocked = blocked or any(w.get("guardrail", {}).get("action") == "BLOCKED" for w in trace.get("warnings", []))
        for error_name in ("accessDeniedException","badGatewayException","dependencyFailedException","internalServerException","throttlingException","validationException"):
            if error_name in event_item: raise RuntimeError(event_item[error_name].get("message", error_name))
    answer = "".join(text_parts).strip() or "I could not find enough information in the authorized documents to answer that question."
    citations = []
    used = {ref["resultIndex"] for citation in citation_refs for ref in citation.get("references", [])}
    for index, source in enumerate(retrieved):
        if used and index not in used: continue
        metadata = source.get("metadata") or {}; uri = metadata.get("x-amz-bedrock-kb-source-uri") or metadata.get("source-uri") or ""
        citations.append({"documentId": f"{KB_ID}:{index}", "title": uri.rsplit("/",1)[-1] or "Company document", "excerpt": (source.get("content") or {}).get("text", "")[:1200]})
    message_id = str(uuid.uuid4()); elapsed = round((time.perf_counter()-started)*1000)
    put(f"USER#{uid}", f"CONV#{conversation_id}", entity="conversation", conversationId=conversation_id, title=question[:80], updatedAt=utc_now())
    put(f"CONV#{uid}#{conversation_id}", f"MSG#{utc_now()}#{message_id}", entity="message", messageId=message_id, question=question, text=answer, citations=citations[:6], latencyMs=elapsed, guardrailBlocked=blocked, createdAt=utc_now())
    LOG.info(json.dumps({"requestId":request_id,"userId":uid,"latencyMs":elapsed,"citationCount":len(citations),"guardrailBlocked":blocked}))
    return reply(200, {"id":message_id,"conversationId":conversation_id,"text":answer,"citations":citations[:6],"latencyMs":elapsed,"costUsd":None,"requestId":request_id})


def conversations(uid):
    rows = sorted(items(f"USER#{uid}", "CONV#"), key=lambda x:x["updatedAt"], reverse=True)
    result=[]
    for row in rows:
        messages=[]
        for saved in items(f"CONV#{uid}#{row['conversationId']}", "MSG#"):
            messages += [{"id":str(uuid.uuid4()),"role":"user","text":saved["question"]},{"id":saved["messageId"],"role":"assistant","text":saved["text"],"citations":saved.get("citations",[]),"latencyMs":saved.get("latencyMs",0),"feedback":saved.get("feedback")}]
        result.append({"id":row["conversationId"],"title":row["title"],"messages":messages})
    return reply(200,result)


def feedback(event, uid):
    data=body(event); message_id=data.get("messageId"); rating=data.get("rating")
    if not message_id or rating not in ("up","down"): raise ApiError(400,"Invalid feedback.")
    put(f"USER#{uid}", f"FEEDBACK#{message_id}", entity="feedback", messageId=message_id, rating=rating, updatedAt=utc_now())
    return reply(204)


def metrics(uid):
    convs=items(f"USER#{uid}","CONV#"); answers=[]
    for conv in convs: answers += items(f"CONV#{uid}#{conv['conversationId']}","MSG#")
    ratings=items(f"USER#{uid}","FEEDBACK#")
    avg=round(sum(int(x.get("latencyMs",0)) for x in answers)/len(answers)) if answers else 0
    return reply(200,{"questionsAnswered":len(answers),"conversationCount":len(convs),"averageLatencyMs":avg,"helpful":sum(1 for x in ratings if x.get("rating")=="up"),"ratings":len(ratings),"blocked":sum(1 for x in answers if x.get("guardrailBlocked"))})


def lambda_handler(event, context):
    try:
        uid=user_id(event); method=(event.get("requestContext") or {}).get("http",{}).get("method",""); path=event.get("rawPath",""); stage=(event.get("requestContext") or {}).get("stage")
        if stage and path.startswith(f"/{stage}/"): path=path[len(stage)+1:]
        if method=="POST" and path=="/chat": return answer_question(event,uid,context.aws_request_id)
        if method=="GET" and path=="/documents": return list_documents(uid)
        if method=="POST" and path=="/documents/upload-url": return upload_url(event,uid)
        match=re.fullmatch(r"/documents/([^/]+)/ingest",path)
        if method=="POST" and match: return ingest(match.group(1),uid)
        if method=="GET" and path=="/conversations": return conversations(uid)
        if method=="POST" and path=="/feedback": return feedback(event,uid)
        if method=="GET" and path=="/metrics": return metrics(uid)
        raise ApiError(404,"Route not found.")
    except ApiError as error: return reply(error.status,{"message":error.message})
    except Exception as error:
        LOG.exception("Unhandled request failure")
        return reply(500,{"message":"The service could not complete the request."})
