"""Generate credential-free, importable n8n workflows. Run from any directory."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def node(name, kind, parameters, version=1, **extra):
    return {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "type": "n8n-nodes-base." + kind,
        "typeVersion": version,
        "position": [0, 0],
        "parameters": parameters,
        **extra,
    }


def http(name, path, method="POST", **parameters):
    return node(
        name,
        "httpRequest",
        {
            "method": method,
            "url": "http://backend:8000/api" + path,
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "options": {"timeout": 180000},
            **parameters,
        },
        4.2,
    )


def edge(connections, source, target, output=0):
    outputs = connections.setdefault(source, {"main": []})["main"]
    while len(outputs) <= output:
        outputs.append([])
    outputs[output].append({"node": target, "type": "main", "index": 0})


def save(filename, name, nodes, connections):
    for index, item in enumerate(nodes):
        item["position"] = [index * 250, 300]
    result = {
        "name": name,
        "nodes": nodes,
        "connections": connections,
        "active": False,
        "settings": {
            "executionOrder": "v1",
            "timezone": "Asia/Kolkata",
            "saveDataErrorExecution": "all",
            "saveDataSuccessExecution": "none",
        },
        "pinData": {},
        "tags": [],
    }
    path = ROOT / "n8n" / "workflows" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def intake():
    nodes = [
        node(
            "Gmail - New Invoice",
            "gmailTrigger",
            {
                "pollTimes": {"item": [{"mode": "everyMinute"}]},
                "simple": True,
                "filters": {
                    "q": "has:attachment (subject:invoice OR filename:invoice) (filename:pdf OR filename:png OR filename:jpg OR filename:jpeg)",
                    "readStatus": "both",
                },
            },
            1.2,
        ),
        node(
            "Gmail - Download Attachments",
            "gmail",
            {
                "resource": "message",
                "operation": "get",
                "messageId": "={{ $json.id }}",
                "simple": False,
                "options": {"downloadAttachments": True},
            },
            2.1,
            onError="continueErrorOutput",
            retryOnFail=True,
            maxTries=3,
            waitBetweenTries=2000,
        ),
        node(
            "Extract Attachments",
            "code",
            {
                "jsCode": "const out = []; for (const [index,item] of $input.all().entries()) { for (const [key,file] of Object.entries(item.binary || {})) { if (/\\.(pdf|png|jpe?g)$/i.test(file.fileName || '')) out.push({json:{gmail_message_id:item.json.id,attachment_id:key,source_email:item.json.from?.text || String(item.json.from || ''),source_filename:file.fileName},binary:{data:file},pairedItem:{item:index}}); } } return out;"
            },
            2,
        ),
        node(
            "Loop - Each Attachment",
            "splitInBatches",
            {"batchSize": 1, "options": {}},
            3,
        ),
        node(
            "Drive - Upload Invoice",
            "googleDrive",
            {
                "resource": "file",
                "operation": "upload",
                "inputDataFieldName": "data",
                "name": "={{ $json.gmail_message_id + '_' + $json.attachment_id + '_' + $json.source_filename }}",
                "driveId": {"__rl": True, "mode": "list", "value": "My Drive"},
                "folderId": {
                    "__rl": True,
                    "mode": "id",
                    "value": "REPLACE_WITH_INVOICE_FOLDER_ID",
                },
                "options": {},
            },
            3,
            onError="continueErrorOutput",
        ),
        node(
            "Restore Attachment Context",
            "code",
            {
                "mode": "runOnceForEachItem",
                "jsCode": "const source = $('Loop - Each Attachment').item; return {json:{...source.json,google_drive_url:'https://drive.google.com/file/d/' + $json.id + '/view'},binary:source.binary};",
            },
            2,
        ),
        http(
            "Backend - Process Invoice",
            "/processing/invoice",
            sendBody=True,
            contentType="multipart-form-data",
            bodyParameters={
                "parameters": [
                    {
                        "parameterType": "formBinaryData",
                        "name": "file",
                        "inputDataFieldName": "data",
                    }
                ]
                + [
                    {"name": key, "value": "={{ $json." + key + " }}"}
                    for key in (
                        "gmail_message_id",
                        "attachment_id",
                        "source_email",
                        "google_drive_url",
                    )
                ]
            },
        ),
        node(
            "Log - Integration Failure",
            "code",
            {
                "mode": "runOnceForEachItem",
                "jsCode": "console.error('Invoice attachment integration failed; inspect execution and retry after reconciliation.'); return $input.item;",
            },
            2,
        ),
    ]
    nodes[6].update(
        onError="continueErrorOutput",
        retryOnFail=True,
        maxTries=3,
        waitBetweenTries=3000,
    )
    c = {}
    for a, b in [(0, 1), (1, 2), (2, 3), (4, 5), (5, 6), (6, 3), (7, 3)]:
        edge(c, nodes[a]["name"], nodes[b]["name"])
    edge(c, nodes[3]["name"], nodes[4]["name"], 1)
    edge(c, nodes[4]["name"], nodes[7]["name"], 1)
    edge(c, nodes[6]["name"], nodes[7]["name"], 1)
    save(
        "invoice_intake.json", "Invoice intake - Gmail to Drive to validation", nodes, c
    )


def notifications(kind):
    nodes = [
        node(
            "Schedule - Payment Check"
            if kind == "payment"
            else "Schedule - Risk Check",
            "scheduleTrigger",
            {
                "rule": {
                    "interval": [
                        {
                            "field": "cronExpression",
                            "expression": "0 8 * * *"
                            if kind == "payment"
                            else "*/15 * * * *",
                        }
                    ]
                }
            },
            1.2,
        )
    ]
    if kind == "payment":
        nodes.append(http("Backend - Refresh Payment Status", "/automation/monitor"))
    nodes += [
        http(
            "Backend - Reserve Notifications",
            f"/automation/notifications/claim?kind={kind}",
        ),
        node(
            "Loop - Each Notification",
            "splitInBatches",
            {"batchSize": 1, "options": {}},
            3,
        ),
        node(
            "Gmail - Send Reminder" if kind == "payment" else "Gmail - Send Risk Alert",
            "gmail",
            {
                "resource": "message",
                "operation": "send",
                "sendTo": "={{ $json.recipient }}",
                "subject": "={{ $json.subject }}",
                "emailType": "text",
                "message": "={{ $json.message }}",
                "options": {"appendAttribution": False},
            },
            2.1,
            onError="continueErrorOutput",
        ),
        http(
            "Backend - Acknowledge Delivery",
            "/unused",
            sendBody=True,
            specifyBody="json",
            jsonBody="={{ {delivery_id: $json.id} }}",
        ),
        node(
            "Log - Delivery Uncertain",
            "code",
            {
                "mode": "runOnceForEachItem",
                "jsCode": "console.error('Delivery is unacknowledged. Check Gmail Sent and the reserved reminder before attempting a manual resend.'); return $input.item;",
            },
            2,
        ),
    ]
    ack = nodes[-2]
    ack["parameters"]["url"] = (
        "=http://backend:8000/api/automation/notifications/{{ $('Loop - Each Notification').item.json.id }}/sent"
    )
    ack.update(
        retryOnFail=True,
        maxTries=3,
        waitBetweenTries=2000,
        onError="continueErrorOutput",
    )
    c = {}
    loop_index = next(
        i for i, n in enumerate(nodes) if n["type"].endswith("splitInBatches")
    )
    for i in range(loop_index):
        edge(c, nodes[i]["name"], nodes[i + 1]["name"])
    edge(c, nodes[loop_index]["name"], nodes[loop_index + 1]["name"], 1)
    edge(c, nodes[loop_index + 1]["name"], ack["name"])
    edge(c, ack["name"], nodes[loop_index]["name"])
    edge(c, nodes[loop_index + 1]["name"], nodes[-1]["name"], 1)
    edge(c, ack["name"], nodes[-1]["name"], 1)
    edge(c, nodes[-1]["name"], nodes[loop_index]["name"])
    save(
        "payment_monitoring.json" if kind == "payment" else "high_risk_alert.json",
        "Payment monitoring and reminders"
        if kind == "payment"
        else "High-risk finance alerts",
        nodes,
        c,
    )


def payment_update():
    nodes = [
        node(
            "Webhook - Confirmed Payment",
            "webhook",
            {
                "httpMethod": "POST",
                "path": "invoice-payment-confirmed",
                "authentication": "headerAuth",
                "responseMode": "lastNode",
                "options": {},
            },
            2,
        ),
        node(
            "Validate Payment Event",
            "code",
            {
                "mode": "runOnceForEachItem",
                "jsCode": "const b=$json.body; if(!b || !Number.isInteger(b.invoice_id) || b.invoice_id < 1 || typeof b.payment_reference !== 'string' || b.payment_reference.length < 3) throw new Error('invoice_id and payment_reference are required'); return {json:b};",
            },
            2,
        ),
        http(
            "Backend - Mark Paid",
            "/unused",
            sendBody=True,
            specifyBody="json",
            jsonBody="={{ {reason: 'Confirmed payment: ' + $json.payment_reference} }}",
        ),
    ]
    nodes[-1]["parameters"]["url"] = (
        "=http://backend:8000/api/invoices/{{ $json.invoice_id }}/pay"
    )
    nodes[-1].update(retryOnFail=True, maxTries=3, waitBetweenTries=2000)
    c = {}
    for a, b in zip(nodes, nodes[1:]):
        edge(c, a["name"], b["name"])
    save("payment_update.json", "Authenticated payment confirmation", nodes, c)


if __name__ == "__main__":
    intake()
    notifications("payment")
    notifications("risk")
    payment_update()
