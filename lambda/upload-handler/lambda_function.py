import boto3, json, uuid, os
from datetime import datetime

# AWS clients
comprehend = boto3.client("comprehend")
dynamodb   = boto3.resource("dynamodb")
sns        = boto3.client("sns")

# Env variables
TABLE_NAME     = os.environ.get("TABLE_NAME", "note_summaries")
SNS_TOPIC_ARN  = os.environ.get("SNS_TOPIC_ARN")           # must be verified
MAX_CHARS      = int(os.environ.get("MAX_CHARS", "4800"))

table = dynamodb.Table(TABLE_NAME)

# ------------------- Build human-readable summary --------------------------
def build_human_summary(text):
    """Generate a summary paragraph using AWS Comprehend."""

    senti_resp   = comprehend.detect_sentiment(Text=text, LanguageCode="en")
    ent_resp     = comprehend.detect_entities(Text=text, LanguageCode="en")
    phrase_resp  = comprehend.detect_key_phrases(Text=text, LanguageCode="en")

    sentiment    = senti_resp.get("Sentiment", "NEUTRAL").lower()
    entities     = list({e["Text"] for e in ent_resp.get("Entities", []) if len(e["Text"]) > 2})
    key_phrases  = list({p["Text"] for p in phrase_resp.get("KeyPhrases", []) if len(p["Text"]) > 3})

    summary_parts = [f" **Summary Insight**:\n"]
    summary_parts.append(f"The tone of this note is *{sentiment}*.")    

    if entities:
        summary_parts.append(" It talks about " + ", ".join(entities[:5]) + ".")

    if key_phrases:
        summary_parts.append(" Main ideas include: " + ", ".join(key_phrases[:8]) + ".")

    return "\n".join(summary_parts)

# ------------------- Lambda Entry Point ------------------------------------
def lambda_handler(event, context):
    try:
        body     = json.loads(event.get("body", "{}"))
        raw_text = body.get("text", "").strip()

        if not raw_text:
            return _resp(400, {"message": "Text not provided."})

        # Trim for Comprehend limit
        text = raw_text[:MAX_CHARS]

        summary = build_human_summary(text)

        if len(summary.strip()) < 10:
            return _resp(500, {"message": "Unable to generate meaningful summary."})

        note_id = str(uuid.uuid4())
        table.put_item(Item={
            "note_id"   : note_id,
            "summary"   : summary,
            "created_at": datetime.utcnow().isoformat()
        })

        # ---------- SNS Notification (if topic exists) ----------
        if SNS_TOPIC_ARN:
            sns.publish(
                TopicArn = SNS_TOPIC_ARN,
                Subject  = " New Note Summary Created",
                Message  = f"A new summary was created with ID: {note_id}\n\n{summary}"
            )

        return _resp(200, {"note_id": note_id, "summary": summary})

    except Exception as e:
        print("Exception:", e)

        # Failure Notification
        if SNS_TOPIC_ARN:
            sns.publish(
                TopicArn = SNS_TOPIC_ARN,
                Subject  = " Note Summary FAILED",
                Message  = f"Error occurred: {str(e)}"
            )

        return _resp(500, {"message": "Something went wrong.", "error": str(e)})

# ------------------- Response Formatter ------------------------------------
def _resp(code, body):
    return {
        "statusCode": code,
        "body": json.dumps(body),
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        }
    }
