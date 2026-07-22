import os
import logging
from datetime import datetime, UTC
from decimal import Decimal

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table(os.environ["ORDERS_TABLE"])


def get_string(image, field):
    return image[field]["S"]


def determine_action(decision):
    """
    Convert the business decision into
    a downstream operational action.
    """

    if decision == "APPROVED":
        return (
            "FULFILMENT_QUEUED",
            "COMPLETED",
        )

    if decision == "MANUAL_REVIEW":
        return (
            "ESCALATED",
            "COMPLETED",
        )

    if decision == "DECLINED":
        return (
            "CLOSED",
            "COMPLETED",
        )

    return (
        None,
        None,
    )


def lambda_handler(event, context):
    logger.info("Received %d stream records", len(event["Records"]))

    for record in event["Records"]:

        # Only process updates
        if record["eventName"] != "MODIFY":
            continue

        new_image = record["dynamodb"]["NewImage"]

        decision = get_string(new_image, "decision")

        # Ignore orders that haven't been decided yet
        if decision == "PENDING":
            continue

        # Already processed?
        downstream_status = new_image.get(
            "downstreamStatus",
            {},
        ).get("S")

        if downstream_status == "COMPLETED":
            logger.info("Order already completed")
            continue

        order_id = get_string(new_image, "orderId")

        action, status = determine_action(decision)

        if action is None:
            logger.warning(
                "No downstream action for %s",
                decision,
            )
            continue

        logger.info(
            "Processing downstream action %s for %s",
            action,
            order_id,
        )

        try:
            orders_table.update_item(
                Key={
                    "orderId": order_id,
                },
                UpdateExpression="""
                    SET
                        downstreamAction = :action,
                        downstreamStatus = :status,
                        downstreamTimestamp = :timestamp
                """,
                ConditionExpression="downstreamStatus = :pending",
                ExpressionAttributeValues={
                    ":action": action,
                    ":status": status,
                    ":pending": "PENDING",
                    ":timestamp": datetime.now(UTC).isoformat(),
                },
            )

            logger.info(
                "Successfully completed downstream processing for %s",
                order_id,
            )

        except Exception:
            logger.exception(
                "Failed downstream processing for %s",
                order_id,
            )

    return {
        "statusCode": 200,
        "processedRecords": len(event["Records"]),
    }
