import boto3
import json
import os

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get("TABLE_NAME")
print("🔧 Using TABLE_NAME:", TABLE_NAME)

def lambda_handler(event, context):
    print(" Incoming event:", json.dumps(event))  # Log full event

    try:
        params = event.get("queryStringParameters") or {}
        note_id = params.get("noteId")

        print(" Extracted note_id:", note_id)  # Debug note_id

        if not note_id:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "Missing noteId"})
            }

        table = dynamodb.Table(TABLE_NAME)
        response = table.get_item(Key={"note_id": note_id})

        print(" DynamoDB response:", response)  # Debug Dynamo response

        if 'Item' not in response:
            return {
                "statusCode": 404,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "No summary found for this Note ID."})
            }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "summary": response['Item'].get('summary', '')
            })
        }

    except Exception as e:
        print(" ERROR CAUGHT:", str(e))  # Full error in logs
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": "Internal Server Error"})
        }
